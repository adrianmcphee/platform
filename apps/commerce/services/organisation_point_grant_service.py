from django.db import transaction
from typing import Tuple, Optional, Dict
import logging
from ..interfaces import OrganisationPointGrantServiceInterface
from ..models import OrganisationPointGrant, OrganisationPointGrantRequest, Organisation, SalesOrderLineItem
from apps.talent.models import Person  # Update this import

logger = logging.getLogger(__name__)

class OrganisationPointGrantService(OrganisationPointGrantServiceInterface):
    GrantType = OrganisationPointGrantRequest.GrantType

    def create_grant(
        self,
        organisation_id: str,
        amount: int,
        granted_by_id: str,
        rationale: str,
        grant_request_id: Optional[str] = None,
        sales_order_item_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                organisation = Organisation.objects.get(id=organisation_id)
                granted_by = Person.objects.get(id=granted_by_id)
                
                grant_data = {
                    'organisation': organisation,
                    'amount': amount,
                    'granted_by': granted_by,
                    'rationale': rationale,
                    'grant_request_id': grant_request_id
                }
                
                if sales_order_item_id:
                    sales_order_item = SalesOrderLineItem.objects.get(id=sales_order_item_id)
                    grant_data['sales_order_item'] = sales_order_item

                grant = OrganisationPointGrant.objects.create(**grant_data)
                
                # Update organisation's point balance
                organisation.point_account.balance += amount
                organisation.point_account.save()
                
                return True, f"Grant of {amount} points created successfully"
        except (Organisation.DoesNotExist, Person.DoesNotExist, SalesOrderLineItem.DoesNotExist) as e:
            return False, f"{e.__class__.__name__}: {str(e)}"
        except Exception as e:
            logger.error(f"Error creating point grant: {str(e)}")
            return False, str(e)

    def get_grant(self, grant_id: str) -> Optional[Dict]:
        try:
            grant = OrganisationPointGrant.objects.get(id=grant_id)
            return {
                'id': grant.id,
                'organisation': grant.organisation.name,
                'amount': grant.amount,
                'granted_by': grant.granted_by.full_name,
                'rationale': grant.rationale,
                'created_at': grant.created_at,
            }
        except OrganisationPointGrant.DoesNotExist:
            return None

    def create_request(
        self,
        organisation_id: str,
        number_of_points: int,
        requested_by_id: str,
        rationale: str,
        grant_type: str
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                organisation = Organisation.objects.get(id=organisation_id)
                requested_by = Person.objects.get(id=requested_by_id)
                
                request = OrganisationPointGrantRequest.objects.create(
                    organisation=organisation,
                    number_of_points=number_of_points,
                    requested_by=requested_by,
                    rationale=rationale,
                    grant_type=grant_type
                )
                
                return True, f"Point grant request for {number_of_points} points created successfully"
        except (Organisation.DoesNotExist, Person.DoesNotExist) as e:
            return False, f"{e.__class__.__name__}: {str(e)}"
        except Exception as e:
            logger.error(f"Error creating point grant request: {str(e)}")
            return False, str(e)

    def approve_request(self, request_id: str) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                request = OrganisationPointGrantRequest.objects.get(id=request_id)
                if request.status != "Pending":
                    return False, "Request is not in a pending state"
                
                if request.grant_type == OrganisationPointGrantRequest.GrantType.FREE:
                    success, message = self.create_grant(
                        organisation_id=request.organisation.id,
                        amount=request.number_of_points,
                        granted_by_id=request.requested_by.id,
                        rationale=request.rationale,
                        grant_request_id=request.id
                    )
                    if success:
                        request.status = "Approved"
                        request.save()
                        return True, "Free grant request approved and grant created"
                    else:
                        return False, f"Failed to create free grant: {message}"
                elif request.grant_type == OrganisationPointGrantRequest.GrantType.PAID:
                    request.status = "Approved"
                    request.save()
                    return True, "Paid grant request approved"
                else:
                    return False, "Invalid grant type"
        except OrganisationPointGrantRequest.DoesNotExist:
            return False, "Request not found"
        except Exception as e:
            logger.error(f"Error approving point grant request: {str(e)}")
            return False, str(e)

    def process_paid_grant(self, grant_request_id: str, sales_order_item_id: str) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                request = OrganisationPointGrantRequest.objects.get(id=grant_request_id)
                sales_order_item = SalesOrderLineItem.objects.get(id=sales_order_item_id)
                
                if request.status != "Approved":
                    return False, "Grant request is not approved"
                
                success, message = self.create_grant(
                    organisation_id=request.organisation.id,
                    amount=request.number_of_points,
                    granted_by_id=request.requested_by.id,
                    rationale=request.rationale,
                    grant_request_id=request.id,
                    sales_order_item_id=sales_order_item.id
                )
                
                if success:
                    return True, "Paid grant processed successfully"
                else:
                    return False, f"Failed to process paid grant: {message}"
        except (OrganisationPointGrantRequest.DoesNotExist, SalesOrderLineItem.DoesNotExist) as e:
            return False, f"{e.__class__.__name__}: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing paid grant: {str(e)}")
            return False, str(e)

    def reject_request(self, request_id: str) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                request = OrganisationPointGrantRequest.objects.get(id=request_id)
                if request.status != "Pending":
                    return False, "Request is not in a pending state"
                
                request.status = "Rejected"
                request.save()
                return True, "Request rejected successfully"
        except OrganisationPointGrantRequest.DoesNotExist:
            return False, "Request not found"
        except Exception as e:
            logger.error(f"Error rejecting point grant request: {str(e)}")
            return False, str(e)

    def get_request(self, request_id: str) -> Optional[Dict]:
        try:
            request = OrganisationPointGrantRequest.objects.get(id=request_id)
            return {
                'id': request.id,
                'organisation': request.organisation.name,
                'number_of_points': request.number_of_points,
                'requested_by': request.requested_by.full_name,
                'rationale': request.rationale,
                'grant_type': request.grant_type,
                'status': request.status,
                'created_at': request.created_at,
            }
        except OrganisationPointGrantRequest.DoesNotExist:
            return None

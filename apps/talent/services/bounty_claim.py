import logging
from typing import Dict, Tuple, Optional, List
from django.db import transaction
from django.core.exceptions import ValidationError
from django.apps import apps

from ..interfaces import BountyClaimServiceInterface
from ..models import BountyClaim, BountyBid, BountyDeliveryAttempt, Person

logger = logging.getLogger(__name__)

class BountyClaimService(BountyClaimServiceInterface):
    @transaction.atomic
    def create_claim(
        self,
        bounty_id: str,
        person_id: str,
        accepted_bid_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            # Get and validate bounty
            Bounty = apps.get_model('product_management', 'Bounty')
            bounty = Bounty.objects.select_for_update().get(id=bounty_id)
            
            if bounty.status not in [Bounty.BountyStatus.DRAFT, Bounty.BountyStatus.IN_PROGRESS]:
                return False, "Bounty is not available for claiming"

            # Validate person
            person = Person.objects.get(id=person_id)

            # Check for existing claim
            if BountyClaim.objects.filter(bounty=bounty, person=person).exists():
                return False, "Person has already claimed this bounty"

            # Validate accepted bid if provided
            if accepted_bid_id:
                try:
                    accepted_bid = BountyBid.objects.get(
                        id=accepted_bid_id,
                        bounty=bounty,
                        person=person,
                        status=BountyBid.Status.ACCEPTED
                    )
                except BountyBid.DoesNotExist:
                    return False, "Invalid or unauthorized accepted bid"
            else:
                accepted_bid = None

            # Create claim
            claim = BountyClaim.objects.create(
                bounty=bounty,
                person=person,
                accepted_bid=accepted_bid
            )

            # Update bounty status
            bounty.status = Bounty.BountyStatus.IN_PROGRESS
            bounty.save()

            return True, "Claim created successfully"

        except (Bounty.DoesNotExist, Person.DoesNotExist):
            return False, "Invalid bounty or person ID"
        except Exception as e:
            logger.error(f"Error creating claim: {str(e)}")
            return False, "Failed to create claim"

    @transaction.atomic
    def submit_delivery_attempt(
        self,
        claim_id: str,
        delivery_message: str,
        attachments: Optional[List] = None
    ) -> Tuple[bool, str]:
        try:
            claim = BountyClaim.objects.select_for_update().get(id=claim_id)
            
            if claim.status != BountyClaim.Status.ACTIVE:
                return False, "Claim is not active"

            # Create delivery attempt
            delivery_attempt = BountyDeliveryAttempt.objects.create(
                bounty_claim=claim,
                delivery_message=delivery_message
            )

            # Handle attachments if provided
            if attachments:
                for attachment in attachments:
                    delivery_attempt.add_attachment(attachment)

            return True, "Delivery attempt submitted successfully"

        except BountyClaim.DoesNotExist:
            return False, "Claim not found"
        except Exception as e:
            logger.error(f"Error submitting delivery attempt: {str(e)}")
            return False, "Failed to submit delivery attempt"

    @transaction.atomic
    def review_delivery_attempt(
        self,
        attempt_id: str,
        reviewer_id: str,
        status: str,
        review_message: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            # Validate reviewer
            reviewer = Person.objects.get(id=reviewer_id)
            
            # Get and validate delivery attempt
            attempt = BountyDeliveryAttempt.objects.select_for_update().get(id=attempt_id)
            
            if attempt.status != BountyDeliveryAttempt.Status.NEW:
                return False, "Delivery attempt has already been reviewed"

            # Validate status
            if status not in BountyDeliveryAttempt.Status:
                return False, f"Invalid status: {status}"

            # Update attempt
            attempt.status = status
            attempt.review_message = review_message
            attempt.reviewed_by = reviewer
            attempt.save()

            # Handle claim and bounty status updates
            if status == BountyDeliveryAttempt.Status.APPROVED:
                return self._handle_approved_delivery(attempt)
            elif status == BountyDeliveryAttempt.Status.REJECTED:
                return self._handle_rejected_delivery(attempt)
            else:
                return True, "Delivery attempt updated successfully"

        except (BountyDeliveryAttempt.DoesNotExist, Person.DoesNotExist):
            return False, "Invalid delivery attempt or reviewer ID"
        except Exception as e:
            logger.error(f"Error reviewing delivery attempt: {str(e)}")
            return False, "Failed to review delivery attempt"

    @transaction.atomic
    def _handle_approved_delivery(
        self,
        attempt: BountyDeliveryAttempt
    ) -> Tuple[bool, str]:
        try:
            claim = attempt.bounty_claim
            bounty = claim.bounty

            # Update claim status
            claim.status = BountyClaim.Status.COMPLETED
            claim.save()

            # Update bounty status
            bounty.status = bounty.BountyStatus.COMPLETED
            bounty.save()

            # Process reward payment
            if bounty.reward_type == 'USD':
                success, message = self._process_usd_payment(claim)
            else:
                success, message = self._process_points_payment(claim)

            if not success:
                raise ValidationError(message)

            return True, "Delivery approved and reward processed"

        except Exception as e:
            logger.error(f"Error handling approved delivery: {str(e)}")
            return False, "Failed to process approved delivery"

    @transaction.atomic
    def _handle_rejected_delivery(
        self,
        attempt: BountyDeliveryAttempt
    ) -> Tuple[bool, str]:
        """Update related records when delivery is rejected"""
        try:
            # The claim remains active for new attempts
            return True, "Delivery rejected, awaiting new attempt"
        except Exception as e:
            logger.error(f"Error handling rejected delivery: {str(e)}")
            return False, "Failed to process rejected delivery"

    def _process_usd_payment(self, claim: BountyClaim) -> Tuple[bool, str]:
        """Process USD payment for completed bounty"""
        try:
            # Get wallet service
            ContributorWalletService = apps.get_model('commerce', 'ContributorWalletService')
            wallet_service = ContributorWalletService()

            amount = claim.accepted_bid.amount_in_usd_cents if claim.accepted_bid else claim.bounty.final_reward_in_usd_cents

            # Add funds to contributor wallet
            success, message = wallet_service.add_funds(
                person_id=claim.person.id,
                amount_cents=amount,
                description=f"Payment for bounty: {claim.bounty.title}",
                from_bounty_id=claim.bounty.id
            )

            return success, message

        except Exception as e:
            logger.error(f"Error processing USD payment: {str(e)}")
            return False, "Failed to process USD payment"

    def _process_points_payment(self, claim: BountyClaim) -> Tuple[bool, str]:
        """Process points payment for completed bounty"""
        try:
            from .person_service import PersonManagementService
            person_service = PersonManagementService()

            points = claim.accepted_bid.amount_in_points if claim.accepted_bid else claim.bounty.final_reward_in_points

            success, message = person_service.add_points(
                person_id=claim.person.id,
                points=points
            )

            return success, message

        except Exception as e:
            logger.error(f"Error processing points payment: {str(e)}")
            return False, "Failed to process points payment"

    def get_claim_status(self, claim_id: str) -> Dict:
        """Get detailed status information for a claim"""
        try:
            claim = BountyClaim.objects.get(id=claim_id)
            
            latest_attempt = claim.delivery_attempts.order_by('-created_at').first()
            
            return {
                'status': claim.status,
                'has_active_delivery': bool(latest_attempt and latest_attempt.status == BountyDeliveryAttempt.Status.NEW),
                'total_attempts': claim.delivery_attempts.count(),
                'expected_finish_date': claim.expected_finish_date,
                'latest_attempt_status': latest_attempt.status if latest_attempt else None,
                'latest_attempt_date': latest_attempt.created_at if latest_attempt else None
            }

        except BountyClaim.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting claim status: {str(e)}")
            return {}
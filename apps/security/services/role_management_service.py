import logging
from typing import Dict, Tuple, Optional
from django.db import transaction
from django.core.exceptions import ValidationError

from ..interfaces import RoleManagementServiceInterface
from ..models import (
    ProductRoleAssignment,
    OrganisationPersonRoleAssignment,
    Person
)

logger = logging.getLogger(__name__)

class RoleManagementService(RoleManagementServiceInterface):
    @transaction.atomic
    def assign_product_role(
        self,
        person_id: str,
        product_id: str,
        role: str
    ) -> Tuple[bool, str]:
        try:
            # Validate role assignment
            valid, message = self.validate_role_assignment(
                person_id=person_id,
                role=role,
                product_id=product_id
            )
            if not valid:
                return False, message

            # Create or update role assignment
            ProductRoleAssignment.objects.update_or_create(
                person_id=person_id,
                product_id=product_id,
                defaults={'role': role}
            )

            return True, "Product role assigned successfully"

        except Exception as e:
            logger.error(f"Error assigning product role: {str(e)}")
            return False, "Failed to assign product role"

    @transaction.atomic
    def assign_organisation_role(
        self,
        person_id: str,
        organisation_id: str,
        role: str
    ) -> Tuple[bool, str]:
        try:
            # Validate role assignment
            valid, message = self.validate_role_assignment(
                person_id=person_id,
                role=role,
                organisation_id=organisation_id
            )
            if not valid:
                return False, message

            # Create or update role assignment
            OrganisationPersonRoleAssignment.objects.update_or_create(
                person_id=person_id,
                organisation_id=organisation_id,
                defaults={'role': role}
            )

            return True, "Organisation role assigned successfully"

        except Exception as e:
            logger.error(f"Error assigning organisation role: {str(e)}")
            return False, "Failed to assign organisation role"

    def validate_role_assignment(
        self,
        person_id: str,
        role: str,
        product_id: Optional[str] = None,
        organisation_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            # Verify person exists
            if not Person.objects.filter(id=person_id).exists():
                return False, f"Invalid person_id: {person_id}"

            # Validate role based on type
            if product_id:
                if role not in dict(ProductRoleAssignment.ProductRoles.choices):
                    return False, f"Invalid product role: {role}"
            elif organisation_id:
                if role not in dict(OrganisationPersonRoleAssignment.OrganisationRoles.choices):
                    return False, f"Invalid organisation role: {role}"
            else:
                return False, "Either product_id or organisation_id must be provided"

            return True, "Role assignment is valid"

        except Exception as e:
            logger.error(f"Error validating role assignment: {str(e)}")
            return False, "Failed to validate role assignment"

    def get_user_roles(self, person_id: str)
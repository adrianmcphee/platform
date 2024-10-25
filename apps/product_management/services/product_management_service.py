import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.apps import apps

from ..interfaces import ProductManagementServiceInterface
from ..models import (
    Product, 
    ProductTree,
    ProductContributorAgreement,
    ProductContributorAgreementTemplate
)

logger = logging.getLogger(__name__)

class ProductManagementService(ProductManagementServiceInterface):
    @staticmethod
    def convert_youtube_link_to_embed(url: str) -> str:
        """Convert YouTube watch URL to embed URL"""
        if url:
            return url.replace("watch?v=", "embed/")
        return url

    def create_product(
        self,
        name: str,
        owner_id: str,
        owner_type: str,
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new product with ownership"""
        try:
            with transaction.atomic():
                # Validate unique slug
                slug = slugify(name)
                if Product.objects.filter(slug=slug).exists():
                    return False, f"Product name '{name}' is already taken", None

                # Convert YouTube URL if present
                if video_url := details.get('video_url'):
                    details['video_url'] = self.convert_youtube_link_to_embed(video_url)

                # Set owner based on type
                owner_kwargs = {}
                if owner_type == 'person':
                    Person = apps.get_model('talent', 'Person')
                    person = Person.objects.get(id=owner_id)
                    owner_kwargs['person'] = person
                elif owner_type == 'organisation':
                    Organisation = apps.get_model('commerce', 'Organisation')
                    org = Organisation.objects.get(id=owner_id)
                    owner_kwargs['organisation'] = org
                else:
                    return False, "Invalid owner type", None

                # Create product
                product = Product.objects.create(
                    name=name,
                    slug=slug,
                    short_description=details.get('short_description', ''),
                    full_description=details.get('full_description', ''),
                    website=details.get('website'),
                    detail_url=details.get('detail_url'),
                    video_url=details.get('video_url'),
                    visibility=details.get('visibility', Product.Visibility.ORG_ONLY),
                    **owner_kwargs
                )

                # Create default product tree if needed
                if details.get('create_tree', True):
                    ProductTree.objects.create(
                        name=f"{name} Tree",
                        product=product
                    )

                # Ensure point account exists
                self._ensure_point_account(product)

                return True, "Product created successfully", product.id

        except (Person.DoesNotExist, Organisation.DoesNotExist):
            return False, "Owner not found", None
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return False, "Failed to create product", None

    def update_product(
        self,
        product_id: str,
        details: Dict,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update product details"""
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)
                
                # Verify updater has permission
                if not self._can_modify_product(product, updater_id):
                    return False, "No permission to update product"

                # Convert YouTube URL if present
                if video_url := details.get('video_url'):
                    details['video_url'] = self.convert_youtube_link_to_embed(video_url)

                # Update basic fields
                updateable_fields = [
                    'name', 'short_description', 'full_description',
                    'website', 'detail_url', 'video_url', 'visibility'
                ]
                
                for field in updateable_fields:
                    if field in details:
                        setattr(product, field, details[field])

                # Handle ownership change if requested
                if new_owner_id := details.get('new_owner_id'):
                    if new_owner_type := details.get('new_owner_type'):
                        success, message = self._update_product_ownership(
                            product, new_owner_type, new_owner_id
                        )
                        if not success:
                            raise ValidationError(message)

                product.save()
                return True, "Product updated successfully"

        except Product.DoesNotExist:
            return False, "Product not found"
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            return False, "Failed to update product"

    def check_product_access(
        self,
        product_id: str,
        person_id: str
    ) -> Tuple[bool, str]:
        """Check if person has access to product based on visibility settings"""
        try:
            product = Product.objects.get(id=product_id)
            Person = apps.get_model('talent', 'Person')
            person = Person.objects.get(id=person_id)
            
            # Global products are accessible to all
            if product.visibility == Product.Visibility.GLOBAL:
                return True, "Product is globally accessible"

            # Check organization membership for ORG_ONLY products
            if product.visibility == Product.Visibility.ORG_ONLY:
                OrganisationPersonRoleAssignment = apps.get_model('security', 'OrganisationPersonRoleAssignment')
                if OrganisationPersonRoleAssignment.objects.filter(
                    person=person,
                    organisation=product.organisation
                ).exists():
                    return True, "Person has organization access"

            # Check direct product role for RESTRICTED products
            if product.visibility == Product.Visibility.RESTRICTED:
                ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
                if ProductRoleAssignment.objects.filter(
                    person=person,
                    product=product
                ).exists():
                    return True, "Person has product role access"

            return False, "No access to product"

        except (Product.DoesNotExist, Person.DoesNotExist):
            return False, "Product or person not found"
        except Exception as e:
            logger.error(f"Error checking product access: {str(e)}")
            return False, "Failed to check product access"

    def manage_points(
        self,
        product_id: str,
        points: int,
        action: str
    ) -> Tuple[bool, str]:
        """Manage product point balance"""
        try:
            with transaction.atomic():
                ProductPointAccount = apps.get_model('commerce', 'ProductPointAccount')
                product = Product.objects.select_for_update().get(id=product_id)
                
                point_account = ProductPointAccount.objects.select_for_update().get(product=product)

                if action == "add":
                    point_account.balance += points
                elif action == "deduct":
                    if point_account.balance < points:
                        return False, "Insufficient points balance"
                    point_account.balance -= points
                else:
                    return False, "Invalid action"

                point_account.save()
                return True, f"Points {action}ed successfully"

        except Product.DoesNotExist:
            return False, "Product not found"
        except ProductPointAccount.DoesNotExist:
            return False, "Point account not found"
        except Exception as e:
            logger.error(f"Error managing points: {str(e)}")
            return False, "Failed to manage points"

    def _ensure_point_account(self, product: Product) -> None:
        """Ensure product has a point account"""
        ProductPointAccount = apps.get_model('commerce', 'ProductPointAccount')
        ProductPointAccount.objects.get_or_create(product=product)

    def _can_modify_product(self, product: Product, person_id: str) -> bool:
        """Check if person can modify product"""
        try:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                person_id=person_id,
                product=product,
                role__in=['ADMIN', 'MANAGER']
            ).exists()
        except Exception:
            return False

    def _update_product_ownership(
        self,
        product: Product,
        owner_type: str,
        owner_id: str
    ) -> Tuple[bool, str]:
        """Update product ownership"""
        try:
            if owner_type == 'person':
                Person = apps.get_model('talent', 'Person')
                new_owner = Person.objects.get(id=owner_id)
                product.person = new_owner
                product.organisation = None
            elif owner_type == 'organisation':
                Organisation = apps.get_model('commerce', 'Organisation')
                new_owner = Organisation.objects.get(id=owner_id)
                product.organisation = new_owner
                product.person = None
            else:
                return False, "Invalid owner type"
            
            return True, "Ownership updated successfully"
            
        except (Person.DoesNotExist, Organisation.DoesNotExist):
            return False, "New owner not found"
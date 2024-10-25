import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone
from django.apps import apps

from ..interfaces import ProductSupportServiceInterface
from ..models import (
    Idea,
    Bug,
    IdeaVote,
    ContributorGuide,
    ProductContributorAgreement,
    ProductContributorAgreementTemplate,
    Product
)

logger = logging.getLogger(__name__)

class ProductSupportService(ProductSupportServiceInterface):
    def create_idea(
        self,
        product_id: str,
        person_id: str,
        title: str,
        description: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create new product idea"""
        try:
            with transaction.atomic():
                # Validate product access
                product = Product.objects.get(id=product_id)
                Person = apps.get_model('talent', 'Person')
                person = Person.objects.get(id=person_id)

                if not self._can_access_product(product, person_id):
                    return False, "No access to product", None

                # Create idea
                idea = Idea.objects.create(
                    product=product,
                    person=person,
                    title=title,
                    description=description
                )

                return True, "Idea created successfully", idea.id

        except (Product.DoesNotExist, Person.DoesNotExist):
            return False, "Product or person not found", None
        except Exception as e:
            logger.error(f"Error creating idea: {str(e)}")
            return False, str(e), None

    def create_bug_report(
        self,
        product_id: str,
        person_id: str,
        title: str,
        description: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create new bug report"""
        try:
            with transaction.atomic():
                product = Product.objects.get(id=product_id)
                Person = apps.get_model('talent', 'Person')
                person = Person.objects.get(id=person_id)

                if not self._can_access_product(product, person_id):
                    return False, "No access to product", None

                bug = Bug.objects.create(
                    product=product,
                    person=person,
                    title=title,
                    description=description
                )

                return True, "Bug report created successfully", bug.id

        except (Product.DoesNotExist, Person.DoesNotExist):
            return False, "Product or person not found", None
        except Exception as e:
            logger.error(f"Error creating bug report: {str(e)}")
            return False, str(e), None

    def process_vote(
        self,
        idea_id: str,
        voter_id: str
    ) -> Tuple[bool, str, int]:
        """Process vote on idea and return updated count"""
        try:
            with transaction.atomic():
                idea = Idea.objects.get(id=idea_id)
                Person = apps.get_model('talent', 'Person')
                voter = Person.objects.get(id=voter_id)

                if not self._can_access_product(idea.product, voter_id):
                    return False, "No access to product", 0

                # Toggle vote
                vote, created = IdeaVote.objects.get_or_create(
                    idea=idea,
                    voter=voter
                )

                if not created:
                    vote.delete()

                # Get updated vote count
                vote_count = IdeaVote.objects.filter(idea=idea).count()
                return True, "Vote processed successfully", vote_count

        except (Idea.DoesNotExist, Person.DoesNotExist):
            return False, "Idea or voter not found", 0
        except Exception as e:
            logger.error(f"Error processing vote: {str(e)}")
            return False, str(e), 0

    def manage_contributor_agreement(
        self,
        product_id: str,
        person_id: str,
        agreement_id: str,
        action: str
    ) -> Tuple[bool, str]:
        """Manage contributor agreements"""
        try:
            with transaction.atomic():
                template = ProductContributorAgreementTemplate.objects.get(
                    id=agreement_id,
                    product_id=product_id
                )
                Person = apps.get_model('talent', 'Person')
                person = Person.objects.get(id=person_id)

                if action == "accept":
                    # Check if already accepted
                    if ProductContributorAgreement.objects.filter(
                        agreement_template=template,
                        person=person
                    ).exists():
                        return False, "Agreement already accepted"

                    # Create agreement
                    ProductContributorAgreement.objects.create(
                        agreement_template=template,
                        person=person
                    )
                    return True, "Agreement accepted successfully"

                elif action == "revoke":
                    # Only product admins can revoke agreements
                    if not self._is_product_admin(product_id, person_id):
                        return False, "No permission to revoke agreements"

                    agreements = ProductContributorAgreement.objects.filter(
                        agreement_template=template,
                        person=person
                    )
                    if not agreements.exists():
                        return False, "No agreement found to revoke"

                    agreements.delete()
                    return True, "Agreement revoked successfully"

                return False, "Invalid action"

        except (ProductContributorAgreementTemplate.DoesNotExist, Person.DoesNotExist):
            return False, "Template or person not found"
        except Exception as e:
            logger.error(f"Error managing agreement: {str(e)}")
            return False, str(e)

    def create_contributor_guide(
        self,
        product_id: str,
        creator_id: str,
        title: str,
        description: str,
        skill_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """Create new contributor guide"""
        try:
            with transaction.atomic():
                if not self._is_product_admin(product_id, creator_id):
                    return False, "No permission to create guides", None

                product = Product.objects.get(id=product_id)
                
                guide_data = {
                    'product': product,
                    'title': title,
                    'description': description
                }

                if skill_id:
                    Skill = apps.get_model('talent', 'Skill')
                    guide_data['skill'] = Skill.objects.get(id=skill_id)

                guide = ContributorGuide.objects.create(**guide_data)
                return True, "Guide created successfully", guide.id

        except (Product.DoesNotExist, Skill.DoesNotExist):
            return False, "Product or skill not found", None
        except Exception as e:
            logger.error(f"Error creating guide: {str(e)}")
            return False, str(e), None

    def get_product_ideas(
        self,
        product_id: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get filtered ideas with votes"""
        try:
            queryset = Idea.objects.filter(product_id=product_id)

            if filters:
                if person_id := filters.get('person_id'):
                    queryset = queryset.filter(person_id=person_id)
                
                if search := filters.get('search'):
                    queryset = queryset.filter(
                        Q(title__icontains=search) |
                        Q(description__icontains=search)
                    )

            # Annotate with vote counts
            queryset = queryset.annotate(vote_count=Count('ideavote'))

            ideas = []
            for idea in queryset:
                ideas.append({
                    'id': idea.id,
                    'title': idea.title,
                    'description': idea.description,
                    'person': {
                        'id': idea.person.id,
                        'name': idea.person.full_name
                    },
                    'vote_count': idea.vote_count,
                    'created_at': idea.created_at.isoformat()
                })

            return ideas

        except Exception as e:
            logger.error(f"Error getting ideas: {str(e)}")
            return []

    def get_product_bugs(
        self,
        product_id: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get filtered bug reports"""
        try:
            queryset = Bug.objects.filter(product_id=product_id)

            if filters:
                if person_id := filters.get('person_id'):
                    queryset = queryset.filter(person_id=person_id)
                
                if search := filters.get('search'):
                    queryset = queryset.filter(
                        Q(title__icontains=search) |
                        Q(description__icontains=search)
                    )

            bugs = []
            for bug in queryset:
                bugs.append({
                    'id': bug.id,
                    'title': bug.title,
                    'description': bug.description,
                    'person': {
                        'id': bug.person.id,
                        'name': bug.person.full_name
                    },
                    'created_at': bug.created_at.isoformat()
                })

            return bugs

        except Exception as e:
            logger.error(f"Error getting bugs: {str(e)}")
            return []

    def _can_access_product(self, product: Product, person_id: str) -> bool:
        """Check if person has access to product"""
        if product.visibility == Product.Visibility.GLOBAL:
            return True

        if product.visibility == Product.Visibility.ORG_ONLY:
            OrganisationPersonRoleAssignment = apps.get_model('security', 'OrganisationPersonRoleAssignment')
            return OrganisationPersonRoleAssignment.objects.filter(
                person_id=person_id,
                organisation=product.organisation
            ).exists()

        if product.visibility == Product.Visibility.RESTRICTED:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                person_id=person_id,
                product=product
            ).exists()

        return False

    def _is_product_admin(self, product_id: str, person_id: str) -> bool:
        """Check if person is product admin"""
        try:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                product_id=product_id,
                person_id=person_id,
                role='ADMIN'
            ).exists()
        except Exception:
            return False

    def get_contributor_status(
        self,
        product_id: str,
        person_id: str
    ) -> Dict:
        """Get person's contributor status for product"""
        try:
            # Get latest agreement
            agreement = ProductContributorAgreement.objects.filter(
                agreement_template__product_id=product_id,
                person_id=person_id
            ).select_related('agreement_template').first()

            # Get contribution stats
            contribution_stats = {
                'ideas': Idea.objects.filter(
                    product_id=product_id,
                    person_id=person_id
                ).count(),
                'bugs': Bug.objects.filter(
                    product_id=product_id,
                    person_id=person_id
                ).count(),
                'voted_ideas': IdeaVote.objects.filter(
                    voter_id=person_id,
                    idea__product_id=product_id
                ).count()
            }

            return {
                'has_agreement': bool(agreement),
                'agreement_date': agreement.created_at.isoformat() if agreement else None,
                'agreement_version': agreement.agreement_template.title if agreement else None,
                'stats': contribution_stats
            }

        except Exception as e:
            logger.error(f"Error getting contributor status: {str(e)}")
            return {
                'has_agreement': False,
                'agreement_date': None,
                'agreement_version': None,
                'stats': {
                    'ideas': 0,
                    'bugs': 0,
                    'voted_ideas': 0
                }
            }
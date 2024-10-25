import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.apps import apps

from ..interfaces import PortalServiceInterface
from ..models import (
    Product,
    Challenge,
    Bounty,
    ProductContributorAgreement
)

logger = logging.getLogger(__name__)

class PortalService(PortalServiceInterface):
    def __init__(
        self,
        product_service,
        challenge_service,
        bounty_service,
        product_support_service
    ):
        self.product_service = product_service
        self.challenge_service = challenge_service
        self.bounty_service = bounty_service
        self.product_support_service = product_support_service

    def get_user_dashboard(
        self,
        person_id: str
    ) -> Dict:
        """Get user dashboard data"""
        try:
            Person = apps.get_model('talent', 'Person')
            person = Person.objects.get(id=person_id)

            # Get role assignments
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            role_assignments = ProductRoleAssignment.objects.filter(
                person=person
            ).exclude(
                role='CONTRIBUTOR'
            ).select_related('product')

            # Get active claims
            BountyClaim = apps.get_model('talent', 'BountyClaim')
            active_claims = BountyClaim.objects.filter(
                person=person,
                status='ACTIVE'
            ).select_related('bounty', 'bounty__challenge', 'bounty__challenge__product')

            # Get recent activity
            recent_activity = self._get_person_activity(person_id)

            return {
                'person': {
                    'id': person.id,
                    'name': person.full_name,
                    'points': person.points,
                    'status': person.points_status
                },
                'product_roles': [
                    {
                        'product_id': assignment.product.id,
                        'product_name': assignment.product.name,
                        'role': assignment.role
                    }
                    for assignment in role_assignments
                ],
                'active_claims': [
                    {
                        'id': claim.id,
                        'bounty_title': claim.bounty.title,
                        'product_name': claim.bounty.challenge.product.name,
                        'created_at': claim.created_at.isoformat()
                    }
                    for claim in active_claims
                ],
                'recent_activity': recent_activity,
                'contribution_stats': self._get_contribution_stats(person_id)
            }

        except Person.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting user dashboard: {str(e)}")
            return {}

    def get_product_dashboard(
        self,
        product_id: str,
        person_id: str
    ) -> Dict:
        """Get product dashboard data"""
        try:
            product = Product.objects.get(id=product_id)

            # Get challenge stats
            challenge_stats = Challenge.objects.filter(
                product=product
            ).aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(status='ACTIVE')),
                completed=Count('id', filter=Q(status='COMPLETED'))
            )

            # Get bounty stats
            bounty_stats = Bounty.objects.filter(
                challenge__product=product
            ).aggregate(
                total=Count('id'),
                in_progress=Count('id', filter=Q(status='IN_PROGRESS')),
                completed=Count('id', filter=Q(status='COMPLETED')),
                total_usd=Sum('reward_in_usd_cents', filter=Q(reward_type='USD')),
                total_points=Sum('reward_in_points', filter=Q(reward_type='Points'))
            )

            return {
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'visibility': product.visibility,
                    'point_balance': product.point_balance
                },
                'challenge_stats': challenge_stats,
                'bounty_stats': bounty_stats,
                'pending_reviews': self._get_pending_reviews(product_id),
                'recent_activity': self._get_product_activity(product_id),
                'user_role': self._get_user_role(product_id, person_id)
            }

        except Product.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting product dashboard: {str(e)}")
            return {}

    def get_bounty_management(
        self,
        person_id: str,
        filters: Optional[Dict] = None
    ) -> Dict:
        """Get bounty management overview"""
        try:
            BountyClaim = apps.get_model('talent', 'BountyClaim')
            claims = BountyClaim.objects.filter(
                person_id=person_id
            ).select_related(
                'bounty',
                'bounty__challenge'
            )

            if filters:
                if status := filters.get('status'):
                    claims = claims.filter(status=status)

            return {
                'active_claims': [
                    {
                        'id': claim.id,
                        'bounty_title': claim.bounty.title,
                        'challenge_title': claim.bounty.challenge.title,
                        'status': claim.status,
                        'created_at': claim.created_at.isoformat()
                    }
                    for claim in claims
                ],
                'completion_stats': self._get_completion_stats(person_id),
                'pending_deliveries': self._get_pending_deliveries(person_id)
            }

        except Exception as e:
            logger.error(f"Error getting bounty management: {str(e)}")
            return {}

    def get_user_management(
        self,
        product_id: str,
        person_id: str,
        filters: Optional[Dict] = None
    ) -> Dict:
        """Get user management data"""
        try:
            if not self._can_manage_users(product_id, person_id):
                return {}

            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            role_assignments = ProductRoleAssignment.objects.filter(
                product_id=product_id
            ).select_related('person')

            if filters:
                if role := filters.get('role'):
                    role_assignments = role_assignments.filter(role=role)

            return {
                'role_assignments': [
                    {
                        'person_id': assignment.person.id,
                        'person_name': assignment.person.full_name,
                        'role': assignment.role,
                        'assigned_at': assignment.created_at.isoformat()
                    }
                    for assignment in role_assignments
                ],
                'contribution_metrics': self._get_contribution_metrics(product_id)
            }

        except Exception as e:
            logger.error(f"Error getting user management: {str(e)}")
            return {}

    def get_work_review_queue(
        self,
        product_id: str,
        reviewer_id: str
    ) -> Dict:
        """Get review queue data"""
        try:
            if not self._can_review_work(product_id, reviewer_id):
                return {}

            BountyDeliveryAttempt = apps.get_model('talent', 'BountyDeliveryAttempt')
            pending_reviews = BountyDeliveryAttempt.objects.filter(
                bounty_claim__bounty__challenge__product_id=product_id,
                status='NEW'
            ).select_related(
                'bounty_claim__person',
                'bounty_claim__bounty'
            )

            return {
                'pending_reviews': [
                    {
                        'id': review.id,
                        'delivery_message': review.delivery_message,
                        'submitter_name': review.bounty_claim.person.full_name,
                        'bounty_title': review.bounty_claim.bounty.title,
                        'submitted_at': review.created_at.isoformat()
                    }
                    for review in pending_reviews
                ],
                'review_stats': self._get_review_stats(product_id, reviewer_id)
            }

        except Exception as e:
            logger.error(f"Error getting review queue: {str(e)}")
            return {}

    def get_contribution_overview(
        self,
        person_id: str
    ) -> Dict:
        """Get contributor overview"""
        try:
            Person = apps.get_model('talent', 'Person')
            person = Person.objects.get(id=person_id)

            return {
                'active_contributions': self._get_active_contributions(person_id),
                'historical_stats': self._get_historical_stats(person_id),
                'earned_rewards': self._get_earned_rewards(person_id),
                'product_participation': self._get_product_participation(person_id)
            }

        except Person.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting contribution overview: {str(e)}")
            return {}

    # Private helper methods...
    def _get_person_activity(self, person_id: str) -> List[Dict]:
        """Get recent activity for person"""
        # Implementation details...
        pass

    def _get_contribution_stats(self, person_id: str) -> Dict:
        """Get contribution statistics"""
        # Implementation details...
        pass

    def _get_pending_reviews(self, product_id: str) -> List[Dict]:
        """Get pending reviews for product"""
        # Implementation details...
        pass

    def _get_product_activity(self, product_id: str) -> List[Dict]:
        """Get recent activity for product"""
        # Implementation details...
        pass

    def _can_manage_users(self, product_id: str, person_id: str) -> bool:
        """Check if person can manage users"""
        # Implementation details...
        pass

    def _can_review_work(self, product_id: str, person_id: str) -> bool:
        """Check if person can review work"""
        # Implementation details...
        pass

    # Additional helper methods...
import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.apps import apps

from ..interfaces import InitiativeServiceInterface
from ..models import (
    Initiative,
    Challenge,
    Product,
    Bounty
)

logger = logging.getLogger(__name__)

class InitiativeService(InitiativeServiceInterface):
    def create_initiative(
        self,
        product_id: str,
        name: str,
        description: str,
        creator_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new initiative"""
        try:
            with transaction.atomic():
                # Validate product and creator access
                product = Product.objects.get(id=product_id)
                
                if not self._can_manage_initiative(product_id, creator_id):
                    return False, "No permission to create initiative", None

                # Convert video URL if present
                video_url = None
                if video_url:
                    from ..services import ProductService
                    video_url = ProductService.convert_youtube_link_to_embed(video_url)

                # Create initiative
                initiative = Initiative.objects.create(
                    product=product,
                    name=name,
                    description=description,
                    status=Initiative.InitiativeStatus.DRAFT,
                    video_url=video_url
                )

                return True, "Initiative created successfully", initiative.id

        except Product.DoesNotExist:
            return False, "Product not found", None
        except Exception as e:
            logger.error(f"Error creating initiative: {str(e)}")
            return False, str(e), None

    def get_initiative_stats(
        self,
        initiative_id: str
    ) -> Dict:
        """Get initiative statistics including points and challenge status"""
        try:
            initiative = Initiative.objects.get(id=initiative_id)
            challenges = Challenge.objects.filter(initiative=initiative)

            # Get challenge counts by status
            challenge_stats = challenges.aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(status=Challenge.ChallengeStatus.ACTIVE)),
                completed=Count('id', filter=Q(status=Challenge.ChallengeStatus.COMPLETED)),
                blocked=Count('id', filter=Q(status=Challenge.ChallengeStatus.BLOCKED))
            )

            # Calculate total rewards
            bounties = Bounty.objects.filter(challenge__initiative=initiative)
            reward_stats = {
                'total_usd_cents': bounties.filter(
                    reward_type='USD'
                ).aggregate(
                    total=Sum('reward_in_usd_cents')
                )['total'] or 0,
                'total_points': bounties.filter(
                    reward_type='Points'
                ).aggregate(
                    total=Sum('reward_in_points')
                )['total'] or 0
            }

            # Get completion percentage
            total_challenges = challenge_stats['total'] or 1  # Avoid division by zero
            completion_percentage = (challenge_stats['completed'] / total_challenges) * 100

            return {
                'id': initiative.id,
                'name': initiative.name,
                'status': initiative.status,
                'challenges': challenge_stats,
                'rewards': reward_stats,
                'completion_percentage': round(completion_percentage, 1),
                'last_updated': initiative.updated_at.isoformat()
            }

        except Initiative.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting initiative stats: {str(e)}")
            return {}

    def manage_challenges(
        self,
        initiative_id: str,
        challenge_ids: List[str],
        action: str
    ) -> Tuple[bool, str]:
        """Manage challenges within initiative"""
        try:
            with transaction.atomic():
                initiative = Initiative.objects.select_for_update().get(id=initiative_id)
                challenges = Challenge.objects.filter(id__in=challenge_ids)

                if not challenges.exists():
                    return False, "No valid challenges provided"

                # Verify all challenges belong to same product as initiative
                if challenges.filter(product_id=initiative.product_id).count() != len(challenge_ids):
                    return False, "Some challenges belong to different products"

                if action == "add":
                    # Add challenges to initiative
                    challenges.update(initiative=initiative)
                    
                    # Update initiative status if needed
                    self._update_initiative_status(initiative)
                    
                    return True, f"Added {len(challenge_ids)} challenges to initiative"

                elif action == "remove":
                    # Remove challenges from initiative
                    challenges.update(initiative=None)
                    
                    # Update initiative status
                    self._update_initiative_status(initiative)
                    
                    return True, f"Removed {len(challenge_ids)} challenges from initiative"

                else:
                    return False, "Invalid action"

        except Initiative.DoesNotExist:
            return False, "Initiative not found"
        except Exception as e:
            logger.error(f"Error managing initiative challenges: {str(e)}")
            return False, str(e)

    def update_status(
        self,
        initiative_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update initiative status"""
        try:
            with transaction.atomic():
                initiative = Initiative.objects.select_for_update().get(id=initiative_id)

                if not self._can_manage_initiative(initiative.product_id, updater_id):
                    return False, "No permission to update initiative status"

                if not self._is_valid_status_transition(initiative.status, new_status):
                    return False, f"Invalid status transition from {initiative.status} to {new_status}"

                old_status = initiative.status
                initiative.status = new_status
                initiative.save()

                # Handle status-specific logic
                if new_status == Initiative.InitiativeStatus.ACTIVE:
                    self._activate_initiative_challenges(initiative)
                elif new_status == Initiative.InitiativeStatus.COMPLETED:
                    self._complete_initiative_challenges(initiative)
                elif new_status == Initiative.InitiativeStatus.CANCELLED:
                    self._cancel_initiative_challenges(initiative)

                return True, f"Status updated from {old_status} to {new_status}"

        except Initiative.DoesNotExist:
            return False, "Initiative not found"
        except Exception as e:
            logger.error(f"Error updating initiative status: {str(e)}")
            return False, str(e)

    def _can_manage_initiative(self, product_id: str, person_id: str) -> bool:
        """Check if person can manage initiatives for product"""
        try:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                product_id=product_id,
                person_id=person_id,
                role__in=['ADMIN', 'MANAGER']
            ).exists()
        except Exception:
            return False

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate initiative status transition"""
        valid_transitions = {
            Initiative.InitiativeStatus.DRAFT: [
                Initiative.InitiativeStatus.ACTIVE,
                Initiative.InitiativeStatus.CANCELLED
            ],
            Initiative.InitiativeStatus.ACTIVE: [
                Initiative.InitiativeStatus.COMPLETED,
                Initiative.InitiativeStatus.CANCELLED
            ],
            Initiative.InitiativeStatus.COMPLETED: [
                Initiative.InitiativeStatus.ACTIVE
            ],
            Initiative.InitiativeStatus.CANCELLED: [
                Initiative.InitiativeStatus.DRAFT
            ]
        }
        return new_status in valid_transitions.get(current_status, [])

    def _update_initiative_status(self, initiative: Initiative) -> None:
        """Update initiative status based on challenges"""
        if not initiative.challenge_set.exists():
            return

        # Get challenge counts
        challenges = initiative.challenge_set.all()
        total = challenges.count()
        completed = challenges.filter(status=Challenge.ChallengeStatus.COMPLETED).count()
        cancelled = challenges.filter(status=Challenge.ChallengeStatus.CANCELLED).count()
        active = challenges.filter(status=Challenge.ChallengeStatus.ACTIVE).count()

        # Determine status
        if completed == total:
            new_status = Initiative.InitiativeStatus.COMPLETED
        elif cancelled == total:
            new_status = Initiative.InitiativeStatus.CANCELLED
        elif active > 0:
            new_status = Initiative.InitiativeStatus.ACTIVE
        else:
            new_status = Initiative.InitiativeStatus.DRAFT

        if initiative.status != new_status:
            initiative.status = new_status
            initiative.save()

    def _activate_initiative_challenges(self, initiative: Initiative) -> None:
        """Activate draft challenges when initiative is activated"""
        Challenge.objects.filter(
            initiative=initiative,
            status=Challenge.ChallengeStatus.DRAFT
        ).update(status=Challenge.ChallengeStatus.ACTIVE)

    def _complete_initiative_challenges(self, initiative: Initiative) -> None:
        """Complete remaining challenges when initiative is completed"""
        Challenge.objects.filter(
            initiative=initiative
        ).exclude(
            status__in=[
                Challenge.ChallengeStatus.COMPLETED,
                Challenge.ChallengeStatus.CANCELLED
            ]
        ).update(status=Challenge.ChallengeStatus.COMPLETED)

    def _cancel_initiative_challenges(self, initiative: Initiative) -> None:
        """Cancel non-completed challenges when initiative is cancelled"""
        Challenge.objects.filter(
            initiative=initiative
        ).exclude(
            status=Challenge.ChallengeStatus.COMPLETED
        ).update(status=Challenge.ChallengeStatus.CANCELLED)

    def get_filtered_initiatives(
        self,
        product_id: str,
        filters: Dict
    ) -> List[Dict]:
        """Get filtered initiatives with stats"""
        try:
            queryset = Initiative.objects.filter(product_id=product_id)

            # Apply status filter
            if statuses := filters.get('status'):
                queryset = queryset.filter(status__in=statuses)

            # Apply search
            if search_term := filters.get('search'):
                queryset = queryset.filter(
                    Q(name__icontains=search_term) |
                    Q(description__icontains=search_term)
                )

            # Get stats for each initiative
            initiatives = []
            for initiative in queryset:
                stats = self.get_initiative_stats(initiative.id)
                initiatives.append({
                    'id': initiative.id,
                    'name': initiative.name,
                    'description': initiative.description,
                    'status': initiative.status,
                    'stats': stats,
                    'created_at': initiative.created_at.isoformat(),
                    'updated_at': initiative.updated_at.isoformat()
                })

            return initiatives

        except Exception as e:
            logger.error(f"Error filtering initiatives: {str(e)}")
            return []
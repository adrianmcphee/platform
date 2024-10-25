import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Case, When, Value, IntegerField
from django.utils import timezone
from django.apps import apps

from ..interfaces import ChallengeServiceInterface
from ..models import (
    Challenge,
    Product,
    Initiative,
    ChallengeDependency,
    Bounty
)

logger = logging.getLogger(__name__)

class ChallengeService(ChallengeServiceInterface):
    def create_challenge(
        self,
        product_id: str,
        title: str,
        description: str,
        initiative_id: Optional[str],
        creator_id: str,
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new challenge"""
        try:
            with transaction.atomic():
                # Validate product and creator access
                product = Product.objects.get(id=product_id)
                Person = apps.get_model('talent', 'Person')
                creator = Person.objects.get(id=creator_id)

                ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
                if not ProductRoleAssignment.objects.filter(
                    person=creator,
                    product=product,
                    role__in=['ADMIN', 'MANAGER']
                ).exists():
                    return False, "No permission to create challenge", None

                # Handle initiative if provided
                initiative = None
                if initiative_id:
                    initiative = Initiative.objects.get(id=initiative_id)
                    if initiative.product_id != product_id:
                        return False, "Initiative does not belong to product", None

                # Convert video URL if present
                if video_url := details.get('video_url'):
                    from . import ProductService
                    details['video_url'] = ProductService.convert_youtube_link_to_embed(video_url)

                # Create challenge
                challenge = Challenge.objects.create(
                    product=product,
                    initiative=initiative,
                    title=title,
                    description=description,
                    short_description=details.get('short_description', ''),
                    status=Challenge.ChallengeStatus.DRAFT,
                    priority=details.get('priority', Challenge.ChallengePriority.MEDIUM),
                    blocked=details.get('blocked', False),
                    featured=details.get('featured', False),
                    auto_approve_bounty_claims=details.get('auto_approve_bounty_claims', False),
                    video_url=details.get('video_url'),
                    product_area_id=details.get('product_area_id')
                )

                # Handle dependencies if provided
                if dependencies := details.get('dependencies', []):
                    self._create_dependencies(challenge, dependencies)

                return True, "Challenge created successfully", challenge.id

        except (Product.DoesNotExist, Person.DoesNotExist, Initiative.DoesNotExist):
            return False, "Referenced entity not found", None
        except Exception as e:
            logger.error(f"Error creating challenge: {str(e)}")
            return False, "Failed to create challenge", None

    def update_status(
        self,
        challenge_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update challenge status with validation"""
        try:
            with transaction.atomic():
                challenge = Challenge.objects.select_for_update().get(id=challenge_id)
                
                # Validate status transition
                if not self._is_valid_status_transition(challenge.status, new_status):
                    return False, f"Invalid status transition from {challenge.status} to {new_status}"

                # Check permissions
                if not self._can_update_status(challenge, updater_id, new_status):
                    return False, "No permission to update status"

                # Check dependencies for activation
                if new_status == Challenge.ChallengeStatus.ACTIVE:
                    if not self._can_activate_challenge(challenge):
                        return False, "Blocking dependencies not completed"

                # Update status
                old_status = challenge.status
                challenge.status = new_status
                
                # Handle automatic status changes
                if new_status == Challenge.ChallengeStatus.COMPLETED:
                    self._handle_completion(challenge)
                elif new_status == Challenge.ChallengeStatus.CANCELLED:
                    self._handle_cancellation(challenge)

                challenge.save()

                # Update initiative status if needed
                if challenge.initiative:
                    self._update_initiative_status(challenge.initiative)

                return True, f"Status updated from {old_status} to {new_status}"

        except Challenge.DoesNotExist:
            return False, "Challenge not found"
        except Exception as e:
            logger.error(f"Error updating challenge status: {str(e)}")
            return False, "Failed to update status"

    def get_filtered_challenges(
        self,
        product_id: str,
        filters: Dict
    ) -> List[Dict]:
        """Get filtered and ordered challenges"""
        try:
            queryset = Challenge.objects.filter(product_id=product_id)

            # Apply status filters
            if statuses := filters.get('statuses'):
                queryset = queryset.filter(status__in=statuses)

            # Apply priority filters
            if priorities := filters.get('priorities'):
                queryset = queryset.filter(priority__in=priorities)

            # Apply initiative filter
            if initiative_id := filters.get('initiative_id'):
                queryset = queryset.filter(initiative_id=initiative_id)

            # Apply product area filter
            if product_area_id := filters.get('product_area_id'):
                queryset = queryset.filter(product_area_id=product_area_id)

            # Apply search
            if search_term := filters.get('search'):
                queryset = queryset.filter(title__icontains=search_term)

            # Apply custom ordering
            queryset = queryset.annotate(
                custom_order=Case(
                    When(status=Challenge.ChallengeStatus.ACTIVE, then=Value(0)),
                    When(status=Challenge.ChallengeStatus.BLOCKED, then=Value(1)),
                    When(status=Challenge.ChallengeStatus.COMPLETED, then=Value(2)),
                    When(status=Challenge.ChallengeStatus.CANCELLED, then=Value(3)),
                    default=Value(4),
                    output_field=IntegerField(),
                )
            ).order_by('custom_order', '-created_at')

            # Return serialized results
            return [self._serialize_challenge(challenge) for challenge in queryset]

        except Exception as e:
            logger.error(f"Error filtering challenges: {str(e)}")
            return []

    def calculate_rewards(
        self,
        challenge_id: str
    ) -> Dict:
        """Calculate total rewards for challenge"""
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            
            bounties = Bounty.objects.filter(challenge=challenge)
            total_usd_cents = bounties.filter(
                reward_type='USD'
            ).aggregate(
                total=Sum('reward_in_usd_cents')
            )['total'] or 0
            
            total_points = bounties.filter(
                reward_type='Points'
            ).aggregate(
                total=Sum('reward_in_points')
            )['total'] or 0

            return {
                'total_usd_cents': total_usd_cents,
                'total_points': total_points,
                'total_bounties': bounties.count()
            }

        except Challenge.DoesNotExist:
            return {'total_usd_cents': 0, 'total_points': 0, 'total_bounties': 0}
        except Exception as e:
            logger.error(f"Error calculating rewards: {str(e)}")
            return {'total_usd_cents': 0, 'total_points': 0, 'total_bounties': 0}

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """Validate status transition"""
        valid_transitions = {
            Challenge.ChallengeStatus.DRAFT: [
                Challenge.ChallengeStatus.ACTIVE,
                Challenge.ChallengeStatus.CANCELLED
            ],
            Challenge.ChallengeStatus.ACTIVE: [
                Challenge.ChallengeStatus.BLOCKED,
                Challenge.ChallengeStatus.COMPLETED,
                Challenge.ChallengeStatus.CANCELLED
            ],
            Challenge.ChallengeStatus.BLOCKED: [
                Challenge.ChallengeStatus.ACTIVE,
                Challenge.ChallengeStatus.CANCELLED
            ],
            Challenge.ChallengeStatus.COMPLETED: [
                Challenge.ChallengeStatus.ACTIVE
            ],
            Challenge.ChallengeStatus.CANCELLED: [
                Challenge.ChallengeStatus.DRAFT
            ]
        }
        return new_status in valid_transitions.get(current_status, [])

    def _can_update_status(
        self,
        challenge: Challenge,
        updater_id: str,
        new_status: str
    ) -> bool:
        """Check if user can update to new status"""
        try:
            ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
            return ProductRoleAssignment.objects.filter(
                person_id=updater_id,
                product=challenge.product,
                role__in=['ADMIN', 'MANAGER']
            ).exists()
        except Exception:
            return False

    def _can_activate_challenge(self, challenge: Challenge) -> bool:
        """Check if challenge can be activated"""
        dependencies = ChallengeDependency.objects.filter(
            subsequent_challenge=challenge
        ).select_related('preceding_challenge')
        
        return all(
            dep.preceding_challenge.status == Challenge.ChallengeStatus.COMPLETED
            for dep in dependencies
        )

    def _handle_completion(self, challenge: Challenge) -> None:
        """Handle challenge completion"""
        # Update bounties
        Bounty.objects.filter(
            challenge=challenge,
            status__in=[
                Bounty.BountyStatus.DRAFT,
                Bounty.BountyStatus.OPEN
            ]
        ).update(status=Bounty.BountyStatus.CANCELLED)

    def _handle_cancellation(self, challenge: Challenge) -> None:
        """Handle challenge cancellation"""
        # Cancel all non-completed bounties
        Bounty.objects.filter(
            challenge=challenge
        ).exclude(
            status__in=[Bounty.BountyStatus.COMPLETED]
        ).update(status=Bounty.BountyStatus.CANCELLED)

    def _create_dependencies(self, challenge: Challenge, dependency_ids: List[str]) -> None:
        """Create challenge dependencies"""
        for dep_id in dependency_ids:
            try:
                preceding = Challenge.objects.get(id=dep_id)
                if preceding.product_id != challenge.product_id:
                    logger.warning(f"Skipping cross-product dependency: {dep_id}")
                    continue
                ChallengeDependency.objects.create(
                    preceding_challenge=preceding,
                    subsequent_challenge=challenge
                )
            except Challenge.DoesNotExist:
                logger.warning(f"Skipping non-existent dependency: {dep_id}")

    def _update_initiative_status(self, initiative: Initiative) -> None:
        """Update initiative status based on challenges"""
        challenges = Challenge.objects.filter(initiative=initiative)
        
        if not challenges.exists():
            return

        if challenges.filter(status=Challenge.ChallengeStatus.ACTIVE).exists():
            initiative.status = Initiative.InitiativeStatus.ACTIVE
        elif all(c.status == Challenge.ChallengeStatus.COMPLETED for c in challenges):
            initiative.status = Initiative.InitiativeStatus.COMPLETED
        elif all(c.status == Challenge.ChallengeStatus.CANCELLED for c in challenges):
            initiative.status = Initiative.InitiativeStatus.CANCELLED
            
        initiative.save()

    def _serialize_challenge(self, challenge: Challenge) -> Dict:
        """Serialize challenge for API response"""
        rewards = self.calculate_rewards(challenge.id)
        return {
            'id': challenge.id,
            'title': challenge.title,
            'short_description': challenge.short_description,
            'status': challenge.status,
            'priority': challenge.priority,
            'blocked': challenge.blocked,
            'featured': challenge.featured,
            'initiative_id': challenge.initiative_id,
            'product_area_id': challenge.product_area_id,
            'total_usd_cents': rewards['total_usd_cents'],
            'total_points': rewards['total_points'],
            'total_bounties': rewards['total_bounties'],
            'created_at': challenge.created_at.isoformat(),
            'updated_at': challenge.updated_at.isoformat()
        }
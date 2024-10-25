import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.apps import apps

from ..interfaces import CompetitionServiceInterface
from ..models import (
    Competition,
    CompetitionEntry,
    CompetitionEntryRating,
    Product,
    Bounty
)

logger = logging.getLogger(__name__)

class CompetitionService(CompetitionServiceInterface):
    def create_competition(
        self,
        product_id: str,
        title: str,
        description: str,
        creator_id: str,
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new competition"""
        try:
            with transaction.atomic():
                # Validate product and creator access
                product = Product.objects.get(id=product_id)
                if not self._can_manage_competitions(product_id, creator_id):
                    return False, "No permission to create competitions", None

                # Convert video URL if present
                if video_url := details.get('video_url'):
                    from .services import ProductService
                    details['video_url'] = ProductService.convert_youtube_link_to_embed(video_url)

                # Create competition
                competition = Competition.objects.create(
                    product=product,
                    title=title,
                    description=description,
                    short_description=details.get('short_description', ''),
                    status=Competition.CompetitionStatus.DRAFT,
                    entry_deadline=details['entry_deadline'],
                    judging_deadline=details['judging_deadline'],
                    max_entries=details.get('max_entries'),
                    product_area_id=details.get('product_area_id')
                )

                # Create associated bounty if reward specified
                if reward_details := details.get('reward'):
                    self._create_competition_bounty(competition, reward_details)

                return True, "Competition created successfully", competition.id

        except Product.DoesNotExist:
            return False, "Product not found", None
        except ValidationError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Error creating competition: {str(e)}")
            return False, str(e), None

    def submit_entry(
        self,
        competition_id: str,
        person_id: str,
        content: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Submit a competition entry"""
        try:
            with transaction.atomic():
                competition = Competition.objects.select_for_update().get(id=competition_id)
                Person = apps.get_model('talent', 'Person')
                submitter = Person.objects.get(id=person_id)

                # Validate submission
                if not self._can_submit_entry(competition, person_id):
                    return False, "Cannot submit entry", None

                # Check max entries if specified
                if competition.max_entries:
                    current_entries = CompetitionEntry.objects.filter(
                        competition=competition
                    ).count()
                    if current_entries >= competition.max_entries:
                        return False, "Maximum entries reached", None

                # Create entry
                entry = CompetitionEntry.objects.create(
                    competition=competition,
                    submitter=submitter,
                    content=content,
                    status=CompetitionEntry.EntryStatus.SUBMITTED
                )

                return True, "Entry submitted successfully", entry.id

        except (Competition.DoesNotExist, Person.DoesNotExist):
            return False, "Competition or person not found", None
        except Exception as e:
            logger.error(f"Error submitting entry: {str(e)}")
            return False, str(e), None

    def rate_entry(
        self,
        entry_id: str,
        rater_id: str,
        rating: int,
        comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Rate a competition entry"""
        try:
            with transaction.atomic():
                entry = CompetitionEntry.objects.get(id=entry_id)
                Person = apps.get_model('talent', 'Person')
                rater = Person.objects.get(id=rater_id)

                # Validate rater permission
                if not self._can_rate_entry(entry.competition, rater_id):
                    return False, "No permission to rate entries"

                # Validate rating value
                if not 1 <= rating <= 5:
                    return False, "Rating must be between 1 and 5"

                # Create or update rating
                rating_obj, created = CompetitionEntryRating.objects.update_or_create(
                    entry=entry,
                    rater=rater,
                    defaults={
                        'rating': rating,
                        'comment': comment
                    }
                )

                # Update entry status based on ratings
                self._update_entry_status(entry)

                return True, "Rating submitted successfully"

        except (CompetitionEntry.DoesNotExist, Person.DoesNotExist):
            return False, "Entry or rater not found"
        except Exception as e:
            logger.error(f"Error rating entry: {str(e)}")
            return False, str(e)

    def update_competition_status(
        self,
        competition_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update competition status"""
        try:
            with transaction.atomic():
                competition = Competition.objects.select_for_update().get(id=competition_id)
                
                if not self._can_manage_competitions(competition.product_id, updater_id):
                    return False, "No permission to update competition status"

                if not self._is_valid_status_transition(competition.status, new_status):
                    return False, f"Invalid status transition from {competition.status} to {new_status}"

                # Handle status-specific logic
                if new_status == Competition.CompetitionStatus.ACTIVE:
                    if not self._validate_competition_for_activation(competition):
                        return False, "Competition not ready for activation"

                elif new_status == Competition.CompetitionStatus.COMPLETED:
                    success, message = self._handle_competition_completion(competition)
                    if not success:
                        return False, message

                competition.status = new_status
                competition.save()

                return True, f"Competition status updated to {new_status}"

        except Competition.DoesNotExist:
            return False, "Competition not found"
        except Exception as e:
            logger.error(f"Error updating competition status: {str(e)}")
            return False, str(e)

    def get_competition_stats(
        self,
        competition_id: str
    ) -> Dict:
        """Get competition statistics and metrics"""
        try:
            competition = Competition.objects.get(id=competition_id)
            entries = CompetitionEntry.objects.filter(competition=competition)

            stats = {
                'total_entries': entries.count(),
                'entries_by_status': {
                    status: entries.filter(status=status).count()
                    for status in CompetitionEntry.EntryStatus
                },
                'average_rating': entries.annotate(
                    avg_rating=Avg('ratings__rating')
                ).aggregate(total_avg=Avg('avg_rating'))['total_avg'] or 0,
                'rating_counts': entries.values(
                    'ratings__rating'
                ).annotate(
                    count=Count('ratings__rating')
                ).order_by('ratings__rating'),
                'judges': self._get_judge_stats(competition)
            }

            if competition.max_entries:
                stats['entries_remaining'] = max(0, competition.max_entries - stats['total_entries'])

            return stats

        except Competition.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"Error getting competition stats: {str(e)}")
            return {}

    def _create_competition_bounty(
        self,
        competition: Competition,
        reward_details: Dict
    ) -> None:
        """Create bounty for competition winner"""
        Bounty.objects.create(
            product=competition.product,
            competition=competition,
            title=f"Winner: {competition.title}",
            description=f"Reward for winning competition: {competition.title}",
            reward_type=reward_details['type'],
            reward_in_usd_cents=reward_details.get('amount_cents'),
            reward_in_points=reward_details.get('amount_points'),
            status=Bounty.BountyStatus.DRAFT
        )

    def _can_submit_entry(
        self,
        competition: Competition,
        person_id: str
    ) -> bool:
        """Check if person can submit entry"""
        # Check competition status
        if competition.status != Competition.CompetitionStatus.ACTIVE:
            return False

        # Check deadline
        if timezone.now() > competition.entry_deadline:
            return False

        # Check if person has already submitted
        return not CompetitionEntry.objects.filter(
            competition=competition,
            submitter_id=person_id
        ).exists()

    def _can_rate_entry(
        self,
        competition: Competition,
        person_id: str
    ) -> bool:
        """Check if person can rate entries"""
        ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
        return ProductRoleAssignment.objects.filter(
            product=competition.product,
            person_id=person_id,
            role__in=['ADMIN', 'JUDGE']
        ).exists()

    def _can_manage_competitions(
        self,
        product_id: str,
        person_id: str
    ) -> bool:
        """Check if person can manage competitions"""
        ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
        return ProductRoleAssignment.objects.filter(
            product_id=product_id,
            person_id=person_id,
            role__in=['ADMIN', 'MANAGER']
        ).exists()

    def _is_valid_status_transition(
        self,
        current_status: str,
        new_status: str
    ) -> bool:
        """Validate competition status transition"""
        valid_transitions = {
            Competition.CompetitionStatus.DRAFT: [
                Competition.CompetitionStatus.ACTIVE,
                Competition.CompetitionStatus.CANCELLED
            ],
            Competition.CompetitionStatus.ACTIVE: [
                Competition.CompetitionStatus.ENTRIES_CLOSED,
                Competition.CompetitionStatus.CANCELLED
            ],
            Competition.CompetitionStatus.ENTRIES_CLOSED: [
                Competition.CompetitionStatus.JUDGING,
                Competition.CompetitionStatus.CANCELLED
            ],
            Competition.CompetitionStatus.JUDGING: [
                Competition.CompetitionStatus.COMPLETED,
                Competition.CompetitionStatus.CANCELLED
            ]
        }
        return new_status in valid_transitions.get(current_status, [])

    def _validate_competition_for_activation(
        self,
        competition: Competition
    ) -> bool:
        """Validate competition can be activated"""
        if not competition.entry_deadline or not competition.judging_deadline:
            return False
        if competition.entry_deadline >= competition.judging_deadline:
            return False
        if not competition.description:
            return False
        if competition.bounty and competition.bounty.status == Bounty.BountyStatus.DRAFT:
            return False
        return True

    def _handle_competition_completion(
        self,
        competition: Competition
    ) -> Tuple[bool, str]:
        """Handle competition completion"""
        try:
            # Ensure winner is selected
            winner = CompetitionEntry.objects.filter(
                competition=competition,
                status=CompetitionEntry.EntryStatus.WINNER
            ).first()

            if not winner:
                return False, "No winner selected"

            # Process bounty if exists
            if competition.bounty:
                competition.bounty.status = Bounty.BountyStatus.COMPLETED
                competition.bounty.save()

            return True, "Competition completed successfully"

        except Exception as e:
            logger.error(f"Error completing competition: {str(e)}")
            return False, str(e)

    def _update_entry_status(
        self,
        entry: CompetitionEntry
    ) -> None:
        """Update entry status based on ratings"""
        avg_rating = CompetitionEntryRating.objects.filter(
            entry=entry
        ).aggregate(Avg('rating'))['rating__avg']

        if not avg_rating:
            return

        # Example threshold logic (can be customized)
        if avg_rating >= 4.5:
            entry.status = CompetitionEntry.EntryStatus.WINNER
        elif avg_rating >= 4.0:
            entry.status = CompetitionEntry.EntryStatus.FINALIST
        elif avg_rating < 2.0:
            entry.status = CompetitionEntry.EntryStatus.REJECTED
        
        entry.save()

    def _get_judge_stats(
        self,
        competition: Competition
    ) -> Dict:
        """Get judging statistics"""
        ProductRoleAssignment = apps.get_model('security', 'ProductRoleAssignment')
        judges = ProductRoleAssignment.objects.filter(
            product=competition.product,
            role__in=['ADMIN', 'JUDGE']
        ).select_related('person')

        stats = []
        entries = CompetitionEntry.objects.filter(competition=competition)
        
        for judge in judges:
            ratings = CompetitionEntryRating.objects.filter(
                entry__in=entries,
                rater=judge.person
            )
            
            stats.append({
                'id': judge.person.id,
                'name': judge.person.full_name,
                'entries_rated': ratings.count(),
                'total_entries': entries.count(),
                'average_rating': ratings.aggregate(
                    Avg('rating')
                )['rating__avg'] or 0
            })

        return stats
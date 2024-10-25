import logging
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.apps import apps

from ..interfaces import BountyServiceInterface
from ..models import (
    Bounty,
    BountySkill,
    Challenge,
    Product
)

logger = logging.getLogger(__name__)

class BountyService(BountyServiceInterface):
    def create_bounty(
        self,
        challenge_id: str,
        details: Dict,
        creator_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new bounty"""
        try:
            with transaction.atomic():
                # Validate challenge and creator access
                challenge = Challenge.objects.select_related('product').get(id=challenge_id)
                
                if not self._can_manage_bounty(challenge.product_id, creator_id):
                    return False, "No permission to create bounty", None

                if challenge.status not in [Challenge.ChallengeStatus.DRAFT, Challenge.ChallengeStatus.ACTIVE]:
                    return False, "Challenge must be in Draft or Active status", None

                # Validate reward details
                reward_type = details.get('reward_type')
                if reward_type not in ['USD', 'Points']:
                    return False, "Invalid reward type", None

                reward_amount = details.get('reward_amount')
                if not reward_amount or reward_amount <= 0:
                    return False, "Invalid reward amount", None

                # Create bounty
                bounty = Bounty.objects.create(
                    product=challenge.product,
                    challenge=challenge,
                    title=details['title'],
                    description=details['description'],
                    reward_type=reward_type,
                    reward_in_usd_cents=reward_amount if reward_type == 'USD' else None,
                    reward_in_points=reward_amount if reward_type == 'Points' else None,
                    status=Bounty.BountyStatus.DRAFT
                )

                # Handle skills and expertise
                if skills_data := details.get('skills'):
                    self._assign_skills(bounty, skills_data)

                return True, "Bounty created successfully", bounty.id

        except Challenge.DoesNotExist:
            return False, "Challenge not found", None
        except Exception as e:
            logger.error(f"Error creating bounty: {str(e)}")
            return False, str(e), None

    def update_bounty_status(
        self,
        bounty_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update bounty status"""
        try:
            with transaction.atomic():
                bounty = Bounty.objects.select_for_update().get(id=bounty_id)
                
                if not self._can_manage_bounty(bounty.product_id, updater_id):
                    return False, "No permission to update bounty status"

                if not self._is_valid_status_transition(bounty.status, new_status):
                    return False, f"Invalid status transition from {bounty.status} to {new_status}"

                # Handle status-specific logic
                if new_status == Bounty.BountyStatus.OPEN:
                    if not self._validate_bounty_for_opening(bounty):
                        return False, "Bounty not ready to be opened"
                
                if new_status == Bounty.BountyStatus.COMPLETED:
                    success, message = self._handle_bounty_completion(bounty)
                    if not success:
                        return False, message

                bounty.status = new_status
                bounty.save()

                # Update challenge status if needed
                self._update_challenge_status(bounty.challenge)

                return True, f"Bounty status updated to {new_status}"

        except Bounty.DoesNotExist:
            return False, "Bounty not found"
        except Exception as e:
            logger.error(f"Error updating bounty status: {str(e)}")
            return False, str(e)

    def assign_skills(
        self,
        bounty_id: str,
        skill_ids: List[str],
        expertise_ids: List[str]
    ) -> Tuple[bool, str]:
        """Assign skills and expertise to bounty"""
        try:
            with transaction.atomic():
                bounty = Bounty.objects.get(id=bounty_id)
                
                # Clear existing skills
                BountySkill.objects.filter(bounty=bounty).delete()

                # Validate and add new skills
                Skill = apps.get_model('talent', 'Skill')
                Expertise = apps.get_model('talent', 'Expertise')

                for skill_id in skill_ids:
                    skill = Skill.objects.get(id=skill_id)
                    bounty_skill = BountySkill.objects.create(
                        bounty=bounty,
                        skill=skill
                    )

                    # Add expertise for this skill
                    relevant_expertise = Expertise.objects.filter(
                        id__in=expertise_ids,
                        skill=skill
                    )
                    bounty_skill.expertise.set(relevant_expertise)

                return True, "Skills assigned successfully"

        except (Bounty.DoesNotExist, Skill.DoesNotExist):
            return False, "Bounty or skill not found"
        except Exception as e:
            logger.error(f"Error assigning skills: {str(e)}")
            return False, str(e)

    def process_claim(
        self,
        bounty_id: str,
        person_id: str,
        action: str
    ) -> Tuple[bool, str]:
        """Process bounty claim actions"""
        try:
            with transaction.atomic():
                bounty = Bounty.objects.select_for_update().get(id=bounty_id)
                
                # Get claim
                BountyClaim = apps.get_model('talent', 'BountyClaim')
                claim = BountyClaim.objects.select_for_update().get(
                    bounty=bounty,
                    person_id=person_id
                )

                if action == "accept":
                    return self._accept_claim(bounty, claim)
                elif action == "reject":
                    return self._reject_claim(bounty, claim)
                elif action == "withdraw":
                    return self._withdraw_claim(bounty, claim, person_id)
                else:
                    return False, "Invalid action"

        except (Bounty.DoesNotExist, BountyClaim.DoesNotExist):
            return False, "Bounty or claim not found"
        except Exception as e:
            logger.error(f"Error processing claim: {str(e)}")
            return False, str(e)

    def _can_manage_bounty(self, product_id: str, person_id: str) -> bool:
        """Check if person can manage bounties for product"""
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
        """Validate bounty status transition"""
        valid_transitions = {
            Bounty.BountyStatus.DRAFT: [
                Bounty.BountyStatus.OPEN,
                Bounty.BountyStatus.CANCELLED
            ],
            Bounty.BountyStatus.OPEN: [
                Bounty.BountyStatus.IN_PROGRESS,
                Bounty.BountyStatus.CANCELLED
            ],
            Bounty.BountyStatus.IN_PROGRESS: [
                Bounty.BountyStatus.IN_REVIEW,
                Bounty.BountyStatus.CANCELLED
            ],
            Bounty.BountyStatus.IN_REVIEW: [
                Bounty.BountyStatus.COMPLETED,
                Bounty.BountyStatus.IN_PROGRESS
            ]
        }
        return new_status in valid_transitions.get(current_status, [])

    def _validate_bounty_for_opening(self, bounty: Bounty) -> bool:
        """Validate bounty can be opened"""
        if not bounty.title or not bounty.description:
            return False
        if not bounty.skills.exists():
            return False
        if bounty.reward_type == 'USD' and not bounty.reward_in_usd_cents:
            return False
        if bounty.reward_type == 'Points' and not bounty.reward_in_points:
            return False
        return True

    def _handle_bounty_completion(self, bounty: Bounty) -> Tuple[bool, str]:
        """Handle bounty completion logic"""
        try:
            # Process rewards
            if bounty.reward_type == 'USD':
                success, message = self._process_usd_reward(bounty)
            else:
                success, message = self._process_points_reward(bounty)

            if not success:
                return False, message

            return True, "Bounty completion processed"

        except Exception as e:
            logger.error(f"Error handling bounty completion: {str(e)}")
            return False, str(e)

    def _process_usd_reward(self, bounty: Bounty) -> Tuple[bool, str]:
        """Process USD reward payment"""
        try:
            BountyClaim = apps.get_model('talent', 'BountyClaim')
            claim = BountyClaim.objects.get(
                bounty=bounty,
                status=BountyClaim.Status.ACTIVE
            )

            ContributorWalletService = apps.get_model('commerce', 'ContributorWalletService')
            wallet_service = ContributorWalletService()

            success, message = wallet_service.add_funds(
                person_id=claim.person.id,
                amount_cents=bounty.final_reward_in_usd_cents or bounty.reward_in_usd_cents,
                description=f"Reward for bounty: {bounty.title}",
                from_bounty_id=bounty.id
            )

            return success, message

        except Exception as e:
            logger.error(f"Error processing USD reward: {str(e)}")
            return False, str(e)

    def _process_points_reward(self, bounty: Bounty) -> Tuple[bool, str]:
        """Process points reward"""
        try:
            BountyClaim = apps.get_model('talent', 'BountyClaim')
            claim = BountyClaim.objects.get(
                bounty=bounty,
                status=BountyClaim.Status.ACTIVE
            )

            PersonManagementService = apps.get_model('talent', 'PersonManagementService')
            person_service = PersonManagementService()

            success, message = person_service.add_points(
                person_id=claim.person.id,
                points=bounty.final_reward_in_points or bounty.reward_in_points
            )

            return success, message

        except Exception as e:
            logger.error(f"Error processing points reward: {str(e)}")
            return False, str(e)

    def _update_challenge_status(self, challenge: Challenge) -> None:
        """Update challenge status based on bounty status"""
        if not challenge:
            return

        bounties = challenge.bounties.all()
        
        if all(b.status == Bounty.BountyStatus.COMPLETED for b in bounties):
            challenge.status = Challenge.ChallengeStatus.COMPLETED
            challenge.save()
        elif any(b.status == Bounty.BountyStatus.IN_PROGRESS for b in bounties):
            challenge.status = Challenge.ChallengeStatus.IN_PROGRESS
            challenge.save()

    def _accept_claim(
        self,
        bounty: Bounty,
        claim: any
    ) -> Tuple[bool, str]:
        """Accept a bounty claim"""
        BountyClaim = apps.get_model('talent', 'BountyClaim')
        
        if claim.status != BountyClaim.Status.REQUESTED:
            return False, "Only pending claims can be accepted"

        # Set this claim as accepted
        claim.status = BountyClaim.Status.GRANTED
        claim.save()

        # Reject other claims
        BountyClaim.objects.filter(
            bounty=bounty
        ).exclude(
            id=claim.id
        ).update(status=BountyClaim.Status.REJECTED)

        # Update bounty status
        bounty.status = Bounty.BountyStatus.IN_PROGRESS
        bounty.save()

        return True, "Claim accepted successfully"

    def _reject_claim(
        self,
        bounty: Bounty,
        claim: any
    ) -> Tuple[bool, str]:
        """Reject a bounty claim"""
        BountyClaim = apps.get_model('talent', 'BountyClaim')
        
        if claim.status != BountyClaim.Status.REQUESTED:
            return False, "Only pending claims can be rejected"

        claim.status = BountyClaim.Status.REJECTED
        claim.save()

        return True, "Claim rejected successfully"

    def _withdraw_claim(
        self,
        bounty: Bounty,
        claim: any,
        person_id: str
    ) -> Tuple[bool, str]:
        """Withdraw a bounty claim"""
        if str(claim.person_id) != person_id:
            return False, "Only claim owner can withdraw"

        BountyClaim = apps.get_model('talent', 'BountyClaim')
        if claim.status != BountyClaim.Status.REQUESTED:
            return False, "Only pending claims can be withdrawn"

        claim.status = BountyClaim.Status.CANCELLED
        claim.save()

        return True, "Claim withdrawn successfully"
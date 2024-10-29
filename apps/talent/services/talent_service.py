from typing import Dict, Tuple
import logging
from django.db import transaction

from .bounty_bid import BountyBidService
from .bounty_claim import BountyClaimService
from .skill_service import SkillManagementService
from .person_service import PersonManagementService
from .feedback_service import FeedbackService

logger = logging.getLogger(__name__)

class TalentService:
    def __init__(self):
        self.bounty_bid_service = BountyBidService()
        self.bounty_claim_service = BountyClaimService()
        self.skill_service = SkillManagementService()
        self.person_service = PersonManagementService()
        self.feedback_service = FeedbackService()

    @transaction.atomic
    def handle_bounty_claim_created(self, event_data: Dict) -> Tuple[bool, str]:
        """Handle bounty claim created event"""
        try:
            claim_id = event_data.get('claim_id')
            if not claim_id:
                return False, "Missing claim_id in event data"

            # Update person's points based on claim
            # Add any other business logic needed when a claim is created
            
            return True, "Bounty claim handled successfully"
            
        except Exception as e:
            logger.error(f"Error handling bounty claim created: {str(e)}")
            return False, f"Failed to handle bounty claim: {str(e)}"

    @transaction.atomic
    def handle_bounty_completed(self, event_data: Dict) -> Tuple[bool, str]:
        """Handle bounty completed event"""
        try:
            bounty_id = event_data.get('bounty_id')
            person_id = event_data.get('person_id')
            if not all([bounty_id, person_id]):
                return False, "Missing required data in event"

            # Award points or handle other completion logic
            success, message = self.person_service.add_points(
                person_id=person_id,
                points=event_data.get('points', 0)
            )
            
            return success, message
            
        except Exception as e:
            logger.error(f"Error handling bounty completed: {str(e)}")
            return False, f"Failed to handle bounty completion: {str(e)}"

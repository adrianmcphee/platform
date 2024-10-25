from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional, List
from datetime import date
from decimal import Decimal

class PersonManagementServiceInterface(ABC):
    @abstractmethod
    def calculate_points_status(self, points: int) -> str:
        """Calculate person's status based on points"""
        pass

    @abstractmethod
    def get_points_privileges(self, status: str) -> str:
        """Get privileges for a given status"""
        pass

    @abstractmethod
    def add_points(self, person_id: str, points: int) -> Tuple[bool, str]:
        """Add points to person's account"""
        pass

    @abstractmethod
    def update_profile(
        self,
        person_id: str,
        profile_data: Dict
    ) -> Tuple[bool, str]:
        """Update person's profile information"""
        pass

    @abstractmethod
    def get_profile_completion_status(self, person_id: str) -> Tuple[bool, List[str]]:
        """Check profile completion and return missing fields"""
        pass

class SkillManagementServiceInterface(ABC):
    @abstractmethod
    def add_skill_to_person(
        self,
        person_id: str,
        skill_id: str,
        expertise_ids: List[str]
    ) -> Tuple[bool, str]:
        """Add a skill with expertise to a person"""
        pass

    @abstractmethod
    def get_active_skills(
        self,
        parent_id: Optional[str] = None
    ) -> List[Dict]:
        """Get active skills, optionally filtered by parent"""
        pass

    @abstractmethod
    def get_expertise_for_skill(
        self,
        skill_id: str
    ) -> List[Dict]:
        """Get expertise options for a skill"""
        pass

class BountyBidServiceInterface(ABC):
    @abstractmethod
    def create_bid(
        self,
        bounty_id: str,
        person_id: str,
        expected_finish_date: date,
        message: Optional[str] = None,
        amount_in_usd_cents: Optional[int] = None,
        amount_in_points: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Create a new bounty bid"""
        pass

    @abstractmethod
    def accept_bid(
        self,
        bid_id: str,
        reviewer_id: str
    ) -> Tuple[bool, str]:
        """Accept a bid and process necessary adjustments"""
        pass

    @abstractmethod
    def reject_bid(
        self,
        bid_id: str,
        reviewer_id: str,
        reason: str
    ) -> Tuple[bool, str]:
        """Reject a bid"""
        pass

    @abstractmethod
    def withdraw_bid(
        self,
        bid_id: str,
        person_id: str
    ) -> Tuple[bool, str]:
        """Withdraw a bid"""
        pass

class BountyClaimServiceInterface(ABC):
    @abstractmethod
    def create_claim(
        self,
        bounty_id: str,
        person_id: str,
        accepted_bid_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Create a bounty claim"""
        pass

    @abstractmethod
    def submit_delivery_attempt(
        self,
        claim_id: str,
        delivery_message: str,
        attachments: Optional[List] = None
    ) -> Tuple[bool, str]:
        """Submit a delivery attempt for a claim"""
        pass

    @abstractmethod
    def review_delivery_attempt(
        self,
        attempt_id: str,
        reviewer_id: str,
        status: str,
        review_message: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Review a delivery attempt"""
        pass

class FeedbackServiceInterface(ABC):
    @abstractmethod
    def create_feedback(
        self,
        recipient_id: str,
        provider_id: str,
        message: str,
        stars: int
    ) -> Tuple[bool, str]:
        """Create feedback for a person"""
        pass

    @abstractmethod
    def get_person_feedback_analytics(
        self,
        person_id: str
    ) -> Dict:
        """Get analytics about feedback received by a person"""
        pass

    @abstractmethod
    def validate_feedback(
        self,
        recipient_id: str,
        provider_id: str,
        stars: int
    ) -> Tuple[bool, str]:
        """Validate feedback before creation"""
        pass
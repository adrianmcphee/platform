from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal

class ProductManagementServiceInterface(ABC):
    @abstractmethod
    def create_product(
        self,
        name: str,
        owner_id: str,
        owner_type: str,  # 'person' or 'organisation'
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new product with optional organization ownership"""
        pass

    @abstractmethod
    def update_product(
        self,
        product_id: str,
        details: Dict,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update product details"""
        pass

    @abstractmethod
    def check_product_access(
        self,
        product_id: str,
        person_id: str
    ) -> Tuple[bool, str]:
        """Check if person has access to product based on visibility settings"""
        pass

    @abstractmethod
    def manage_points(
        self,
        product_id: str,
        points: int,
        action: str
    ) -> Tuple[bool, str]:
        """Manage product point balance"""
        pass

class ChallengeServiceInterface(ABC):
    @abstractmethod
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
        pass

    @abstractmethod
    def update_status(
        self,
        challenge_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update challenge status with validation"""
        pass

    @abstractmethod
    def get_filtered_challenges(
        self,
        product_id: str,
        filters: Dict
    ) -> List[Dict]:
        """Get filtered and ordered challenges"""
        pass

    @abstractmethod
    def calculate_rewards(
        self,
        challenge_id: str
    ) -> Dict:
        """Calculate total rewards for challenge"""
        pass

    @abstractmethod
    def get_challenge_details(self, challenge_id: str) -> Dict:
        """Get detailed information about a specific challenge"""
        pass

    @abstractmethod
    def get_challenge_bounties(self, challenge_id: str) -> List[Dict]:
        """Get bounties for a specific challenge"""
        pass

    @abstractmethod
    def check_challenge_permission(self, challenge_id: str, user_id: str) -> bool:
        """Check if user has permission to modify the challenge"""
        pass

    @abstractmethod
    def check_contributor_agreement(self, product_id: str, person_id: str) -> bool:
        """Check if person has signed the contributor agreement for the product"""
        pass

    @abstractmethod
    def get_contributor_agreement_template(self, product_id: str) -> Optional[Dict]:
        """Get the contributor agreement template for the product"""
        pass

    @abstractmethod
    def update_challenge(self, challenge_id: str, details: Dict, updater_id: str) -> Tuple[bool, str]:
        """Update challenge details"""
        pass

    @abstractmethod
    def can_delete_challenge(self, challenge_id: str, person_id: str) -> bool:
        """Check if person can delete the challenge"""
        pass

    @abstractmethod
    def delete_challenge(self, challenge_id: str, deleter_id: str) -> Tuple[bool, str]:
        """Delete a challenge"""
        pass

    @abstractmethod
    def get_bounty_statuses(self) -> Dict:
        """Get all bounty statuses"""
        pass

    @abstractmethod
    def get_challenge_statuses(self) -> Dict:
        """Get all challenge statuses"""
        pass

class BountyServiceInterface(ABC):
    @abstractmethod
    def create_bounty(
        self,
        challenge_id: str,
        details: Dict,
        creator_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new bounty"""
        pass

    @abstractmethod
    def update_bounty_status(
        self,
        bounty_id: str,
        new_status: str,
        updater_id: str
    ) -> Tuple[bool, str]:
        """Update bounty status"""
        pass

    @abstractmethod
    def assign_skills(
        self,
        bounty_id: str,
        skill_ids: List[str],
        expertise_ids: List[str]
    ) -> Tuple[bool, str]:
        """Assign skills and expertise to bounty"""
        pass

    @abstractmethod
    def process_claim(
        self,
        bounty_id: str,
        person_id: str,
        action: str
    ) -> Tuple[bool, str]:
        """Process bounty claim actions"""
        pass

    @abstractmethod
    def get_bounties(
        self,
        filters: Dict[str, Any] = None,
        paginate: bool = True,
        page: int = 1,
        per_page: int = 51
    ) -> Tuple[List[Dict], int]:
        """Get filtered bounties with optional pagination"""
        pass

    @abstractmethod
    def get_bounty_details(self, bounty_id: str, user_id: Optional[str] = None) -> Dict:
        """Get detailed information about a specific bounty"""
        pass

    @abstractmethod
    def get_product_bounties(self, product_id: str) -> List[Dict]:
        """Get bounties for a specific product"""
        pass

    @abstractmethod
    def create_bounty_claim(self, bounty_id: str, person_id: str) -> Tuple[bool, str]:
        """Create a new bounty claim"""
        pass

    @abstractmethod
    def delete_bounty_claim(self, claim_id: str, person_id: str) -> Tuple[bool, str]:
        """Delete (cancel) a bounty claim"""
        pass

    @abstractmethod
    def get_bounty_claims(self, product_id: str) -> List[Dict]:
        """Get bounty claims for a specific product"""
        pass

class InitiativeServiceInterface(ABC):
    @abstractmethod
    def create_initiative(
        self,
        product_id: str,
        name: str,
        description: str,
        creator_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new initiative"""
        pass

    @abstractmethod
    def get_initiative_stats(
        self,
        initiative_id: str
    ) -> Dict:
        """Get initiative statistics including points and challenge status"""
        pass

    @abstractmethod
    def manage_challenges(
        self,
        initiative_id: str,
        challenge_ids: List[str],
        action: str
    ) -> Tuple[bool, str]:
        """Manage challenges within initiative"""
        pass

class ProductAreaServiceInterface(ABC):
    @abstractmethod
    def create_node(
        self,
        product_id: str,
        name: str,
        parent_id: Optional[str],
        details: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """Create a new product area node"""
        pass

    @abstractmethod
    def move_node(
        self,
        node_id: str,
        new_parent_id: Optional[str]
    ) -> Tuple[bool, str]:
        """Move node in tree structure"""
        pass

    @abstractmethod
    def get_tree(
        self,
        product_id: str
    ) -> List[Dict]:
        """Get complete tree structure for product"""
        pass

class ProductSupportServiceInterface(ABC):
    @abstractmethod
    def create_idea(
        self,
        product_id: str,
        person_id: str,
        title: str,
        description: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create new product idea"""
        pass

    @abstractmethod
    def create_bug_report(
        self,
        product_id: str,
        person_id: str,
        title: str,
        description: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Create new bug report"""
        pass

    @abstractmethod
    def process_vote(
        self,
        idea_id: str,
        voter_id: str
    ) -> Tuple[bool, str, int]:
        """Process vote on idea and return updated count"""
        pass

    @abstractmethod
    def manage_contributor_agreement(
        self,
        product_id: str,
        person_id: str,
        agreement_id: str,
        action: str
    ) -> Tuple[bool, str]:
        """Manage contributor agreements"""
        pass

class PortalServiceInterface(ABC):
    @abstractmethod
    def get_user_dashboard(
        self,
        person_id: str
    ) -> Dict:
        """
        Get dashboard data including:
        - Active bounty claims
        - Product roles
        - Product access
        - Recent activity
        """
        pass

    @abstractmethod
    def get_product_dashboard(
        self,
        product_id: str,
        person_id: str
    ) -> Dict:
        """
        Get product-specific dashboard including:
        - Product metrics
        - Role assignments
        - Activity feed
        - Pending reviews
        """
        pass

    @abstractmethod
    def get_bounty_management(
        self,
        person_id: str,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Get bounty management overview including:
        - Active claims
        - Pending reviews
        - Completion stats
        """
        pass

    @abstractmethod
    def get_user_management(
        self,
        product_id: str,
        person_id: str,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Get user management data including:
        - Role assignments
        - Activity metrics 
        - Contribution stats
        """
        pass

    @abstractmethod
    def get_work_review_queue(
        self,
        product_id: str,
        reviewer_id: str
    ) -> Dict:
        """
        Get review queue including:
        - Pending deliveries
        - Claim requests
        - Competition entries
        """
        pass

    @abstractmethod
    def get_contribution_overview(
        self,
        person_id: str
    ) -> Dict:
        """
        Get contributor overview including:
        - Active contributions
        - Historical stats
        - Earned rewards
        - Product participation
        """
        pass

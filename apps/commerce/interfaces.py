from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, List, Any
from decimal import Decimal
from apps.common.data_transfer_objects import BountyPurchaseData

class OrganisationWalletServiceInterface(ABC):
    @abstractmethod
    def add_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        payment_method: str,
        transaction_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Add funds to an organisation wallet
        
        Args:
            wallet_id: The wallet identifier
            amount_cents: Amount to add in cents
            description: Transaction description
            payment_method: Method of payment (e.g., "PayPal", "USDT")
            transaction_id: Optional external transaction identifier
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def deduct_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        order_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Deduct funds from an organisation wallet
        
        Args:
            wallet_id: The wallet identifier
            amount_cents: Amount to deduct in cents
            description: Transaction description
            order_id: Optional related order identifier
        """
        pass

    @abstractmethod
    def get_balance(self, wallet_id: str) -> int:
        """Get current wallet balance in cents"""
        pass

class ContributorWalletServiceInterface(ABC):
    @abstractmethod
    def add_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        from_bounty_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Add funds to a contributor wallet"""
        pass

    @abstractmethod
    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        payment_method: str,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        """Process a withdrawal request"""
        pass

    @abstractmethod
    def get_balance(self, wallet_id: str) -> int:
        """Get current wallet balance in cents"""
        pass

class CartServiceInterface(ABC):
    @abstractmethod
    def add_bounty(
        self,
        cart_id: str,
        bounty_data: BountyPurchaseData,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        """
        Add a bounty to the cart
        
        Args:
            cart_id: The cart identifier
            bounty_data: Dictionary containing bounty details (e.g., title, reward, etc.)
            quantity: Number of bounties to add (default is 1)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def update_totals(self, cart_id: str) -> Tuple[bool, str]:
        """Update cart totals including fees and taxes"""
        pass

    @abstractmethod
    def validate(self, cart_id: str) -> Tuple[bool, List[str]]:
        """
        Validate cart state
        Returns tuple of (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def add_point_grant_request(
        self,
        cart_id: str,
        grant_request_id: str,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        """Add a point grant request to the cart"""
        pass

class OrderServiceInterface(ABC):
    @abstractmethod
    def create_from_cart(
        self,
        cart_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new order from a cart
        
        Returns:
            Tuple of (success: bool, message: str, order_id: Optional[str])
        """
        pass

    @abstractmethod
    def process_payment(
        self,
        order_id: str
    ) -> Tuple[bool, str]:
        """Process payment for an order"""
        pass

    @abstractmethod
    def validate(self, order_id: str) -> Tuple[bool, List[str]]:
        """
        Validate order state
        Returns tuple of (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def process_paid_point_grants(self, order_id: str) -> Tuple[bool, str]:
        """Process paid point grants after successful payment"""
        pass

    @abstractmethod
    def get_order_items(self, order_id: str) -> List[Dict]:
        """
        Get all items in an order
        
        Returns:
            List of dictionaries containing order item details
        """
        pass

class PaymentStrategyInterface(ABC):
    @abstractmethod
    def process_payment(
        self,
        wallet_id: str,
        amount_cents: int,
        payment_details: Dict,
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process a payment
        Returns (success, message, transaction_id)
        """
        pass

class TaxServiceInterface(ABC):
    @abstractmethod
    def calculate_tax(
        self,
        amount_cents: int,
        country_code: str
    ) -> int:
        """Calculate tax amount in cents"""
        pass

    @abstractmethod
    def get_tax_rate(self, country_code: str) -> Tuple[bool, Decimal]:
        """Get tax rate for a country, returns (success, rate)"""
        pass

class FeeServiceInterface(ABC):
    @abstractmethod
    def calculate_platform_fee(
        self,
        amount_cents: int
    ) -> int:
        """Calculate platform fee in cents"""
        pass

    @abstractmethod
    def get_platform_fee_rate(self) -> Decimal:
        """Get current platform fee rate"""
        pass

class WithdrawalStrategyInterface(ABC):
    @abstractmethod
    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        """Process a withdrawal request"""
        pass

    @abstractmethod
    def validate_withdrawal_details(
        self,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        """Validate withdrawal details"""
        pass

class OrganisationPointGrantServiceInterface(ABC):
    @abstractmethod
    def create_grant(
        self,
        organisation_id: str,
        amount: int,
        granted_by_id: str,
        rationale: str,
        grant_request_id: Optional[str] = None,
        sales_order_item_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Create a new point grant for an organisation
        
        Args:
            organisation_id: The organisation identifier
            amount: Number of points to grant
            granted_by_id: ID of the person granting the points
            rationale: Reason for the grant
            grant_request_id: Optional ID of the associated grant request
            sales_order_item_id: Optional ID of the associated sales order item
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def create_request(
        self,
        organisation_id: str,
        number_of_points: int,
        requested_by_id: str,
        rationale: str,
        grant_type: str
    ) -> Tuple[bool, str]:
        """
        Create a new point grant request for an organisation
        
        Args:
            organisation_id: The organisation identifier
            number_of_points: Number of points requested
            requested_by_id: ID of the person making the request
            rationale: Reason for the request
            grant_type: Type of grant (e.g., "free", "paid")
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def get_grant(self, grant_id: str) -> Optional[Dict]:
        """Get details of a specific point grant"""
        pass

    @abstractmethod
    def approve_request(self, request_id: str) -> Tuple[bool, str]:
        """Approve a point grant request"""
        pass

    @abstractmethod
    def process_paid_grant(self, grant_request_id: str, sales_order_item_id: str) -> Tuple[bool, str]:
        """Process a paid grant after successful payment"""
        pass

class OrganisationPointGrantRequestServiceInterface(ABC):
    @abstractmethod
    def reject_request(self, request_id: str) -> Tuple[bool, str]:
        """Reject a point grant request"""
        pass

    @abstractmethod
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get details of a specific point grant request"""
        pass

class PaymentServiceInterface(ABC):
    @abstractmethod
    def process_payment(
        self,
        amount_cents: int,
        payment_details: Dict,
        **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Process a payment
        Returns (success, message, transaction_id)
        """
        pass

    @abstractmethod
    def validate_payment_details(
        self,
        payment_details: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Validate payment details
        Returns (is_valid, list_of_error_messages)
        """
        pass

    @abstractmethod
    def refund_payment(
        self,
        transaction_id: str,
        amount_cents: int,
        reason: str
    ) -> Tuple[bool, str]:
        """
        Refund a payment
        Returns (success, message)
        """
        pass

    @abstractmethod
    def get_payment_status(
        self,
        transaction_id: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Get the status of a payment
        Returns (success, status, error_message)
        """
        pass

class BountyServiceInterface(ABC):
    @abstractmethod
    def get_bounty(self, bounty_id: str) -> Optional[Dict]:
        """Get details of a specific bounty"""
        pass

    @abstractmethod
    def update_bounty_status(self, bounty_id: str, new_status: str) -> Tuple[bool, str]:
        """Update the status of a bounty"""
        pass

    @abstractmethod
    def create_bounty(self, bounty_data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new bounty
        Returns (success, message, bounty_id)
        """
        pass

    @abstractmethod
    def get_bounty_purchase_data(self, bounty_id: str) -> BountyPurchaseData:
        """Get bounty data for purchase"""
        pass

class BountyPurchaseInterface:
    """Interface for bounty purchase data"""
    @property
    def purchase_status(self) -> str:
        """Get the purchase status of the bounty"""
        pass

class BountyPurchaseServiceInterface(ABC):
    @abstractmethod
    def create_purchase(self, bounty_id: str, buyer_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new bounty purchase
        Returns (success, message, purchase_id)
        """
        pass

    @abstractmethod
    def get_purchase(self, purchase_id: str) -> Optional[BountyPurchaseInterface]:
        """Get details of a specific bounty purchase"""
        pass

    @abstractmethod
    def update_purchase_status(self, purchase_id: str, new_status: str) -> Tuple[bool, str]:
        """Update the status of a bounty purchase"""
        pass

class BountyCreationServiceInterface(ABC):
    @abstractmethod
    def create_bounty_from_order_item(
        self,
        order_item_id: str,
        bounty_data: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a bounty based on a successful order item
        
        Args:
            order_item_id: The ID of the order item
            bounty_data: Dictionary containing bounty details
        
        Returns:
            Tuple of (success: bool, message: str, bounty_id: Optional[str])
        """
        pass


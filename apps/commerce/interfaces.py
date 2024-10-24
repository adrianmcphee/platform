from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, List
from decimal import Decimal

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
        bounty_id: str,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        """Add a bounty to the cart"""
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

class OrderServiceInterface(ABC):
    @abstractmethod
    def create_from_cart(
        self,
        cart_id: str
    ) -> Tuple[bool, str]:
        """Create a new order from a cart"""
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

class PaymentStrategyInterface(ABC):
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
    def get_rate(self, country_code: str) -> Decimal:
        """Get tax rate for a country"""
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
    def get_current_rate(self) -> Decimal:
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

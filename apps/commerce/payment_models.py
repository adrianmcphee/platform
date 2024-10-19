from abc import ABC, abstractmethod

from django.apps import apps

from apps.commerce import models
from apps.common.fields import Base58UUIDv5Field
from apps.common.mixins import TimeStampMixin


class PaymentStrategy(ABC):
    
    @abstractmethod
    def process_payment(self, organisation_wallet, amount, **kwargs):
        """
        Processes the payment and updates the OrganisationWalletTransaction.
        """
        pass
    
    @abstractmethod
    def validate_payment(self, **kwargs):
        """
        Validates payment details before processing.
        """
        pass

class PayPalPaymentStrategy(PaymentStrategy):
    
    def process_payment(self, organisation_wallet, amount_cents, **kwargs):
        # Simulate PayPal payment processing (replace with actual PayPal API integration)
        print(f"Processing PayPal payment of {amount_cents / 100:.2f} USD")

        OrganisationWalletTransaction = apps.get_model("commerce", "OrganisationWalletTransaction")
        
        # Update the OrganisationWalletTransaction
        OrganisationWalletTransaction.objects.create(
            wallet=organisation_wallet,
            amount_cents=amount_cents,
            transaction_type='Credit',
            payment_method='PayPal',
            transaction_id="PayPal-Transaction-ID"
        )
    
    def validate_payment(self, paypal_email, **kwargs):
        if not paypal_email:
            raise ValueError("PayPal email is required for PayPal payments.")
        return True
    
class USDTPaymentStrategy(PaymentStrategy):
    
    def process_payment(self, organisation_wallet, amount_cents, crypto_wallet_address, **kwargs):
        # Simulate USDT payment processing (replace with actual USDT blockchain integration)
        print(f"Processing USDT payment of {amount_cents / 100:.2f} USD to wallet {crypto_wallet_address}")
        
        OrganisationWalletTransaction = apps.get_model("commerce", "OrganisationWalletTransaction")
        # Update the OrganisationWalletTransaction
        OrganisationWalletTransaction.objects.create(
            wallet=organisation_wallet,
            amount_cents=amount_cents,
            transaction_type='Credit',
            payment_method='USDT',
            transaction_id="USDT-Transaction-Hash"
        )
    
    def validate_payment(self, crypto_wallet_address, **kwargs):
        if not crypto_wallet_address:
            raise ValueError("Crypto wallet address is required for USDT payments.")
        return True

class WithdrawalRequest(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    contributor_wallet = models.ForeignKey("commerece.ContributorWallet", on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed')
    ], default='Pending')
    payment_method = models.CharField(max_length=20, choices=[
        ('PayPal', 'PayPal'),
        ('USDT', 'USDT')
    ])
    transaction_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Withdrawal of ${self.amount_cents / 100:.2f} via {self.payment_method}"
    
    def process(self):
        # Process the withdrawal via the appropriate strategy
        if self.payment_method == 'PayPal':
            PayPalWithdrawalRequest().process(self)
        elif self.payment_method == 'USDT':
            USDTWithdrawalRequest().process(self)


class PayPalWithdrawalRequest:
    
    def process(self, withdrawal_request):
        # Simulate PayPal withdrawal (replace with PayPal API integration)
        print(f"Processing PayPal withdrawal of ${withdrawal_request.amount_cents / 100:.2f}")
        
        ContributorWalletTransaction = apps.get_model("commerce", "ContributorWalletTransaction")
        
        # Update ContributorWalletTransaction
        ContributorWalletTransaction.objects.create(
            wallet=withdrawal_request.contributor_wallet,
            amount_cents=withdrawal_request.amount_cents,
            transaction_type='Debit',
            payment_method='PayPal',
            transaction_id="PayPal-Withdrawal-ID"
        )
        
        # Mark the withdrawal as completed
        withdrawal_request.status = 'Completed'
        withdrawal_request.save()

class USDTWithdrawalRequest:
    
    def process(self, withdrawal_request):
        # Simulate USDT withdrawal (replace with blockchain integration)
        print(f"Processing USDT withdrawal of ${withdrawal_request.amount_cents / 100:.2f}")
        
        ContributorWalletTransaction = apps.get_model("commerce", "ContributorWalletTransaction")
        # Update ContributorWalletTransaction
        ContributorWalletTransaction.objects.create(
            wallet=withdrawal_request.contributor_wallet,
            amount_cents=withdrawal_request.amount_cents,
            transaction_type='Debit',
            payment_method='USDT',
            transaction_id="USDT-Withdrawal-Hash"
        )
        
        # Mark the withdrawal as completed
        withdrawal_request.status = 'Completed'
        withdrawal_request.save()
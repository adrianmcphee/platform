from django.db import transaction
from typing import Tuple, Optional, Dict
import logging
from ..interfaces import ContributorWalletServiceInterface
from ..models import ContributorWallet, ContributorWalletTransaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class ContributorWalletService(ContributorWalletServiceInterface):
    def add_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        from_bounty_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = (
                    ContributorWallet.objects
                    .select_for_update()
                    .get(id=wallet_id)
                )
                
                if amount_cents <= 0:
                    return False, "Amount must be positive"
                
                wallet.balance_usd_in_cents += amount_cents
                wallet.save()
                
                ContributorWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=ContributorWalletTransaction.TransactionType.CREDIT,
                    description=description,
                    status=ContributorWalletTransaction.Status.COMPLETED
                )
                
                return True, "Funds added successfully"
                
        except ContributorWallet.DoesNotExist:
            logger.error(f"Wallet {wallet_id} not found")
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error adding funds to wallet {wallet_id}: {str(e)}")
            return False, f"Error adding funds: {str(e)}"

    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        payment_method: str,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = (
                    ContributorWallet.objects
                    .select_for_update()
                    .get(id=wallet_id)
                )
                
                if amount_cents <= 0:
                    return False, "Amount must be positive"
                    
                if amount_cents < 1000:  # $10.00 minimum withdrawal
                    return False, "Minimum withdrawal amount is $10.00"
                
                if wallet.balance_usd_in_cents < amount_cents:
                    return False, "Insufficient funds"
                
                # Create pending transaction
                transaction = ContributorWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=ContributorWalletTransaction.TransactionType.WITHDRAWAL,
                    payment_method=payment_method,
                    description=f"Withdrawal via {payment_method}",
                    status=ContributorWalletTransaction.Status.PENDING
                )
                
                try:
                    # Deduct funds
                    wallet.balance_usd_in_cents -= amount_cents
                    wallet.save()
                    
                    # Mark transaction as completed
                    transaction.status = ContributorWalletTransaction.Status.COMPLETED
                    transaction.save()
                    
                    return True, "Withdrawal processed successfully"
                    
                except Exception as e:
                    # If anything fails, mark transaction as failed
                    transaction.status = ContributorWalletTransaction.Status.FAILED
                    transaction.save()
                    raise
                
        except ContributorWallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error processing withdrawal from wallet {wallet_id}: {str(e)}")
            return False, str(e)

    def get_balance(self, wallet_id: str) -> int:
        try:
            wallet = ContributorWallet.objects.get(id=wallet_id)
            return wallet.balance_usd_in_cents
        except ContributorWallet.DoesNotExist:
            raise ValidationError("Wallet not found")

    def _validate_withdrawal_amount(self, amount_cents: int) -> Tuple[bool, Optional[str]]:
        """Helper method to validate withdrawal amounts"""
        if amount_cents <= 0:
            return False, "Amount must be positive"
            
        if amount_cents < 1000:  # $10.00 minimum withdrawal
            return False, "Minimum withdrawal amount is $10.00"
            
        if amount_cents > 1000000:  # $10,000.00 maximum withdrawal
            return False, "Maximum withdrawal amount is $10,000.00"
            
        return True, None
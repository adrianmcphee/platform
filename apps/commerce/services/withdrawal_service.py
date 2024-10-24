from typing import Tuple, Dict
import logging
from ..models import ContributorWallet, ContributorWalletTransaction
from django.db import transaction
from ..interfaces import WithdrawalStrategyInterface

logger = logging.getLogger(__name__)

class PayPalWithdrawalStrategy(WithdrawalStrategyInterface):
    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = ContributorWallet.objects.select_for_update().get(id=wallet_id)
                
                if wallet.balance_usd_in_cents < amount_cents:
                    return False, "Insufficient funds"
                
                # Process PayPal withdrawal (implement PayPal API call here)
                # For now, we'll just simulate the process
                
                wallet.balance_usd_in_cents -= amount_cents
                wallet.save()
                
                ContributorWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=ContributorWalletTransaction.TransactionType.WITHDRAWAL,
                    payment_method="PayPal",
                    description="PayPal withdrawal",
                    status=ContributorWalletTransaction.Status.COMPLETED
                )
                
                return True, "PayPal withdrawal processed successfully"
        
        except ContributorWallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error processing PayPal withdrawal: {str(e)}")
            return False, f"Error processing withdrawal: {str(e)}"

    def validate_withdrawal_details(self, withdrawal_details: Dict) -> Tuple[bool, str]:
        if 'paypal_email' not in withdrawal_details:
            return False, "PayPal email is required"
        # Add more PayPal-specific validations here
        return True, "Withdrawal details are valid"

class USDTWithdrawalStrategy(WithdrawalStrategyInterface):
    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = ContributorWallet.objects.select_for_update().get(id=wallet_id)
                
                if wallet.balance_usd_in_cents < amount_cents:
                    return False, "Insufficient funds"
                
                # Process USDT withdrawal (implement blockchain transaction here)
                # For now, we'll just simulate the process
                
                wallet.balance_usd_in_cents -= amount_cents
                wallet.save()
                
                ContributorWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=ContributorWalletTransaction.TransactionType.WITHDRAWAL,
                    payment_method="USDT",
                    description="USDT withdrawal",
                    status=ContributorWalletTransaction.Status.COMPLETED
                )
                
                return True, "USDT withdrawal processed successfully"
        
        except ContributorWallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error processing USDT withdrawal: {str(e)}")
            return False, f"Error processing withdrawal: {str(e)}"

    def validate_withdrawal_details(self, withdrawal_details: Dict) -> Tuple[bool, str]:
        if 'usdt_address' not in withdrawal_details:
            return False, "USDT address is required"
        # Add more USDT-specific validations here
        return True, "Withdrawal details are valid"

class WithdrawalService:
    def __init__(self):
        self.strategies = {
            'PayPal': PayPalWithdrawalStrategy(),
            'USDT': USDTWithdrawalStrategy()
        }

    def process_withdrawal(
        self,
        wallet_id: str,
        amount_cents: int,
        payment_method: str,
        withdrawal_details: Dict
    ) -> Tuple[bool, str]:
        strategy = self.strategies.get(payment_method)
        if not strategy:
            return False, f"Unsupported payment method: {payment_method}"
        
        is_valid, message = strategy.validate_withdrawal_details(withdrawal_details)
        if not is_valid:
            return False, message
        
        return strategy.process_withdrawal(wallet_id, amount_cents, withdrawal_details)

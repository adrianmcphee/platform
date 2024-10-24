from django.db import transaction
from typing import Tuple, Optional, Dict
import logging
from ..interfaces import OrganisationWalletServiceInterface
from ..models import OrganisationWallet, OrganisationWalletTransaction
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class OrganisationWalletService(OrganisationWalletServiceInterface):
    def add_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        payment_method: str,
        transaction_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = (
                    OrganisationWallet.objects
                    .select_for_update()
                    .get(id=wallet_id)
                )
                
                if amount_cents <= 0:
                    return False, "Amount must be positive"
                
                wallet.balance_usd_cents += amount_cents
                wallet.save()
                
                OrganisationWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=OrganisationWalletTransaction.TransactionType.CREDIT,
                    description=description,
                    payment_method=payment_method,
                    transaction_id=transaction_id
                )
                
                return True, "Funds added successfully"
                
        except OrganisationWallet.DoesNotExist:
            logger.error(f"Wallet {wallet_id} not found")
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error adding funds to wallet {wallet_id}: {str(e)}")
            return False, f"Error adding funds: {str(e)}"

    def deduct_funds(
        self,
        wallet_id: str,
        amount_cents: int,
        description: str,
        order_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                wallet = (
                    OrganisationWallet.objects
                    .select_for_update()
                    .get(id=wallet_id)
                )
                
                if amount_cents <= 0:
                    return False, "Amount must be positive"
                
                if wallet.balance_usd_cents < amount_cents:
                    return False, "Insufficient funds"
                
                wallet.balance_usd_cents -= amount_cents
                wallet.save()
                
                OrganisationWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=amount_cents,
                    transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
                    description=description,
                    related_order_id=order_id
                )
                
                return True, "Funds deducted successfully"
                
        except OrganisationWallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception as e:
            logger.error(f"Error deducting funds from wallet {wallet_id}: {str(e)}")
            return False, str(e)

    def get_balance(self, wallet_id: str) -> int:
        try:
            wallet = OrganisationWallet.objects.get(id=wallet_id)
            return wallet.balance_usd_cents
        except OrganisationWallet.DoesNotExist:
            raise ValidationError("Wallet not found")
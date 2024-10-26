from typing import Tuple, Union
from django.db import transaction
from django.core.exceptions import ValidationError
from django.apps import apps
from apps.commerce.models import OrganisationWallet, OrganisationWalletTransaction
from apps.commerce.services import PayPalPaymentStrategy, USDTPaymentStrategy
from apps.commerce.services import activate_challenge, activate_competition
import logging

logger = logging.getLogger(__name__)

class BountyFundingService:
    @staticmethod
    def fund_bounty(
        bounty,
        organisation_wallet: OrganisationWallet,
        amount_cents: int,
        payment_strategy: Union[PayPalPaymentStrategy, USDTPaymentStrategy, None] = None,
        **payment_details
    ) -> Tuple[bool, str]:
        """
        Service to fund a bounty using the specified payment strategy or wallet balance.
        """
        try:
            with transaction.atomic():
                if organisation_wallet.balance_cents >= amount_cents:
                    # Use existing wallet balance
                    organisation_wallet.balance_cents -= amount_cents
                    organisation_wallet.save()
                elif payment_strategy:
                    # Validate and process external payment
                    payment_strategy.validate_payment(**payment_details)
                    payment_strategy.process_payment(organisation_wallet, amount_cents)
                    
                    # Credit the wallet
                    organisation_wallet.balance_cents += amount_cents
                    organisation_wallet.save()
                    
                    OrganisationWalletTransaction.objects.create(
                        wallet=organisation_wallet,
                        amount_cents=amount_cents,
                        transaction_type='CREDIT',
                        description=f'External payment for bounty {bounty.id}'
                    )
                else:
                    raise ValidationError("Insufficient wallet balance and no payment strategy provided")

                # Debit the wallet to fund the bounty
                OrganisationWalletTransaction.objects.create(
                    wallet=organisation_wallet,
                    amount_cents=amount_cents,
                    transaction_type='DEBIT',
                    description=f'Funding for bounty {bounty.id}'
                )

                # Update the bounty's funding
                bounty.funded_amount_cents += amount_cents
                bounty.save()

                # Activate the bounty if it's a challenge or competition
                if bounty.bounty_type == 'CHALLENGE':
                    activate_challenge(bounty)
                elif bounty.bounty_type == 'COMPETITION':
                    activate_competition(bounty)

            return True, "Bounty funded successfully"

        except ValidationError as e:
            logger.error(f"Validation error while funding bounty: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Error while funding bounty: {str(e)}")
            return False, "An unexpected error occurred while funding the bounty"

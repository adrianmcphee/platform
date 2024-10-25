import logging
from typing import Dict, Tuple, Optional
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.apps import apps

from ..interfaces import BountyBidServiceInterface
from ..models import BountyBid, BountyClaim, Person

logger = logging.getLogger(__name__)

class BountyBidService(BountyBidServiceInterface):
    @transaction.atomic
    def create_bid(
        self,
        bounty_id: str,
        person_id: str,
        expected_finish_date: date,
        message: Optional[str] = None,
        amount_in_usd_cents: Optional[int] = None,
        amount_in_points: Optional[int] = None
    ) -> Tuple[bool, str]:
        try:
            # Get bounty and validate status
            Bounty = apps.get_model('product_management', 'Bounty')
            bounty = Bounty.objects.get(id=bounty_id)
            
            if bounty.status != Bounty.BountyStatus.DRAFT:
                return False, "Bounty is not available for bidding"

            # Validate person
            person = Person.objects.get(id=person_id)

            # Validate bid amounts based on bounty type
            if bounty.reward_type == 'USD':
                if amount_in_usd_cents is None:
                    return False, "USD amount is required for USD bounties"
                if amount_in_points is not None:
                    return False, "Points amount should not be set for USD bounties"
            else:  # Points bounty
                if amount_in_points is None:
                    return False, "Points amount is required for Points bounties"
                if amount_in_usd_cents is not None:
                    return False, "USD amount should not be set for Points bounties"

            # Check for existing bid
            if BountyBid.objects.filter(bounty=bounty, person=person).exists():
                return False, "Person has already bid on this bounty"

            # Create bid
            BountyBid.objects.create(
                bounty=bounty,
                person=person,
                amount_in_usd_cents=amount_in_usd_cents,
                amount_in_points=amount_in_points,
                expected_finish_date=expected_finish_date,
                message=message
            )

            return True, "Bid created successfully"

        except (Bounty.DoesNotExist, Person.DoesNotExist):
            return False, "Invalid bounty or person ID"
        except Exception as e:
            logger.error(f"Error creating bid: {str(e)}")
            return False, "Failed to create bid"

    @transaction.atomic
    def accept_bid(self, bid_id: str, reviewer_id: str) -> Tuple[bool, str]:
        try:
            bid = BountyBid.objects.select_for_update().get(id=bid_id)
            
            if bid.status != BountyBid.Status.PENDING:
                return False, "Only pending bids can be accepted"

            # Update bid status
            bid.status = BountyBid.Status.ACCEPTED
            bid.save()

            # Create or update bounty claim
            BountyClaim.objects.get_or_create(
                bounty=bid.bounty,
                person=bid.person,
                defaults={'accepted_bid': bid}
            )

            # Update bounty final reward
            if bid.bounty.reward_type == 'USD':
                bid.bounty.final_reward_in_usd_cents = bid.amount_in_usd_cents
            else:
                bid.bounty.final_reward_in_points = bid.amount_in_points

            bid.bounty.status = bid.bounty.BountyStatus.IN_PROGRESS
            bid.bounty.save()

            # Process reward adjustment if needed
            success, message = self._process_reward_adjustment(bid)
            if not success:
                raise ValidationError(message)

            return True, "Bid accepted successfully"

        except BountyBid.DoesNotExist:
            return False, "Bid not found"
        except Exception as e:
            logger.error(f"Error accepting bid: {str(e)}")
            return False, "Failed to accept bid"

    @transaction.atomic
    def reject_bid(self, bid_id: str, reviewer_id: str, reason: str) -> Tuple[bool, str]:
        try:
            bid = BountyBid.objects.select_for_update().get(id=bid_id)
            
            if bid.status != BountyBid.Status.PENDING:
                return False, "Only pending bids can be rejected"

            bid.status = BountyBid.Status.REJECTED
            bid.message = f"Rejection reason: {reason}"
            bid.save()

            return True, "Bid rejected successfully"

        except BountyBid.DoesNotExist:
            return False, "Bid not found"
        except Exception as e:
            logger.error(f"Error rejecting bid: {str(e)}")
            return False, "Failed to reject bid"

    @transaction.atomic
    def withdraw_bid(self, bid_id: str, person_id: str) -> Tuple[bool, str]:
        try:
            bid = BountyBid.objects.select_for_update().get(
                id=bid_id,
                person_id=person_id
            )
            
            if bid.status != BountyBid.Status.PENDING:
                return False, "Only pending bids can be withdrawn"

            bid.status = BountyBid.Status.WITHDRAWN
            bid.save()

            return True, "Bid withdrawn successfully"

        except BountyBid.DoesNotExist:
            return False, "Bid not found or unauthorized"
        except Exception as e:
            logger.error(f"Error withdrawing bid: {str(e)}")
            return False, "Failed to withdraw bid"

    def _process_reward_adjustment(self, bid: BountyBid) -> Tuple[bool, str]:
        """Process reward adjustments for accepted bids"""
        try:
            SalesOrder = apps.get_model('commerce', 'SalesOrder')
            original_order = SalesOrder.objects.get(
                cart__items__bounty=bid.bounty,
                adjustment_type="INITIAL"
            )

            # Calculate difference
            if bid.bounty.reward_type == 'USD':
                difference = bid.amount_in_usd_cents - bid.bounty.reward_in_usd_cents
            else:
                difference = bid.amount_in_points - bid.bounty.reward_in_points

            if difference > 0:
                return self._create_increase_adjustment(bid, original_order, difference)
            elif difference < 0:
                return self._create_decrease_adjustment(bid, original_order, abs(difference))

            return True, "No adjustment needed"

        except SalesOrder.DoesNotExist:
            # Handle point-based bounties or cases without original order
            return True, "No adjustment needed for this type of bounty"
        except Exception as e:
            logger.error(f"Error processing reward adjustment: {str(e)}")
            return False, "Failed to process reward adjustment"

    def _create_increase_adjustment(
        self,
        bid: BountyBid,
        original_order: any,
        amount: int
    ) -> Tuple[bool, str]:
        try:
            Cart = apps.get_model('commerce', 'Cart')
            SalesOrder = apps.get_model('commerce', 'SalesOrder')
            SalesOrderLineItem = apps.get_model('commerce', 'SalesOrderLineItem')

            # Create new cart
            cart = Cart.objects.create(
                user=original_order.cart.user,
                organisation=original_order.cart.organisation,
                product=bid.bounty.product,
                status=Cart.CartStatus.COMPLETED
            )

            # Create adjustment order
            order = SalesOrder.objects.create(
                cart=cart,
                status=SalesOrder.OrderStatus.COMPLETED,
                total_usd_cents=amount,
                parent_sales_order=original_order
            )

            # Create line item
            SalesOrderLineItem.objects.create(
                sales_order=order,
                item_type=SalesOrderLineItem.ItemType.INCREASE_ADJUSTMENT,
                quantity=1,
                unit_price_cents=amount,
                bounty=bid.bounty,
                related_bounty_bid=bid
            )

            # Process payment
            order.process_payment()

            return True, "Increase adjustment processed"

        except Exception as e:
            logger.error(f"Error creating increase adjustment: {str(e)}")
            return False, "Failed to create increase adjustment"

    def _create_decrease_adjustment(
        self,
        bid: BountyBid,
        original_order: any,
        amount: int
    ) -> Tuple[bool, str]:
        try:
            Cart = apps.get_model('commerce', 'Cart')
            SalesOrder = apps.get_model('commerce', 'SalesOrder')
            SalesOrderLineItem = apps.get_model('commerce', 'SalesOrderLineItem')

            # Create new cart
            cart = Cart.objects.create(
                user=original_order.cart.user,
                organisation=original_order.cart.organisation,
                product=bid.bounty.product,
                status=Cart.CartStatus.COMPLETED
            )

            # Create adjustment order
            order = SalesOrder.objects.create(
                cart=cart,
                status=SalesOrder.OrderStatus.COMPLETED,
                total_usd_cents=amount,
                parent_sales_order=original_order
            )

            # Create line item
            SalesOrderLineItem.objects.create(
                sales_order=order,
                item_type=SalesOrderLineItem.ItemType.DECREASE_ADJUSTMENT,
                quantity=1,
                unit_price_cents=amount,
                bounty=bid.bounty,
                related_bounty_bid=bid
            )

            # Process refund
            organisation_wallet = original_order.cart.organisation.wallet
            organisation_wallet.add_funds(
                amount_cents=amount,
                description=f"Refund for bounty adjustment: {bid.bounty.title}",
                related_order=order
            )

            return True, "Decrease adjustment processed"

        except Exception as e:
            logger.error(f"Error creating decrease adjustment: {str(e)}")
            return False, "Failed to create decrease adjustment"
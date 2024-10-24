from django.db import transaction
from typing import Tuple, List, Optional
import logging
from ..interfaces import CartServiceInterface, TaxServiceInterface, FeeServiceInterface
from ..models import Cart, CartLineItem, Bounty
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class CartService(CartServiceInterface):
    def __init__(
        self,
        tax_service: TaxServiceInterface,
        fee_service: FeeServiceInterface
    ):
        self.tax_service = tax_service
        self.fee_service = fee_service

    def add_bounty(
        self,
        cart_id: str,
        bounty_id: str,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                cart = Cart.objects.select_for_update().get(id=cart_id)
                
                if cart.status != Cart.CartStatus.OPEN:
                    return False, "Cart is not open"
                
                bounty = Bounty.objects.get(id=bounty_id)
                
                # Validate bounty can be added
                if bounty.status != Bounty.BountyStatus.DRAFT:
                    return False, "Bounty is not available for purchase"
                    
                # Check if bounty already in cart
                if CartLineItem.objects.filter(cart=cart, bounty=bounty).exists():
                    return False, "Bounty already in cart"
                
                # Create line item
                CartLineItem.objects.create(
                    cart=cart,
                    bounty=bounty,
                    item_type=CartLineItem.ItemType.BOUNTY,
                    quantity=quantity,
                    unit_price_usd_cents=bounty.reward_in_usd_cents,
                    unit_price_points=bounty.reward_in_points,
                    funding_type=bounty.reward_type
                )
                
                # Update totals
                success, message = self.update_totals(cart_id)
                if not success:
                    raise ValidationError(message)
                
                return True, "Bounty added to cart"
                
        except Cart.DoesNotExist:
            return False, "Cart not found"
        except Bounty.DoesNotExist:
            return False, "Bounty not found"
        except Exception as e:
            logger.error(f"Error adding bounty to cart: {str(e)}")
            return False, str(e)

    def update_totals(self, cart_id: str) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                cart = Cart.objects.select_for_update().get(id=cart_id)
                
                # Calculate base total (excluding fees and taxes)
                base_total = sum(
                    item.unit_price_usd_cents * item.quantity
                    for item in cart.line_items.filter(
                        item_type=CartLineItem.ItemType.BOUNTY,
                        funding_type='USD'
                    )
                )
                
                # Calculate platform fee
                platform_fee = self.fee_service.calculate_platform_fee(base_total)
                
                # Calculate tax
                tax = self.tax_service.calculate_tax(
                    base_total,
                    cart.organisation.country
                )
                
                # Update or create fee line item
                CartLineItem.objects.update_or_create(
                    cart=cart,
                    item_type=CartLineItem.ItemType.PLATFORM_FEE,
                    defaults={
                        'quantity': 1,
                        'unit_price_usd_cents': platform_fee,
                        'funding_type': 'USD'
                    }
                )
                
                # Update or create tax line item
                CartLineItem.objects.update_or_create(
                    cart=cart,
                    item_type=CartLineItem.ItemType.SALES_TAX,
                    defaults={
                        'quantity': 1,
                        'unit_price_usd_cents': tax,
                        'funding_type': 'USD'
                    }
                )
                
                # Update cart totals
                cart.total_usd_cents_excluding_fees_and_taxes = base_total
                cart.total_usd_cents_including_fees_and_taxes = base_total + platform_fee + tax
                cart.save(updating_totals=True)
                
                return True, "Cart totals updated"
                
        except Cart.DoesNotExist:
            return False, "Cart not found"
        except Exception as e:
            logger.error(f"Error updating cart totals: {str(e)}")
            return False, str(e)

    def validate(self, cart_id: str) -> Tuple[bool, List[str]]:
        try:
            cart = Cart.objects.get(id=cart_id)
            errors = []
            
            # Check cart status
            if cart.status != Cart.CartStatus.OPEN:
                errors.append("Cart is not open")
            
            # Check cart has items
            if not cart.line_items.filter(item_type=CartLineItem.ItemType.BOUNTY).exists():
                errors.append("Cart has no items")
            
            # Validate each bounty in cart
            for item in cart.line_items.filter(item_type=CartLineItem.ItemType.BOUNTY):
                if not item.bounty or item.bounty.status != Bounty.BountyStatus.DRAFT:
                    errors.append(f"Bounty {item.bounty.id if item.bounty else 'Unknown'} is not available")
                    
                if item.quantity <= 0:
                    errors.append(f"Invalid quantity for bounty {item.bounty.id if item.bounty else 'Unknown'}")
            
            # Validate totals
            if cart.total_usd_cents_including_fees_and_taxes <= 0:
                errors.append("Cart total must be greater than zero")
            
            return not bool(errors), errors
            
        except Cart.DoesNotExist:
            return False, ["Cart not found"]
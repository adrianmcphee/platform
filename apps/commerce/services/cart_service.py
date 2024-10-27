from django.db import transaction
from typing import Tuple, List, Optional
import logging
from ..interfaces import CartServiceInterface, TaxServiceInterface, FeeServiceInterface, BountyPurchaseInterface
from ..models import Cart, CartLineItem, OrganisationPointGrantRequest
from django.core.exceptions import ValidationError
from apps.common.data_transfer_objects import BountyPurchaseData

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
        bounty_data: BountyPurchaseData,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                cart = Cart.objects.select_for_update().get(id=cart_id)
                
                if cart.status != Cart.CartStatus.OPEN:
                    return False, "Cart is not open"
                
                if bounty_data.status != "DRAFT":
                    return False, "Item is not available for purchase"
                    
                if CartLineItem.objects.filter(cart=cart, bounty_id=bounty_data.id).exists():
                    return False, "Item already in cart"
                
                CartLineItem.objects.create(
                    cart=cart,
                    bounty_id=bounty_data.id,
                    item_type=CartLineItem.ItemType.BOUNTY,
                    quantity=quantity,
                    unit_price_usd_cents=bounty_data.reward_in_usd_cents,
                    unit_price_points=bounty_data.reward_in_points,
                    funding_type=bounty_data.reward_type
                )
                
                success, message = self.update_totals(cart_id)
                if not success:
                    raise ValidationError(message)
                
                return True, "Item added to cart"
                
        except Cart.DoesNotExist:
            return False, "Cart not found"
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
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
                if not item.bounty_id:
                    errors.append(f"Invalid bounty item in cart")
                    
                if item.quantity <= 0:
                    errors.append(f"Invalid quantity for bounty {item.bounty_id}")
                
                if item.unit_price_usd_cents is None and item.unit_price_points is None:
                    errors.append(f"Invalid price for bounty {item.bounty_id}")
            
            # Validate totals
            if cart.total_usd_cents_including_fees_and_taxes <= 0:
                errors.append("Cart total must be greater than zero")
            
            return not bool(errors), errors
            
        except Cart.DoesNotExist:
            return False, ["Cart not found"]

    def add_point_grant_request(
        self,
        cart_id: str,
        grant_request_id: str,
        quantity: int = 1
    ) -> Tuple[bool, str]:
        try:
            with transaction.atomic():
                cart = Cart.objects.select_for_update().get(id=cart_id)
                
                if cart.status != Cart.CartStatus.OPEN:
                    return False, "Cart is not open"
                
                grant_request = OrganisationPointGrantRequest.objects.get(id=grant_request_id)
                
                if grant_request.grant_type != OrganisationPointGrantRequest.GrantType.PAID:
                    return False, "Only paid grant requests can be added to cart"
                
                # Create line item
                CartLineItem.objects.create(
                    cart=cart,
                    item_type=CartLineItem.ItemType.POINT_GRANT,
                    quantity=quantity,
                    unit_price_points=grant_request.number_of_points,
                    point_grant_request=grant_request
                )
                
                # Update totals
                success, message = self.update_totals(cart_id)
                if not success:
                    raise ValidationError(message)
                
                return True, "Point grant request added to cart"
                
        except Cart.DoesNotExist:
            return False, "Cart not found"
        except OrganisationPointGrantRequest.DoesNotExist:
            return False, "Grant request not found"
        except Exception as e:
            logger.error(f"Error adding point grant request to cart: {str(e)}")
            return False, str(e)

from django.db import transaction
from typing import Tuple, Optional, Dict, List
import logging
from ..interfaces import SalesOrderServiceInterface
from ..models import SalesOrder, Cart, SalesOrderLineItem, CartLineItem
from django.core.exceptions import ValidationError
from .organisation_point_grant_service import OrganisationPointGrantService
from apps.product_management.services.bounty_service import BountyService

logger = logging.getLogger(__name__)

class SalesOrderService(SalesOrderServiceInterface):
    @transaction.atomic
    def create_from_cart(self, cart_id: str) -> Tuple[bool, str]:
        try:
            cart = Cart.objects.select_for_update().get(id=cart_id)
            
            if cart.status != Cart.CartStatus.OPEN:
                return False, "Cart is not open"
            
            sales_order, created = SalesOrder.objects.get_or_create(cart=cart)
            
            if not created:
                return False, "Sales order already exists for this cart"
            
            sales_order.organisation = cart.organisation
            self.create_line_items_from_cart(sales_order, cart)
            sales_order.update_totals()
            sales_order.save()
            
            return True, "Sales order created successfully"
            
        except Cart.DoesNotExist:
            logger.error(f"Cart {cart_id} not found")
            return False, "Cart not found"
        except Exception as e:
            logger.error(f"Error creating sales order for cart {cart_id}: {str(e)}")
            return False, f"Error creating sales order: {str(e)}"

    @transaction.atomic
    def process_payment(self, order_id: str) -> Tuple[bool, str]:
        try:
            sales_order = SalesOrder.objects.select_for_update().get(id=order_id)
            
            success, message = sales_order.process_payment()
            
            if success:
                sales_order.cart.status = Cart.CartStatus.CHECKED_OUT
                sales_order.cart.save()
            
            return success, message
            
        except SalesOrder.DoesNotExist:
            logger.error(f"Sales order {order_id} not found")
            return False, "Sales order not found"
        except Exception as e:
            logger.error(f"Error processing payment for sales order {order_id}: {str(e)}")
            return False, f"Error processing payment: {str(e)}"

    def validate(self, order_id: str) -> Tuple[bool, List[str]]:
        try:
            sales_order = SalesOrder.objects.get(id=order_id)
            errors = []

            # Check order status
            if sales_order.status != SalesOrder.OrderStatus.PENDING:
                errors.append("Order is not in pending status")

            # Check if order has line items
            if not sales_order.line_items.exists():
                errors.append("Order has no line items")

            # Validate total amount
            if sales_order.total_usd_cents_including_fees_and_taxes <= 0:
                errors.append("Order total must be greater than zero")

            # Validate organisation wallet balance
            wallet = sales_order.organisation.wallet
            if wallet.balance_usd_cents < sales_order.total_usd_cents_including_fees_and_taxes:
                errors.append("Insufficient funds in organisation wallet")

            return not bool(errors), errors

        except SalesOrder.DoesNotExist:
            logger.error(f"Sales order {order_id} not found")
            return False, ["Sales order not found"]
        except Exception as e:
            logger.error(f"Error validating sales order {order_id}: {str(e)}")
            return False, [f"Error validating order: {str(e)}"]

    def process_paid_point_grants(self, order_id: str) -> Tuple[bool, str]:
        try:
            order = SalesOrder.objects.get(id=order_id)
            if order.status != SalesOrder.OrderStatus.PAID:
                return False, "Order is not paid"
            
            point_grant_service = OrganisationPointGrantService()
            errors = []
            
            for item in order.line_items.filter(item_type=SalesOrderLineItem.ItemType.POINT_GRANT):
                with transaction.atomic():
                    success, message = point_grant_service.process_paid_grant(
                        grant_request_id=item.point_grant_request.id,
                        sales_order_item_id=item.id
                    )
                    if not success:
                        errors.append(f"Failed to process paid grant for item {item.id}: {message}")
            
            if errors:
                return False, "; ".join(errors)
            return True, "All paid point grants processed successfully"
        except SalesOrder.DoesNotExist:
            return False, "Order not found"
        except Exception as e:
            logger.error(f"Error processing paid point grants: {str(e)}")
            return False, str(e)

    def create_line_items_from_cart(self, sales_order: SalesOrder, cart: Cart) -> None:
        # Implementation to create line items based on the associated cart
        for cart_item in cart.items.all():
            SalesOrderLineItem.objects.create(
                sales_order=sales_order,
                item_type=cart_item.item_type,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                # Add other fields as necessary
            )

    def process_order_items(self, order_id: str) -> Tuple[bool, str]:
        """Process items in a completed order"""
        try:
            with transaction.atomic():
                sales_order = SalesOrder.objects.select_related('cart').get(id=order_id)
                
                if sales_order.status != SalesOrder.OrderStatus.PAID:
                    return False, "Order is not paid"
                    
                bounty_service = BountyService()
                
                for item in sales_order.cart.line_items.filter(
                    item_type=CartLineItem.ItemType.BOUNTY
                ):
                    # Create funded bounty for each bounty line item
                    success, message, bounty_id = bounty_service.create_bounty_from_cart_item(
                        product_id=item.metadata['product_id'],
                        cart_item_data=item.__dict__
                    )
                    
                    if not success:
                        raise ValidationError(f"Failed to create bounty: {message}")
                        
                    # Update order item with bounty reference
                    SalesOrderLineItem.objects.filter(
                        sales_order=sales_order,
                        cart_line_item=item
                    ).update(bounty_id=bounty_id)
                
                return True, "Order items processed successfully"
                
        except Exception as e:
            logger.error(f"Error processing order items: {str(e)}")
            return False, str(e)

    def process_paid_items(self, order_id: str) -> Tuple[bool, str]:
        """Process items after successful payment"""
        try:
            with transaction.atomic():
                order = SalesOrder.objects.select_for_update().get(id=order_id)
                
                for item in order.line_items.filter(item_type=CartLineItem.ItemType.BOUNTY):
                    bounty_service = BountyService()
                    success, message, bounty_id = bounty_service.create_bounty_from_cart_item(
                        product_id=item.metadata['product_id'],
                        cart_item_data=item.metadata
                    )
                    
                    if not success:
                        raise ValidationError(f"Failed to create bounty: {message}")
                    
                    # Update the line item with the created bounty ID
                    item.metadata['bounty_id'] = bounty_id
                    item.save()
                
                return True, "Items processed successfully"
                
        except Exception as e:
            logger.error(f"Error processing paid items: {str(e)}")
            return False, str(e)

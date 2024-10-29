import logging
from typing import Dict, Any
from django_q.tasks import async_task
from django.db import transaction
from django.apps import apps

from apps.commerce.models import SalesOrder, SalesOrderLineItem
from apps.product_management.services.bounty_service import BountyService
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.event_hub.services.factory import get_event_bus

logger = logging.getLogger(__name__)

# Get the event bus instance
event_bus = get_event_bus()


def _process_order(sales_order_id: str) -> tuple[bool, str]:
    """
    Internal function to process order items.
    Separated to allow both sync and async execution.
    """
    logger.info(f"Starting to process order {sales_order_id}")
    try:
        # Initialize service
        service = SalesOrderService()
        
        # Process the order
        success, message = service.process_paid_items(sales_order_id)
        logger.info(f"Order {sales_order_id} processed: success={success}, message={message}")
        return success, message
        
    except Exception as e:
        error_message = f"Error processing sales order {sales_order_id}: {str(e)}"
        logger.exception(error_message)
        return False, error_message


def _handle_process_result(task):
    """Handle the async task result"""
    logger.info(f"Handling process result for task: {task}")
    success, message = task.result
    sales_order_id = task.args[0]  # First argument passed to the task
    
    if success:
        logger.info(f"Successfully processed sales order {sales_order_id}: {message}")
        event_bus.emit_event('order_processing_completed', {
            'sales_order_id': sales_order_id,
            'message': message
        })
    else:
        logger.error(f"Failed to process sales order {sales_order_id}: {message}")
        event_bus.emit_event('order_processing_failed', {
            'sales_order_id': sales_order_id,
            'error': message
        })


def process_paid_order_items(payload):
    """Process paid order items"""
    try:
        service = SalesOrderService()
        bounty_service = BountyService()
        
        # Get the order
        order = SalesOrder.objects.get(id=payload['sales_order_id'])
        
        # Process each line item
        for line_item in order.line_items.all():
            if line_item.item_type == SalesOrderLineItem.ItemType.BOUNTY:
                # Create bounty using BountyService with updated parameters
                success, message, bounty_id = bounty_service.create_bounty(
                    details={
                        'title': line_item.metadata['title'],
                        'description': line_item.metadata['description'],
                        'reward_type': line_item.metadata['reward_type'],
                        'reward_amount': line_item.unit_price_usd_cents,
                    },
                    skill_id=line_item.metadata['skill_id'],
                    expertise_ids=line_item.metadata['expertise_ids'],
                    product_id=line_item.metadata['product_id'],
                    challenge_id=None,
                    competition_id=None
                )
                
                if not success:
                    raise ValueError(f"Failed to create bounty: {message}")

    except Exception as e:
        logger.error(f"Error processing order: {str(e)}")
        raise ValueError(f"Failed to process order: {str(e)}")


# Register the listener using the event bus instance
event_bus.register_listener('order_payment_completed', process_paid_order_items)
logger.info("Registered order_payment_completed listener")

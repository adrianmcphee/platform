import logging
from typing import Dict, Any

from apps.commerce.services import SalesOrderService
from apps.event_hub.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@EventBus.register_listener('order_payment_completed')
def process_paid_order_items(payload: Dict[str, Any]) -> None:
    """
    Process items for an order after payment has been completed.
    
    Args:
        payload (Dict[str, Any]): Event payload containing:
            - sales_order_id: Unique identifier of the sales order to process
            
    Emits Events:
        - order_processing_completed: When items are processed successfully
        - order_processing_failed: When processing fails or encounters an error
    """
    try:
        sales_order_id = payload.get('sales_order_id')
        if not sales_order_id:
            raise ValueError("Missing required field 'sales_order_id' in payload")

        service = SalesOrderService()
        success, message = service.process_paid_items(sales_order_id)
        
        if success:
            logger.info(f"Successfully processed sales order {sales_order_id}: {message}")
            EventBus.emit_event('order_processing_completed', {
                'sales_order_id': sales_order_id,
                'message': message
            })
        else:
            logger.error(f"Failed to process sales order {sales_order_id}: {message}")
            EventBus.emit_event('order_processing_failed', {
                'sales_order_id': sales_order_id,
                'error': message
            })
            
    except ValueError as ve:
        error_message = f"Invalid payload for sales order processing: {str(ve)}"
        logger.error(error_message)
        EventBus.emit_event('order_processing_failed', {
            'sales_order_id': payload.get('sales_order_id'),
            'error': error_message
        })
        
    except Exception as e:
        error_message = f"Error processing sales order from payload {payload}: {str(e)}"
        logger.exception(error_message)
        EventBus.emit_event('order_processing_failed', {
            'sales_order_id': payload.get('sales_order_id'),
            'error': error_message
        })

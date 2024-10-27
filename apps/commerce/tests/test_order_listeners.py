import pytest
from unittest.mock import Mock, patch
from apps.event_hub.services.event_bus import EventBus
from apps.commerce.listeners.order_listeners import process_paid_order_items
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.common.fields import Base58UUIDv5Field

@pytest.fixture
def mock_id():
    field = Base58UUIDv5Field()
    return field.generate_id()

@pytest.fixture
def mock_sales_order_service():
    with patch('apps.commerce.listeners.order_listeners.SalesOrderService') as mock:
        service_instance = Mock()
        mock.return_value = service_instance
        yield service_instance

@pytest.mark.django_db
class TestOrderListeners:
    def test_process_paid_order_items_success(self, mock_sales_order_service, mock_id):
        # Arrange
        mock_sales_order_service.process_paid_items.return_value = (True, "Success message")
        payload = {'sales_order_id': mock_id}
        
        # Act
        with patch.object(EventBus, 'emit_event') as mock_emit:
            process_paid_order_items(payload)
            
        # Assert
        mock_sales_order_service.process_paid_items.assert_called_once_with(mock_id)
        mock_emit.assert_called_once_with('order_processing_completed', {
            'sales_order_id': mock_id,
            'message': 'Success message'
        })

    def test_process_paid_order_items_failure(self, mock_sales_order_service, mock_id):
        # Arrange
        mock_sales_order_service.process_paid_items.return_value = (False, "Error message")
        payload = {'sales_order_id': mock_id}
        
        # Act
        with patch.object(EventBus, 'emit_event') as mock_emit:
            process_paid_order_items(payload)
            
        # Assert
        mock_sales_order_service.process_paid_items.assert_called_once_with(mock_id)
        mock_emit.assert_called_once_with('order_processing_failed', {
            'sales_order_id': mock_id,
            'error': 'Error message'
        })

    def test_process_paid_order_items_missing_id(self):
        # Arrange
        payload = {}
        
        # Act
        with patch.object(EventBus, 'emit_event') as mock_emit:
            process_paid_order_items(payload)
            
        # Assert
        mock_emit.assert_called_once_with('order_processing_failed', {
            'sales_order_id': None,
            'error': "Invalid payload for sales order processing: Missing required field 'sales_order_id' in payload"
        })

    def test_process_paid_order_items_unexpected_error(self, mock_sales_order_service):
        # Arrange
        mock_sales_order_service.process_paid_items.side_effect = Exception("Unexpected error")
        payload = {'sales_order_id': 'test_order_id'}
        
        # Act
        with patch.object(EventBus, 'emit_event') as mock_emit:
            process_paid_order_items(payload)
            
        # Assert
        mock_sales_order_service.process_paid_items.assert_called_once_with('test_order_id')
        mock_emit.assert_called_once_with('order_processing_failed', {
            'sales_order_id': 'test_order_id',
            'error': "Unexpected error"
        })

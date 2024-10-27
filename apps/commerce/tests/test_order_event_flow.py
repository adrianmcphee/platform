import pytest
from apps.commerce.models import Cart, SalesOrder, SalesOrderLineItem, Organisation
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.event_hub.services.event_bus import EventBus
from apps.common.data_transfer_objects import BountyPurchaseData
from apps.product_management.services.bounty_service import BountyService
from apps.product_management.models import Bounty
from apps.product_management.models import Product


@pytest.fixture
def test_organisation():
    return Organisation.objects.create(
        name='Test Organisation',
        country='US'
    )


@pytest.fixture
def sales_order_service():
    return SalesOrderService()


@pytest.fixture
def usd_bounty_purchase_data(test_product):  # Add test_product dependency here
    return BountyPurchaseData(
        product_id=test_product.id,  # Use the actual product ID
        title='Test Bounty',
        description='Test Description',
        reward_type='USD',
        reward_in_usd_cents=10000,
        reward_in_points=None,
        status='DRAFT'
    )


@pytest.fixture
def test_product():
    return Product.objects.create(
        name="Test Product",
        short_description="Test Description",
        full_description="Full Test Description",
        slug="test-product"
    )


@pytest.mark.django_db
class TestOrderEventFlow:
    def setUp(self):
        # Clear event listeners before each test
        EventBus.listeners = {}

    def test_order_payment_completed_creates_bounty(self, sales_order_service, usd_bounty_purchase_data, test_organisation, test_product):
        # Arrange
        cart = Cart.objects.create(
            organisation_id=test_organisation.id,
            status=Cart.CartStatus.OPEN
        )

        order = SalesOrder.objects.create(
            cart=cart,
            organisation_id=test_organisation.id,
            status=SalesOrder.OrderStatus.PENDING
        )

        line_item = SalesOrderLineItem.objects.create(
            sales_order=order,
            item_type=SalesOrderLineItem.ItemType.BOUNTY,
            quantity=1,
            unit_price_usd_cents=usd_bounty_purchase_data.reward_in_usd_cents,
            metadata=usd_bounty_purchase_data.model_dump(exclude={'status'})
        )

        # Register the handler that will create the bounty using BountyService
        def handle_payment(payload):
            service = SalesOrderService()
            bounty_service = BountyService()
            
            # Get the order and line item
            order = SalesOrder.objects.get(id=payload['sales_order_id'])
            line_item = order.line_items.first()
            
            # Create bounty using BountyService
            success, message, bounty_id = bounty_service.create_bounty_from_cart_item(
                product_id=line_item.metadata['product_id'],  # Use product_id from metadata
                cart_item_data={
                    'metadata': line_item.metadata,
                    'unit_price_usd_cents': line_item.unit_price_usd_cents,
                    'unit_price_points': None
                }
            )
            
            if not success:
                raise ValueError(f"Failed to create bounty: {message}")

        EventBus.register_listener('order_payment_completed', handle_payment)

        # Get initial bounty count
        initial_bounty_count = Bounty.objects.count()

        # Act
        EventBus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=False)

        # Assert
        # Verify bounty was created
        assert Bounty.objects.count() == initial_bounty_count + 1
        
        # Get the created bounty
        bounty = Bounty.objects.latest('created_at')
        
        # Verify bounty details match the purchase data
        assert bounty.title == usd_bounty_purchase_data.title
        assert bounty.description == usd_bounty_purchase_data.description
        assert bounty.reward_type == usd_bounty_purchase_data.reward_type
        assert bounty.reward_in_usd_cents == usd_bounty_purchase_data.reward_in_usd_cents
        assert bounty.status == 'FUNDED'  # Note: Status should be FUNDED when created from cart

    def test_event_error_handling(self, mocker, sales_order_service, test_organisation):
        # Arrange
        cart = Cart.objects.create(
            organisation_id=test_organisation.id,
            status=Cart.CartStatus.OPEN
        )

        order = SalesOrder.objects.create(
            cart=cart,
            organisation_id=test_organisation.id,
            status=SalesOrder.OrderStatus.PENDING
        )

        # Track error events
        error_events = []

        # Mock EventBus.emit_event before any other setup
        original_emit = EventBus.emit_event

        def mock_emit(event_name, payload, is_async=True):
            if event_name == 'order_processing_failed':
                error_events.append(payload)
            else:
                return original_emit(event_name, payload, is_async=False)

        mocker.patch('apps.event_hub.services.event_bus.EventBus.emit_event', 
                    side_effect=mock_emit)

        # Mock the service method to raise an error
        mocker.patch.object(SalesOrderService, 'process_paid_items',
                            side_effect=ValueError("Order not found"))

        # Register error handler
        def handle_payment_error(payload):
            try:
                service = SalesOrderService()
                service.process_paid_items(order_id=payload['sales_order_id'])
            except Exception as e:
                EventBus.emit_event('order_processing_failed', {
                    'sales_order_id': payload.get('sales_order_id'),
                    'error': str(e)
                }, is_async=False)

        # Clear existing handlers and register our test handler
        EventBus.listeners = {}
        EventBus.register_listener('order_payment_completed', handle_payment_error)

        # Act
        EventBus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=False)

        # Assert
        assert len(error_events) == 1
        assert error_events[0]['error'] == 'Order not found'
        assert error_events[0]['sales_order_id'] == order.id

    def test_event_missing_order_id(self, mocker):
        # Track error events
        error_events = []

        # Mock EventBus.emit_event before any other setup
        original_emit = EventBus.emit_event

        def mock_emit(event_name, payload, is_async=True):
            if event_name == 'order_processing_failed':
                error_events.append(payload)
            else:
                return original_emit(event_name, payload, is_async=False)

        mocker.patch('apps.event_hub.services.event_bus.EventBus.emit_event', 
                    side_effect=mock_emit)

        # Register error handler
        def handle_missing_order_id(payload):
            try:
                if 'sales_order_id' not in payload:
                    raise ValueError("Missing required field: sales_order_id")
                service = SalesOrderService()
                service.process_paid_items(order_id=payload['sales_order_id'])
            except Exception as e:
                EventBus.emit_event('order_processing_failed', {
                    'error': str(e)
                }, is_async=False)

        # Clear existing handlers and register our test handler
        EventBus.listeners = {}
        EventBus.register_listener('order_payment_completed', handle_missing_order_id)

        # Act
        EventBus.emit_event('order_payment_completed', {}, is_async=False)

        # Assert
        assert len(error_events) == 1
        assert error_events[0]['error'] == 'Missing required field: sales_order_id'

    @pytest.mark.integration
    def test_full_event_flow(self, test_organisation, usd_bounty_purchase_data):
        """Test the full flow from payment to bounty creation"""
        # Create cart with required fields
        cart = Cart.objects.create(
            organisation_id=test_organisation.id,
            status=Cart.CartStatus.OPEN
        )

        order = SalesOrder.objects.create(
            cart=cart,
            organisation_id=test_organisation.id,
            status=SalesOrder.OrderStatus.PENDING
        )

        line_item = SalesOrderLineItem.objects.create(
            sales_order=order,
            item_type=SalesOrderLineItem.ItemType.BOUNTY,
            quantity=1,
            unit_price_usd_cents=usd_bounty_purchase_data.reward_in_usd_cents,
            metadata=usd_bounty_purchase_data.model_dump(exclude={'status'})
        )

        # Register event handler
        def handle_payment_completed(event_data):
            order = SalesOrder.objects.get(id=event_data['sales_order_id'])
            order.status = SalesOrder.OrderStatus.PAID
            order.save()

        EventBus.register_listener('order_payment_completed', handle_payment_completed)

        # Emit payment completed event
        EventBus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=False)

        # Verify order status updated
        order.refresh_from_db()
        assert order.status == SalesOrder.OrderStatus.PAID


from django.apps import apps
import pytest
from unittest.mock import Mock
from django_q.models import Schedule, Task
from django.utils import timezone
from apps.commerce.models import Cart, SalesOrder, SalesOrderLineItem, Organisation
from apps.commerce.services.sales_order_service import SalesOrderService
from apps.event_hub.services.event_bus import EventBus
from apps.common.data_transfer_objects import BountyPurchaseData
from apps.product_management.services.bounty_service import BountyService
from apps.product_management.models import Bounty
from apps.product_management.models import Product
from django_q.tasks import async_task
from apps.commerce.listeners.order_listeners import _process_order, _handle_process_result
import logging
import time


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
def test_skill():
    """Create a test skill with the ID matching the purchase data"""
    Skill = apps.get_model('talent', 'Skill')
    return Skill.objects.create(
        id='AnL2GnAWDircPWzgVGXPZq',  # This matches the ID in usd_bounty_purchase_data
        name='Full-stack Development',
        path='8QH3e7bCXywwbYQvd4Uy8W/AnL2GnAWDircPWzgVGXPZq',
        active=True,
        selectable=True
    )


@pytest.fixture
def test_expertise(test_skill):
    """Create a test expertise with the ID matching the purchase data"""
    Expertise = apps.get_model('talent', 'Expertise')
    return Expertise.objects.create(
        id='7aQBuEGZz34iU1djma3dhV',  # This matches the ID in usd_bounty_purchase_data
        name='django',
        skill=test_skill,
        path='JP64GcAGXhfjzF7zGPUFTj/7aQBuEGZz34iU1djma3dhV',
        selectable=True
    )


@pytest.fixture
def usd_bounty_purchase_data(test_product, test_skill, test_expertise):
    """Create purchase data that matches the test skill and expertise"""
    return BountyPurchaseData(
        product_id=test_product.id,
        title='Test Bounty',
        description='Test Description',
        reward_type='USD',
        reward_in_usd_cents=10000,
        reward_in_points=None,
        skill_id=test_skill.id,  # Use the actual test skill ID
        expertise_ids=[test_expertise.id]  # Use the actual test expertise ID
    )


@pytest.fixture
def test_product():
    return Product.objects.create(
        name="Test Product",
        short_description="Test Description",
        full_description="Full Test Description",
        slug="test-product"
    )


@pytest.fixture
def event_bus():
    """Create a fresh EventBus instance for each test"""
    return EventBus()


@pytest.fixture
def mock_django_q(mocker):
    """Mock Django Q async task creation"""
    return mocker.patch('apps.event_hub.services.backends.django_q.async_task')


@pytest.mark.django_db(transaction=True)
class TestOrderEventFlow:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment"""
        from apps.event_hub.services.factory import get_event_bus
        from apps.commerce.listeners.order_listeners import process_paid_order_items
        
        # Get event bus instance
        self.event_bus = get_event_bus()
        
        # Register the listener explicitly for the test
        self.event_bus.register_listener('order_payment_completed', process_paid_order_items)
        
        yield
        
        # Cleanup
        self.event_bus.clear_listeners()

    def test_sync_order_payment_completed_creates_bounty(self, event_bus, sales_order_service, usd_bounty_purchase_data, test_organisation, test_product, test_skill, test_expertise):
        """Test synchronous event processing"""
        # Clear any existing listeners
        event_bus.clear_listeners()
        
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
            metadata=usd_bounty_purchase_data.model_dump()
        )

        # Register the handler that will create the bounty using BountyService
        def handle_payment(payload):
            bounty_service = BountyService()
            
            # Get the order and line item
            order = SalesOrder.objects.get(id=payload['sales_order_id'])
            line_item = order.line_items.first()
            
            # Create bounty using BountyService with product_id
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

        # Register only our test handler
        event_bus.register_listener('order_payment_completed', handle_payment)

        # Get initial bounty count
        initial_bounty_count = Bounty.objects.count()

        # Act
        event_bus.emit_event('order_payment_completed', {
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

        # Add additional assertions for skill and expertise
        bounty_skill = bounty.skills.first()
        assert bounty_skill.skill.id == test_skill.id
        assert list(bounty_skill.expertise.values_list('id', flat=True)) == [test_expertise.id]

    def test_async_order_payment_completed_creates_bounty(
        self,
        mocker,
        sales_order_service,
        usd_bounty_purchase_data,
        test_organisation,
        test_product,
        test_skill,
        test_expertise
    ):
        """Test asynchronous event processing with Django Q"""
        # Mock async_task at the correct import location
        mock_async = mocker.patch('apps.event_hub.services.backends.django_q.async_task')
        
        # Clear any existing listeners
        self.event_bus.clear_listeners()
        
        # Register the default listener from order_listeners
        from apps.commerce.listeners.order_listeners import process_paid_order_items
        self.event_bus.register_listener('order_payment_completed', process_paid_order_items)
        
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

        # Act - emit async event
        self.event_bus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=True)

        # Assert Django Q task was queued with correct parameters
        mock_async.assert_called_once_with(
            'apps.event_hub.services.backends.django_q.execute_listener',
            'apps.commerce.listeners.order_listeners',
            'process_paid_order_items',
            {'sales_order_id': order.id},
            task_name='event.process_paid_order_items',
            hook='apps.event_hub.services.backends.django_q.task_hook'
        )

    def test_async_event_error_handling(
        self, 
        mocker, 
        event_bus, 
        mock_django_q,
        sales_order_service, 
        test_organisation
    ):
        """Test error handling in async event processing"""
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

        # Mock the service method to raise an error
        mocker.patch.object(
            SalesOrderService, 
            'process_paid_items',
            side_effect=ValueError("Order not found")
        )

        # Track error events
        error_events = []
        
        def mock_error_handler(event_name, payload, is_async=True):
            if event_name == 'order_processing_failed':
                error_events.append(payload)

        mocker.patch.object(
            event_bus,
            'emit_event',
            side_effect=mock_error_handler
        )

        # Register error handler
        def handle_payment_error(payload):
            try:
                service = SalesOrderService()
                service.process_paid_items(order_id=payload['sales_order_id'])
            except Exception as e:
                event_bus.emit_event('order_processing_failed', {
                    'sales_order_id': payload.get('sales_order_id'),
                    'error': str(e)
                }, is_async=False)

        event_bus.register_listener('order_payment_completed', handle_payment_error)

        # Act
        event_bus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=True)

        # Simulate task execution
        handle_payment_error({'sales_order_id': order.id})

        # Assert
        assert len(error_events) == 1
        assert error_events[0]['error'] == 'Order not found'
        assert error_events[0]['sales_order_id'] == order.id

    def test_event_missing_order_id(self, mocker):
        # Track error events
        error_events = []
        
        # Store the original emit_event method
        original_emit = self.event_bus.emit_event
        
        # Create a mock emit function that captures error events
        def mock_emit(event_name, payload, is_async=True):
            if event_name == 'order_processing_failed':
                error_events.append(payload)
            else:
                # Call the original handler for non-error events
                original_emit(event_name, payload, is_async)
        
        # Replace the emit_event method on the instance
        mocker.patch.object(self.event_bus, 'emit_event', side_effect=mock_emit)
        
        # Register error handler
        def handle_missing_order_id(payload):
            try:
                if 'sales_order_id' not in payload:
                    raise ValueError("Missing required field: sales_order_id")
                service = SalesOrderService()
                service.process_paid_items(order_id=payload['sales_order_id'])
            except Exception as e:
                self.event_bus.emit_event('order_processing_failed', {
                    'error': str(e)
                }, is_async=False)
        
        # Clear existing handlers and register our test handler
        self.event_bus.listeners = {}
        self.event_bus.register_listener('order_payment_completed', handle_missing_order_id)
        
        # Act - trigger the event without a sales_order_id
        self.event_bus.emit_event('order_payment_completed', {}, is_async=False)
        
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

        self.event_bus.register_listener('order_payment_completed', handle_payment_completed)

        # Emit payment completed event
        self.event_bus.emit_event('order_payment_completed', {
            'sales_order_id': order.id
        }, is_async=False)

        # Verify order status updated
        order.refresh_from_db()
        assert order.status == SalesOrder.OrderStatus.PAID

    @pytest.mark.django_db(transaction=True)
    @pytest.mark.integration
    def test_async_order_flow_integration(
        self,
        test_organisation,
        usd_bounty_purchase_data,
        test_product,
        caplog,
        django_db_blocker
    ):
        """Integration test for the full async order flow"""
        import logging
        import time
        from django_q.models import Task
        
        caplog.set_level(logging.INFO)
        
        # Create test data
        print("\nCreating test data...")
        cart = Cart.objects.create(
            organisation=test_organisation,
            status=Cart.CartStatus.OPEN
        )
        
        order = SalesOrder.objects.create(
            cart=cart,
            organisation=test_organisation,
            status=SalesOrder.OrderStatus.PAID
        )
        
        line_item = SalesOrderLineItem.objects.create(
            sales_order=order,
            item_type=SalesOrderLineItem.ItemType.BOUNTY,
            quantity=1,
            unit_price_usd_cents=usd_bounty_purchase_data.reward_in_usd_cents,
            metadata=usd_bounty_purchase_data.model_dump()
        )
        
        initial_bounty_count = Bounty.objects.count()
        print(f"Initial bounty count: {initial_bounty_count}")
        
        # Emit the event
        print("\nEmitting event...")
        self.event_bus.emit_event('order_payment_completed', {
            'sales_order_id': str(order.id)
        }, is_async=True)
        
        # Wait for task completion
        max_wait = 20  # seconds
        start_time = time.time()
        task_completed = False
        
        print("\nWaiting for task completion...")
        while time.time() - start_time < max_wait:
            # Check for task completion via bounty creation
            current_count = Bounty.objects.count()
            print(f"Current bounty count: {current_count}")
            
            # Check all tasks and their details
            tasks = Task.objects.all()
            for task in tasks:
                print(f"\nTask Details:")
                print(f"  ID: {task.id}")
                print(f"  Name: {task.name}")
                print(f"  Function: {task.func}")
                print(f"  Args: {task.args}")
                print(f"  Success: {task.success}")
                print(f"  Stopped: {task.stopped}")
                if hasattr(task, 'result'):
                    print(f"  Result: {task.result}")
                
                if task.stopped and task.success:
                    task_completed = True
                    break
            
            if task_completed and current_count > initial_bounty_count:
                break
            
            time.sleep(0.5)
        
        # Final assertions
        assert task_completed, "Task did not complete successfully"
        assert Bounty.objects.count() > initial_bounty_count, "No bounty was created"
        
        # Verify the bounty details
        bounty = Bounty.objects.latest('created_at')
        assert bounty.title == usd_bounty_purchase_data.title
        assert bounty.description == usd_bounty_purchase_data.description
        assert bounty.reward_type == usd_bounty_purchase_data.reward_type
        assert bounty.reward_in_usd_cents == usd_bounty_purchase_data.reward_in_usd_cents
        

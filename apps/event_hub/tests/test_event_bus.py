import pytest
from event_hub.services.event_bus import EventBus, EventLog  # Updated import

@pytest.fixture
def sample_payload():
    """Fixture to provide a sample payload for tests."""
    return {'bounty_id': 123, 'amount': 1000}

def test_register_listener(mocker, sample_payload):
    """Test that listeners are correctly registered and called when an event is emitted."""
    
    # Mock the listener function using pytest-mock
    mock_listener = mocker.Mock()

    # Register the mocked listener
    EventBus.register_listener('bounty_funded', mock_listener)

    # Emit the event
    EventBus.emit_event('bounty_funded', sample_payload)

    # Assert that the mock listener was called with the correct payload
    mock_listener.assert_called_once_with(sample_payload)

def test_multiple_listeners(mocker, sample_payload):
    """Test that multiple listeners for the same event are called correctly."""

    # Mock two different listeners
    mock_listener_1 = mocker.Mock()
    mock_listener_2 = mocker.Mock()

    # Register both listeners for the same event
    EventBus.register_listener('bounty_funded', mock_listener_1)
    EventBus.register_listener('bounty_funded', mock_listener_2)

    # Emit the event
    EventBus.emit_event('bounty_funded', sample_payload)

    # Assert that both listeners were called with the correct payload
    mock_listener_1.assert_called_once_with(sample_payload)
    mock_listener_2.assert_called_once_with(sample_payload)

def test_no_listener_called(mocker, sample_payload):
    """Test that no listeners are called when emitting an event with no listeners registered."""

    # Mock a listener
    mock_listener = mocker.Mock()

    # Emit an event with no registered listeners
    EventBus.emit_event('non_existent_event', sample_payload)

    # Assert that the mock listener was never called
    mock_listener.assert_not_called()

def test_async_event_emission(mocker, sample_payload):
    """Test that async event emission is handled correctly."""
    # Mock the delay method of celery tasks
    mock_delay = mocker.patch('celery.app.task.Task.delay')

    # Register a mock listener
    mock_listener = mocker.Mock()
    EventBus.register_listener('async_event', mock_listener)

    # Emit the event asynchronously
    EventBus.emit_event('async_event', sample_payload, is_async=True)

    # Assert that the delay method was called
    mock_delay.assert_called_once_with(sample_payload)

    # Assert that the listener itself was not called directly
    mock_listener.assert_not_called()

def test_event_logging(sample_payload):
    """Test that events are logged in the EventLog model."""
    # Clear any existing event logs
    EventLog.objects.all().delete()

    # Emit an event
    EventBus.emit_event('test_event', sample_payload)

    # Check that the event was logged
    logged_event = EventLog.objects.first()
    assert logged_event is not None
    assert logged_event.event_name == 'test_event'
    assert logged_event.payload == sample_payload
    assert logged_event.processed == False

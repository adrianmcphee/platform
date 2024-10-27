# apps/event_hub/tests/test_event_dispatcher_service.py

import pytest
from event_hub.services.event_dispatcher_service import EventDispatcherService

@pytest.fixture
def sample_payload():
    """Fixture to provide a sample payload for tests."""
    return {'bounty_id': 123, 'amount': 1000}

def test_register_listener(mocker, sample_payload):
    """Test that listeners are correctly registered and called when an event is emitted."""
    
    # Mock the listener function using pytest-mock
    mock_listener = mocker.Mock()

    # Register the mocked listener
    EventDispatcherService.register_listener('bounty_funded', mock_listener)

    # Emit the event
    EventDispatcherService.emit_event('bounty_funded', sample_payload)

    # Assert that the mock listener was called with the correct payload
    mock_listener.assert_called_once_with(sample_payload)

def test_multiple_listeners(mocker, sample_payload):
    """Test that multiple listeners for the same event are called correctly."""

    # Mock two different listeners
    mock_listener_1 = mocker.Mock()
    mock_listener_2 = mocker.Mock()

    # Register both listeners for the same event
    EventDispatcherService.register_listener('bounty_funded', mock_listener_1)
    EventDispatcherService.register_listener('bounty_funded', mock_listener_2)

    # Emit the event
    EventDispatcherService.emit_event('bounty_funded', sample_payload)

    # Assert that both listeners were called with the correct payload
    mock_listener_1.assert_called_once_with(sample_payload)
    mock_listener_2.assert_called_once_with(sample_payload)

def test_no_listener_called(mocker, sample_payload):
    """Test that no listeners are called when emitting an event with no listeners registered."""

    # Mock a listener
    mock_listener = mocker.Mock()

    # Emit an event with no registered listeners
    EventDispatcherService.emit_event('non_existent_event', sample_payload)

    # Assert that the mock listener was never called
    mock_listener.assert_not_called()

import pytest
from unittest.mock import MagicMock
from apps.event_hub.services.event_bus import EventBus
from apps.event_hub.services.backends.django_q import DjangoQBackend

@pytest.fixture
def mock_django_q(mocker):
    # Mock the async_task function
    mock_async = mocker.patch('django_q.tasks.async_task')
    return mock_async

@pytest.fixture
def event_bus():
    # Create a new EventBus instance with a mock backend for testing
    backend = DjangoQBackend()
    return EventBus(backend=backend)

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


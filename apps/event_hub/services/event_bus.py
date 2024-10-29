from django.conf import settings
import logging
from apps.event_hub.models import EventLog
from typing import Protocol, Dict, Callable, List

logger = logging.getLogger(__name__)


class EventBusBackend(Protocol):
    """Protocol defining the interface for event bus backends"""
    def enqueue_task(self, listener: Callable, payload: Dict) -> None: ...
    def execute_task_sync(self, listener: Callable, payload: Dict) -> None: ...
    def report_error(self, error: Exception, context: Dict) -> None: ...


class EventBus:
    """
    A simple event bus implementation that supports both synchronous and asynchronous event handling.
    Uses the singleton pattern to ensure only one instance exists.
    """
    _instance = None
    _initialized = False
    _listeners: Dict[str, List[Callable]] = {}

    def __new__(cls, backend=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, backend: EventBusBackend = None):
        """Initialize the EventBus with a backend if not already initialized"""
        if not self._initialized:
            if backend is None:
                raise ValueError("Backend must be provided for EventBus initialization")
            self.backend = backend
            self._initialized = True

    def register_listener(self, event_name: str, listener: Callable) -> None:
        """
        Register a listener for a specific event.
        
        Args:
            event_name: The name of the event to listen for
            listener: The callback function to execute when the event occurs
        """
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(listener)
        logger.debug(f"Registered listener {listener.__name__} for event {event_name}")

    def emit_event(self, event_name: str, payload: Dict, is_async: bool = True) -> None:
        """
        Emit an event to all registered listeners.
        """
        # Debug logging
        logger.info(f"[EventBus] Emitting event {event_name} with payload {payload}")
        logger.info(f"[EventBus] Current listeners: {self._listeners}")
        
        # Log the event
        EventLog.objects.create(event_name=event_name, payload=payload)
        
        # Get listeners for this event
        listeners = self._listeners.get(event_name, [])
        if not listeners:
            logger.warning(f"[EventBus] No listeners registered for event {event_name}")
            return

        # Process each listener
        for listener in listeners:
            try:
                logger.info(f"[EventBus] Processing listener {listener.__name__}")
                if is_async:
                    logger.info(f"[EventBus] Enqueueing async task for {listener.__name__}")
                    self.backend.enqueue_task(listener, payload)
                else:
                    logger.info(f"[EventBus] Executing sync task for {listener.__name__}")
                    self.backend.execute_task_sync(listener, payload)
            except Exception as e:
                error_context = {
                    "event_name": event_name,
                    "listener": listener.__name__,
                    "payload": payload
                }
                logger.exception(f"[EventBus] Error processing event: {str(e)}", extra=error_context)
                self.backend.report_error(e, error_context)

    def clear_listeners(self) -> None:
        """Clear all registered listeners. Useful for testing."""
        self._listeners.clear()
        logger.debug("Cleared all event listeners")

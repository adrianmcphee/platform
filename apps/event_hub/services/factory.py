from django.conf import settings
from django.utils.module_loading import import_string
from .event_bus import EventBus

def get_event_bus():
    """
    Factory function to get or create the configured EventBus instance.
    
    Returns:
        EventBus: A configured EventBus instance with the appropriate backend
    """
    try:
        # Get the backend class path from settings
        backend_path = settings.EVENT_BUS['BACKEND']
        
        # Import the backend class
        backend_class = import_string(backend_path)
        
        # Create and return the EventBus instance with the configured backend
        return EventBus(backend=backend_class())
        
    except (KeyError, ImportError) as e:
        raise ValueError(
            f"Invalid EVENT_BUS configuration. Please check your settings: {str(e)}"
        )

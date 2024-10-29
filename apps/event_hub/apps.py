from django.apps import AppConfig
from django.conf import settings

class EventHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.event_hub'
    verbose_name = 'Event Hub'
    
    def ready(self):
        """
        Initialize event listeners when the app is ready.
        """
        try:
            from apps.event_hub.services.factory import get_event_bus
            
            # Initialize the event bus
            event_bus = get_event_bus()
            
            # Import and register listeners
            from apps.commerce.listeners import order_listeners  # noqa
            #from apps.talent.listeners import bounty_listeners  # noqa
            
            # Log initialization if enabled
            if settings.EVENT_BUS.get('LOGGING_ENABLED', False):
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Event Hub initialized successfully")
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to initialize Event Hub: {str(e)}")
            raise
from django.conf import settings
from celery import Celery
from functools import wraps

# Initialize Celery with settings from Django
celery_app = Celery('event_hub')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

class EventBus:
    listeners = {}

    @classmethod
    def register_listener(cls, event_name, listener):
        if event_name not in cls.listeners:
            cls.listeners[event_name] = []
        
        @celery_app.task(name=f'event.{event_name}.{listener.__name__}')
        @wraps(listener)
        def celery_task(payload):
            return listener(payload)
        
        cls.listeners[event_name].append(celery_task)

    @classmethod
    def emit_event(cls, event_name, payload, is_async=True):
        if event_name in cls.listeners:
            for listener in cls.listeners[event_name]:
                if is_async:
                    listener.delay(payload)
                else:
                    listener.apply(args=[payload]).get()

    @classmethod
    def _dispatch_event(cls, event_name, payload):
        # This method is now deprecated, but kept for backwards compatibility
        cls.emit_event(event_name, payload, is_async=False)

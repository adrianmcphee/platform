import logging
from typing import Dict, Callable
from celery import shared_task
from functools import wraps
from django.conf import settings

logger = logging.getLogger(__name__)

class CeleryBackend:
    """Celery implementation of the EventBusBackend"""
    
    def enqueue_task(self, listener: Callable, payload: Dict) -> None:
        """
        Enqueue a task to be executed asynchronously.
        Creates a Celery task dynamically for the listener.
        """
        try:
            task_name = f'event.{listener.__module__}.{listener.__name__}'
            
            @shared_task(name=task_name)
            @wraps(listener)
            def celery_task(task_payload):
                return listener(task_payload)
            
            # Delay the task execution
            celery_task.delay(payload)
            logger.debug(f"Enqueued task {task_name} with payload {payload}")
            
        except Exception as e:
            self.report_error(e, {
                "listener": listener.__name__,
                "payload": payload,
                "action": "enqueue_task"
            })
            raise

    def execute_task_sync(self, listener: Callable, payload: Dict) -> None:
        """Execute the listener synchronously"""
        try:
            listener(payload)
            logger.debug(f"Executed {listener.__name__} synchronously with payload {payload}")
            
        except Exception as e:
            self.report_error(e, {
                "listener": listener.__name__,
                "payload": payload,
                "action": "execute_task_sync"
            })
            raise

    def report_error(self, error: Exception, context: Dict) -> None:
        """
        Report error to monitoring system.
        Logs the error and could be extended to report to external monitoring services.
        """
        error_message = f"Error in Celery backend: {str(error)}"
        logger.error(error_message, extra={
            "error_type": error.__class__.__name__,
            "context": context
        }, exc_info=True)
        
        # Could add additional error reporting here (e.g., Sentry)
        if hasattr(settings, 'SENTRY_DSN'):
            try:
                from sentry_sdk import capture_exception
                capture_exception(error)
            except ImportError:
                pass 
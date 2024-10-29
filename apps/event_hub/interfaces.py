from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class EventBusBackend(ABC):
    """Abstract base class for EventBus backends."""
    
    @abstractmethod
    def enqueue_task(self, task_path, *args, **kwargs):
        """Enqueue a task for asynchronous execution."""
        pass

    @abstractmethod
    def execute_task_sync(self, task_path, *args, **kwargs):
        """Execute a task synchronously."""
        pass

    def report_error(self, error, task_info=None):
        """Report an error during task processing."""
        logger.error(f"Error in task {task_info}: {error}") 
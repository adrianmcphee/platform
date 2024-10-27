class EventBus:
    _listeners = {}

    @classmethod
    def register_listener(cls, event_name, listener):
        """Register a listener for a specific event."""
        if event_name not in cls._listeners:
            cls._listeners[event_name] = []
        cls._listeners[event_name].append(listener)

    @classmethod
    def emit_event(cls, event_name, payload, is_async=False):
        """Emit an event and dispatch it to listeners."""
        # Optionally log the event if necessary
        if is_async:
            # TODO: Implement asynchronous event dispatch
            pass
        else:
            cls._dispatch_event(event_name, payload)

    @classmethod
    def _dispatch_event(cls, event_name, payload):
        """Dispatch the event to all registered listeners."""
        if event_name in cls._listeners:
            for listener in cls._listeners[event_name]:
                listener(payload)


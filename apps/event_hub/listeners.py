from event_hub.services.event_bus import EventBus

def handle_bounty_funded(payload):
    """Handle the event when a bounty is funded."""
    print(f"Bounty funded: {payload}")

# Register the listener for the 'bounty_funded' event
EventBus.register_listener('bounty_funded', handle_bounty_funded)

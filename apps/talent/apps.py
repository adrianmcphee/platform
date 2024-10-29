from django.apps import AppConfig
from django.apps import apps


class TalentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.talent"

    def ready(self) -> None:
        from apps.talent.services.talent_service import TalentService
        from apps.event_hub.services.event_bus import EventBus
        
        # Initialize services
        talent_service = TalentService()
        event_bus = EventBus()
        
        # Register event listeners
        event_bus.register_listener('bounty_claim_created', talent_service.handle_bounty_claim_created)
        event_bus.register_listener('bounty_completed', talent_service.handle_bounty_completed)

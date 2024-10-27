from django.apps import AppConfig


class TalentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.talent"

    def ready(self) -> None:
        import apps.talent.signals
        self.register_event_listeners()

    def register_event_listeners(self):
        from apps.event_hub.services.event_bus import EventBus
        from .services import TalentService

        talent_service = TalentService()
        EventBus.register_listener('bounty_claim_created', talent_service.handle_bounty_claim_created)
        EventBus.register_listener('bounty_claim_status_changed', talent_service.handle_bounty_claim_status_changed)

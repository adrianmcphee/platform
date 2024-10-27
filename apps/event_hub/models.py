# apps/event_hub/models.py

from django.db import models

class EventLog(models.Model):
    event_name = models.CharField(max_length=255)
    payload = models.JSONField()  # Store event data as JSON
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Event: {self.event_name} at {self.timestamp}"

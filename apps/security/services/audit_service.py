import logging
from typing import Dict, List, Optional, Tuple
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from ..interfaces import AuditServiceInterface
from ..models import AuditEvent, User

logger = logging.getLogger(__name__)

class AuditService(AuditServiceInterface):
    @transaction.atomic
    def log_event(
        self,
        user_id: Optional[str],
        action: str,
        content_type: str,
        object_id: int,
        changes: Optional[str] = None
    ) -> Tuple[bool, str]:
        try:
            # Validate action
            if action not in dict(AuditEvent.ACTION_CHOICES):
                return False, f"Invalid action: {action}"

            # Get content type
            try:
                ct = ContentType.objects.get(model=content_type.lower())
            except ContentType.DoesNotExist:
                return False, f"Invalid content type: {content_type}"

            # Get user if user_id provided
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return False, f"Invalid user_id: {user_id}"

            # Create audit event
            AuditEvent.objects.create(
                user=user,
                action=action,
                content_type=ct,
                object_id=object_id,
                changes=changes
            )

            return True, "Audit event logged successfully"

        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")
            return False, "Failed to log audit event"

    def get_audit_trail(
        self,
        content_type: str,
        object_id: int
    ) -> List[Dict]:
        try:
            ct = ContentType.objects.get(model=content_type.lower())
            
            audit_events = AuditEvent.objects.filter(
                content_type=ct,
                object_id=object_id
            ).order_by('-timestamp')

            return [{
                'id': event.id,
                'user': event.user.username if event.user else 'system',
                'action': event.action,
                'timestamp': event.timestamp,
                'changes': event.changes
            } for event in audit_events]

        except ContentType.DoesNotExist:
            logger.error(f"Invalid content type: {content_type}")
            return []
        except Exception as e:
            logger.error(f"Error retrieving audit trail: {str(e)}")
            return []
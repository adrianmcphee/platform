import logging
from typing import Dict, Tuple
from django.db import transaction
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from ..interfaces import UserAuthenticationServiceInterface
from ..models import User, SignInAttempt
from .device_service import DeviceService

logger = logging.getLogger(__name__)

class UserAuthenticationService(UserAuthenticationServiceInterface):
    def __init__(self, device_service: DeviceService):
        self.device_service = device_service

    @transaction.atomic
    def authenticate_user(self, username: str, password: str, device_info: Dict) -> Tuple[bool, str]:
        try:
            # Validate device info
            valid, message = self.device_service.validate_device_info(device_info)
            if not valid:
                return False, message

            # Generate device identifier
            device_identifier = self.device_service.generate_device_identifier(device_info)

            # Attempt authentication
            user = authenticate(username=username, password=password)
            
            if user is None:
                self.log_failed_login({'username': username}, device_info)
                return False, "Invalid credentials"

            if user.password_reset_required:
                return False, "Password reset required"

            # Log successful login
            self.log_successful_login(user.id, device_info)
            
            # Reset failed login budget
            self.reset_login_attempt_budget(user.id)

            return True, "Authentication successful"

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, "Authentication failed"

    def log_successful_login(self, user_id: str, device_info: Dict) -> None:
        try:
            user = User.objects.get(id=user_id)
            device_identifier = self.device_service.generate_device_identifier(device_info)
            
            SignInAttempt.objects.create(
                user=user,
                device_identifier=device_identifier,
                successful=True
            )
            
            self.device_service.track_device(device_identifier, user_id)
            
        except Exception as e:
            logger.error(f"Error logging successful login: {str(e)}")

    def log_failed_login(self, credentials: Dict, device_info: Dict) -> None:
        try:
            device_identifier = self.device_service.generate_device_identifier(device_info)
            
            # Try to find the user
            user = None
            if username := credentials.get('username'):
                user = User.objects.filter(username=username).first()

            # Create failed login attempt record
            SignInAttempt.objects.create(
                user=user,
                device_identifier=device_identifier,
                successful=False
            )

            # Update user's failed login budget if user exists
            if user:
                user.remaining_budget_for_failed_logins = max(0, user.remaining_budget_for_failed_logins - 1)
                if user.remaining_budget_for_failed_logins <= 0:
                    user.password_reset_required = True
                user.save()

            self.device_service.track_device(device_identifier, user.id if user else None)

        except Exception as e:
            logger.error(f"Error logging failed login: {str(e)}")

    def check_password_reset_required(self, user_id: str) -> bool:
        try:
            user = User.objects.get(id=user_id)
            return user.password_reset_required
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error checking password reset requirement: {str(e)}")
            return False

    def reset_login_attempt_budget(self, user_id: str) -> None:
        try:
            user = User.objects.get(id=user_id)
            user.remaining_budget_for_failed_logins = DEFAULT_LOGIN_ATTEMPT_BUDGET
            user.password_reset_required = False
            user.save()
        except Exception as e:
            logger.error(f"Error resetting login attempt budget: {str(e)}")
import logging
from typing import Dict, Tuple, Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from random import randrange

from ..interfaces import SignUpServiceInterface
from ..models import SignUpRequest, User, BlacklistedUsername
from .device_service import DeviceService

logger = logging.getLogger(__name__)

class SignUpService(SignUpServiceInterface):
    def __init__(self, device_service: DeviceService):
        self.device_service = device_service

    def _generate_verification_code(self) -> str:
        """Generate a random 6-digit verification code"""
        return str(randrange(100_000, 1_000_000))

    @transaction.atomic
    def create_signup_request(
        self,
        email: str,
        device_info: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        try:
            # Validate device info
            valid, message = self.device_service.validate_device_info(device_info)
            if not valid:
                return False, message, None

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                return False, "Email already registered", None

            # Generate verification code and device identifier
            verification_code = self._generate_verification_code()
            device_identifier = self.device_service.generate_device_identifier(device_info)

            # Create signup request
            SignUpRequest.objects.create(
                device_identifier=device_identifier,
                verification_code=verification_code
            )

            return True, "Verification code sent", verification_code

        except Exception as e:
            logger.error(f"Error creating signup request: {str(e)}")
            return False, "Failed to create signup request", None

    @transaction.atomic
    def verify_signup(self, verification_code: str, email: str) -> Tuple[bool, str]:
        try:
            signup_request = SignUpRequest.objects.filter(
                verification_code=verification_code,
                successful=False
            ).first()

            if not signup_request:
                return False, "Invalid or expired verification code"

            # Mark signup request as successful
            signup_request.successful = True
            signup_request.save()

            return True, "Signup verified successfully"

        except Exception as e:
            logger.error(f"Error verifying signup: {str(e)}")
            return False, "Failed to verify signup"

    def validate_username(self, username: str) -> Tuple[bool, str]:
        try:
            # Check minimum length
            if len(username) < 3:
                return False, "Username must be at least 3 characters long"

            # Check if username is blacklisted
            if BlacklistedUsername.objects.filter(username=username).exists():
                return False, "This username is not allowed"

            # Check if username is already taken
            if User.objects.filter(username=username).exists():
                return False, "Username already taken"

            return True, "Username is valid"

        except Exception as e:
            logger.error(f"Error validating username: {str(e)}")
            return False, "Failed to validate username"
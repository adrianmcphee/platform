import hashlib
import logging
from typing import Dict, Tuple, Optional

from ..interfaces import DeviceServiceInterface
from ..models import SignInAttempt

logger = logging.getLogger(__name__)

class DeviceService(DeviceServiceInterface):
    def generate_device_identifier(self, device_info: Dict) -> str:
        """
        Generate a unique device identifier from device information
        """
        try:
            # Combine relevant device information
            device_string = f"{device_info.get('user_agent', '')}|{device_info.get('ip_address', '')}"
            # Create a hash of the device string
            return hashlib.sha256(device_string.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating device identifier: {str(e)}")
            return hashlib.sha256(str(device_info).encode()).hexdigest()

    def validate_device_info(self, device_info: Dict) -> Tuple[bool, str]:
        """
        Validate required device information is present
        """
        required_fields = ['user_agent', 'ip_address']
        missing_fields = [field for field in required_fields if not device_info.get(field)]
        
        if missing_fields:
            return False, f"Missing required device info: {', '.join(missing_fields)}"
        
        return True, "Device info is valid"

    def track_device(self, device_identifier: str, user_id: Optional[str] = None) -> None:
        """
        Track device usage across sign in attempts
        """
        try:
            # Here we could add additional tracking logic, such as:
            # - Recording device usage patterns
            # - Checking for suspicious activity
            # - Rate limiting by device
            # For now, we just log the tracking
            logger.info(f"Device {device_identifier} tracked for user {user_id or 'anonymous'}")
        except Exception as e:
            logger.error(f"Error tracking device: {str(e)}")
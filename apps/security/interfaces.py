from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional, List
from decimal import Decimal

class UserAuthenticationServiceInterface(ABC):
    @abstractmethod
    def authenticate_user(
        self,
        username: str,
        password: str,
        device_info: Dict
    ) -> Tuple[bool, str]:
        """Authenticate a user login attempt"""
        pass

    @abstractmethod
    def log_successful_login(
        self,
        user_id: str,
        device_info: Dict
    ) -> None:
        """Log a successful login attempt"""
        pass

    @abstractmethod
    def log_failed_login(
        self,
        credentials: Dict,
        device_info: Dict
    ) -> None:
        """Log a failed login attempt"""
        pass

    @abstractmethod
    def check_password_reset_required(
        self,
        user_id: str
    ) -> bool:
        """Check if user needs to reset password"""
        pass

    @abstractmethod
    def reset_login_attempt_budget(
        self,
        user_id: str
    ) -> None:
        """Reset the user's failed login attempt budget"""
        pass

class SignUpServiceInterface(ABC):
    @abstractmethod
    def create_signup_request(
        self,
        email: str,
        device_info: Dict
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new signup request
        Returns (success, message, verification_code if success)
        """
        pass

    @abstractmethod
    def verify_signup(
        self,
        verification_code: str,
        email: str
    ) -> Tuple[bool, str]:
        """Verify a signup request"""
        pass

    @abstractmethod
    def validate_username(
        self,
        username: str
    ) -> Tuple[bool, str]:
        """Check if username is valid and not blacklisted"""
        pass

class AuditServiceInterface(ABC):
    @abstractmethod
    def log_event(
        self,
        user_id: Optional[str],
        action: str,
        content_type: str,
        object_id: int,
        changes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Log an audit event"""
        pass

    @abstractmethod
    def get_audit_trail(
        self,
        content_type: str,
        object_id: int
    ) -> List[Dict]:
        """Get audit trail for an object"""
        pass

class RoleManagementServiceInterface(ABC):
    @abstractmethod
    def assign_product_role(
        self,
        person_id: str,
        product_id: str,
        role: str
    ) -> Tuple[bool, str]:
        """Assign a product role to a person"""
        pass

    @abstractmethod
    def assign_organisation_role(
        self,
        person_id: str,
        organisation_id: str,
        role: str
    ) -> Tuple[bool, str]:
        """Assign an organisation role to a person"""
        pass

    @abstractmethod
    def validate_role_assignment(
        self,
        person_id: str,
        role: str,
        product_id: Optional[str] = None,
        organisation_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Validate a role assignment"""
        pass

    @abstractmethod
    def get_user_roles(
        self,
        person_id: str
    ) -> Dict:
        """Get all roles for a user"""
        pass

class DeviceServiceInterface(ABC):
    @abstractmethod
    def generate_device_identifier(
        self,
        device_info: Dict
    ) -> str:
        """Generate a unique device identifier"""
        pass

    @abstractmethod
    def validate_device_info(
        self,
        device_info: Dict
    ) -> Tuple[bool, str]:
        """Validate device information"""
        pass

    @abstractmethod
    def track_device(
        self,
        device_identifier: str,
        user_id: Optional[str]
    ) -> None:
        """Track device usage"""
        pass
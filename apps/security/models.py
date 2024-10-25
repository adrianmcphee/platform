from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.common.mixins import TimeStampMixin
from apps.common.fields import Base58UUIDv5Field
from apps.talent.models import Person
from apps.security.constants import DEFAULT_LOGIN_ATTEMPT_BUDGET
from apps.security.managers import UserManager


class User(AbstractUser, TimeStampMixin):
    """User model for authentication and identity"""
    id = Base58UUIDv5Field(primary_key=True)
    remaining_budget_for_failed_logins = models.PositiveSmallIntegerField(
        default=DEFAULT_LOGIN_ATTEMPT_BUDGET
    )
    password_reset_required = models.BooleanField(default=False)
    is_test_user = models.BooleanField(_("Test User"), default=False)

    objects = UserManager()

    def __str__(self):
        return self.username


class SignUpRequest(TimeStampMixin):
    """Tracks user registration requests and verification"""
    id = Base58UUIDv5Field(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    device_identifier = models.CharField(max_length=64, null=True, blank=True)
    verification_code = models.CharField(max_length=6)
    successful = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user} - {self.successful}"


class SignInAttempt(TimeStampMixin):
    """Records of login attempts, both successful and failed"""
    id = Base58UUIDv5Field(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    device_identifier = models.CharField(max_length=64, null=True, blank=True)
    successful = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user if self.user else 'Unknown User'} - {'Successful' if self.successful else 'Failed'}"


class AuditEvent(TimeStampMixin):
    """Audit trail for system events and changes"""
    ACTION_CHOICES = (
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )

    id = Base58UUIDv5Field(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField(max_length=6, choices=ACTION_CHOICES)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    changes = models.TextField(null=True)

    def __str__(self):
        return f"{self.action} on {self.content_object} by {self.user or 'system'}"


class ProductRoleAssignment(TimeStampMixin):
    """Product-specific role assignments for users"""
    class ProductRoles(models.TextChoices):
        MEMBER = "Member", "Member"
        MANAGER = "Manager", "Manager"
        ADMIN = "Admin", "Admin"

    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    product = models.ForeignKey(
        'product_management.Product',
        on_delete=models.CASCADE
    )
    role = models.CharField(
        max_length=255,
        choices=ProductRoles.choices,
        default=ProductRoles.MEMBER,
    )

    def __str__(self):
        return f"{self.person} - {self.role}"


class BlacklistedUsername(TimeStampMixin):
    """Usernames that are not allowed to be used"""
    id = Base58UUIDv5Field(primary_key=True)
    username = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = "black_listed_usernames"


class OrganisationPersonRoleAssignment(TimeStampMixin):
    """Organisation-specific role assignments for users"""
    class OrganisationRoles(models.TextChoices):
        OWNER = "Owner", "Owner"
        MANAGER = "Manager", "Manager"
        MEMBER = "Member", "Member"

    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey(
        "talent.Person",
        on_delete=models.CASCADE
    )
    organisation = models.ForeignKey(
        "commerce.Organisation",
        on_delete=models.CASCADE
    )
    role = models.CharField(
        max_length=255,
        choices=OrganisationRoles.choices,
        default=OrganisationRoles.MEMBER,
    )

    class Meta:
        unique_together = ("person", "organisation")

    def __str__(self):
        return f"{self.person} - {self.organisation} - {self.role}"
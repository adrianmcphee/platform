import os
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.common.fields import Base58UUIDv5Field
from apps.common.models import AttachmentAbstract, TreeNode
from apps.common.mixins import TimeStampMixin

class Person(TimeStampMixin):
    class PersonStatus(models.TextChoices):
        DRONE = "Drone"
        HONEYBEE = "Honeybee"
        TRUSTED_BEE = "Trusted Bee"
        QUEEN_BEE = "Queen Bee"
        BEEKEEPER = "Beekeeper"

    id = Base58UUIDv5Field(primary_key=True)
    full_name = models.CharField(max_length=256)
    preferred_name = models.CharField(max_length=128)
    user = models.OneToOneField("security.User", on_delete=models.CASCADE, related_name="person")
    products = GenericRelation("product_management.Product")
    photo = models.ImageField(upload_to=settings.PERSON_PHOTO_UPLOAD_TO, null=True, blank=True)
    headline = models.TextField()
    overview = models.TextField(blank=True)
    location = models.TextField(max_length=128, null=True, blank=True)
    send_me_bounties = models.BooleanField(default=True)
    current_position = models.CharField(max_length=256, null=True, blank=True)
    twitter_link = models.URLField(null=True, blank=True, default="")
    linkedin_link = models.URLField(null=True, blank=True)
    github_link = models.URLField(null=True, blank=True)
    website_link = models.URLField(null=True, blank=True)
    completed_profile = models.BooleanField(default=False)
    points = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "talent_person"
        verbose_name_plural = "People"

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("portfolio", args=(self.user.username,))

    def get_photo_url(self):
        return self.photo.url if self.photo else f"{settings.STATIC_URL}images/profile-empty.png"

class PersonSkill(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey(Person, related_name="skills", on_delete=models.CASCADE)
    skill = models.ForeignKey("talent.Skill", on_delete=models.CASCADE)
    expertise = models.ManyToManyField("talent.Expertise")

    def __str__(self):
        return f"{self.person} - {self.skill}"

class Skill(TreeNode):
    active = models.BooleanField(default=False, db_index=True)
    selectable = models.BooleanField(default=False)
    display_boost_factor = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.name

class Expertise(TreeNode):
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="skill_expertise",
    )
    selectable = models.BooleanField(default=False)
    fa_icon = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BountyBid(TimeStampMixin):
    class Status(models.TextChoices):
        PENDING = "Pending"
        ACCEPTED = "Accepted"
        REJECTED = "Rejected"
        WITHDRAWN = "Withdrawn"

    id = Base58UUIDv5Field(primary_key=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE, related_name="bids")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="bounty_bids")
    amount_in_usd_cents = models.IntegerField(null=True, blank=True, default=None)
    amount_in_points = models.IntegerField(null=True, blank=True, default=None)
    expected_finish_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    message = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("bounty", "person")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Bid for {self.bounty.title} by {self.person}"

class BountyClaim(TimeStampMixin):
    class Status(models.TextChoices):
        ACTIVE = "Active"
        COMPLETED = "Completed"
        FAILED = "Failed"

    id = Base58UUIDv5Field(primary_key=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    accepted_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        unique_together = ("bounty", "person")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Claim on {self.bounty.title} by {self.person}"

class BountyDeliveryAttempt(TimeStampMixin, AttachmentAbstract):
    class Status(models.TextChoices):
        NEW = "New"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    bounty_claim = models.ForeignKey(
        BountyClaim,
        on_delete=models.CASCADE,
        related_name="delivery_attempts",
    )
    delivery_message = models.CharField(max_length=2000)
    review_message = models.CharField(max_length=2000, null=True, blank=True)
    reviewed_by = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_deliveries")

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.bounty_claim.person} - {self.status}"

class Feedback(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    recipient = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="feedback_recipient")
    provider = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="feedback_provider")
    message = models.TextField()
    stars = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    def __str__(self):
        return f"{self.recipient} - {self.provider} - {self.stars}"
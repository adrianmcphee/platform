from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.common.fields import Base58UUIDv5Field
from apps.common.models import AttachmentAbstract, TreeNode
from apps.common.mixins import TimeStampMixin
from apps.talent.models import Skill, Expertise
from apps.commerce.interfaces import BountyPurchaseInterface

class FileAttachment(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    file = models.FileField(upload_to="attachments")

    def __str__(self):
        return f"{self.file.name}"

class Product(TimeStampMixin, AttachmentAbstract):
    class Visibility(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        ORG_ONLY = "ORG_ONLY", "Organisation Only"
        RESTRICTED = "RESTRICTED", "Restricted"

    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE, null=True, blank=True)
    organisation = models.ForeignKey("commerce.Organisation", on_delete=models.SET_NULL, null=True, blank=True)
    photo = models.ImageField(upload_to="products/", blank=True, null=True)
    name = models.TextField()
    short_description = models.TextField()
    full_description = models.TextField()
    website = models.CharField(max_length=512, blank=True, null=True)
    detail_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    slug = models.SlugField(unique=True)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.ORG_ONLY
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=(self.slug,))

class ProductTree(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    product = models.ForeignKey(Product, related_name="product_trees", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

class ProductArea(AttachmentAbstract, TreeNode, TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1000, blank=True, null=True, default="")
    video_link = models.URLField(max_length=255, blank=True, null=True)
    video_name = models.CharField(max_length=255, blank=True, null=True)
    video_duration = models.CharField(max_length=255, blank=True, null=True)
    product_tree = models.ForeignKey(ProductTree, blank=True, null=True, related_name="product_areas", on_delete=models.SET_NULL)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return self.name

class Initiative(TimeStampMixin):
    class InitiativeStatus(models.TextChoices):
        DRAFT = "Draft"
        ACTIVE = "Active"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)  
    name = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=255,
        choices=InitiativeStatus.choices,
        default=InitiativeStatus.ACTIVE
    )
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Challenge(TimeStampMixin, AttachmentAbstract):
    class ChallengeStatus(models.TextChoices):
        DRAFT = "Draft"
        BLOCKED = "Blocked"
        ACTIVE = "Active"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

    class ChallengePriority(models.TextChoices):
        HIGH = "High"
        MEDIUM = "Medium"
        LOW = "Low"

    id = Base58UUIDv5Field(primary_key=True)
    initiative = models.ForeignKey(Initiative, on_delete=models.SET_NULL, blank=True, null=True)
    product_area = models.ForeignKey(ProductArea, on_delete=models.SET_NULL, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    title = models.TextField()
    description = models.TextField()
    short_description = models.TextField(max_length=256)
    status = models.CharField(
        max_length=255,
        choices=ChallengeStatus.choices,
        default=ChallengeStatus.DRAFT
    )
    blocked = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=50,
        choices=ChallengePriority.choices,
        default=ChallengePriority.HIGH
    )
    auto_approve_bounty_claims = models.BooleanField(default=False)
    video_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Challenges"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("challenge_detail", kwargs={"product_slug": self.product.slug, "pk": self.pk})

class Bounty(AttachmentAbstract, TimeStampMixin, models.Model, BountyPurchaseInterface):
    class BountyStatus(models.TextChoices):
        FUNDED = "Funded", "Funded"
        OPEN = "Open", "Open"
        CLAIMED = "Claimed", "Claimed"
        COMPLETED = "Completed", "Completed"
        CANCELLED = "Cancelled", "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='bounties')
    challenge = models.ForeignKey('Challenge', on_delete=models.SET_NULL, null=True, blank=True, related_name='bounties')
    competition = models.OneToOneField('Competition', on_delete=models.SET_NULL, null=True, blank=True, related_name='bounty')
    title = models.CharField(max_length=400)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=BountyStatus.choices,
        default=BountyStatus.FUNDED
    )
    reward_type = models.CharField(max_length=10, choices=[('USD', 'USD'), ('Points', 'Points')])
    reward_in_usd_cents = models.IntegerField(null=True, blank=True)
    reward_in_points = models.IntegerField(null=True, blank=True)
    final_reward_in_usd_cents = models.IntegerField(null=True, blank=True)
    final_reward_in_points = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Bounties"

    def __str__(self):
        return self.title

    def clean(self):
        if self.reward_type == 'USD' and self.reward_in_points is not None:
            raise ValidationError("For USD rewards, reward_in_points should be None")
        if self.reward_type == 'Points' and self.reward_in_usd_cents is not None:
            raise ValidationError("For Points rewards, reward_in_usd_cents should be None")
        if self.challenge is None and self.competition is None:
            raise ValidationError("Bounty must be associated with either a Challenge or a Competition")
        if self.challenge is not None and self.competition is not None:
            raise ValidationError("Bounty cannot be associated with both a Challenge and a Competition")

    # Implement BountyPurchaseInterface methods
    @property
    def purchase_status(self) -> str:
        """Maps the model status to purchase status"""
        return self.status

class Competition(TimeStampMixin, AttachmentAbstract):
    class CompetitionStatus(models.TextChoices):
        DRAFT = "Draft"
        ACTIVE = "Active"
        ENTRIES_CLOSED = "Entries Closed"
        JUDGING = "Judging"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    product_area = models.ForeignKey(ProductArea, on_delete=models.SET_NULL, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    short_description = models.CharField(max_length=256)
    status = models.CharField(
        max_length=20,
        choices=CompetitionStatus.choices,
        default=CompetitionStatus.DRAFT
    )
    entry_deadline = models.DateTimeField()
    judging_deadline = models.DateTimeField()
    max_entries = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("competition_detail", kwargs={"product_slug": self.product.slug, "pk": self.pk})

class CompetitionEntry(TimeStampMixin):
    class EntryStatus(models.TextChoices):
        SUBMITTED = "Submitted"
        FINALIST = "Finalist"
        WINNER = "Winner"
        REJECTED = "Rejected"

    id = Base58UUIDv5Field(primary_key=True)
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="entries")
    submitter = models.ForeignKey("talent.Person", on_delete=models.CASCADE, related_name="competition_entries")
    content = models.TextField()
    entry_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=EntryStatus.choices,
        default=EntryStatus.SUBMITTED
    )

    def __str__(self):
        return f"Entry for {self.competition.title} by {self.submitter}"

class CompetitionEntryRating(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    entry = models.ForeignKey(CompetitionEntry, on_delete=models.CASCADE, related_name="ratings")
    rater = models.ForeignKey("talent.Person", on_delete=models.CASCADE, related_name="given_ratings")
    rating = models.PositiveSmallIntegerField(help_text="Rating from 1 to 5")
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("entry", "rater")

    def __str__(self):
        return f"Rating for {self.entry} by {self.rater}"

class Idea(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    title = models.CharField(max_length=256)
    description = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.person} - {self.title}"

class Bug(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    title = models.CharField(max_length=256)
    description = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.person} - {self.title}"

class BountySkill(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    bounty = models.ForeignKey(Bounty, related_name="skills", on_delete=models.CASCADE)
    skill = models.ForeignKey("talent.Skill", on_delete=models.CASCADE)
    expertise = models.ManyToManyField("talent.Expertise", blank=True)

    def __str__(self):
        return f"{self.bounty.title} - {self.skill}"

class ContributorGuide(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_contributor_guide")
    title = models.CharField(max_length=60, unique=True)
    description = models.TextField(null=True, blank=True)
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="skill_contributor_guide",
        blank=True,
        null=True,
        default=None
    )

    def __str__(self):
        return self.title

class ProductContributorAgreementTemplate(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey(Product, related_name="contributor_agreement_templates", on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    content = models.TextField()
    effective_date = models.DateField()

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} ({self.product})"

class ProductContributorAgreement(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    agreement_template = models.ForeignKey(ProductContributorAgreementTemplate, on_delete=models.CASCADE)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE, related_name="contributor_agreement")
    accepted_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.person} - {self.agreement_template.title}"

class IdeaVote(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    voter = models.ForeignKey("talent.Person", on_delete=models.CASCADE)
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("voter", "idea")

    def __str__(self):
        return f"{self.voter} - {self.idea}"

class ChallengeDependency(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    preceding_challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    subsequent_challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="Challenge")

    class Meta:
        db_table = "product_management_challenge_dependencies"

    def __str__(self):
        return f"{self.preceding_challenge.title} -> {self.subsequent_challenge.title}"


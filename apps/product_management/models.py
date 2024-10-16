from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.text import slugify
from django.apps import apps
from django.utils import timezone

from model_utils import FieldTracker

from apps.common import models as common
from apps.common.mixins import TimeStampMixin
from apps.common.fields import Base58UUIDv5Field

from django.core.exceptions import ValidationError

from django.db.models import Sum

from apps.talent.models import Skill, Expertise


class FileAttachment(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    file = models.FileField(upload_to="attachments")

    def __str__(self):
        return f"{self.file.name}"


class ProductTree(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    product = models.ForeignKey(
        "product_management.Product",
        related_name="product_trees",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name


class ProductArea(common.AttachmentAbstract, common.TreeNode, TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1000, blank=True, null=True, default="")
    video_link = models.URLField(max_length=255, blank=True, null=True)
    video_name = models.CharField(max_length=255, blank=True, null=True)
    video_duration = models.CharField(max_length=255, blank=True, null=True)
    product_tree = models.ForeignKey(
        "product_management.ProductTree",
        blank=True,
        null=True,
        related_name="product_areas",
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['path']


class Product(TimeStampMixin, common.AttachmentAbstract):
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
    is_private = models.BooleanField(default=False)

    def get_owner(self):
        if self.organisation:
            return self.organisation
        return self.person

    def get_initials_of_name(self):
        return "".join([word[0] for word in self.name.split()])

    def get_absolute_url(self):
        return reverse("product_detail", args=(self.slug,))

    def __str__(self):
        return self.name

    def make_private(self):
        self.is_private = True
        self.save()

    def make_public(self):
        self.is_private = False
        self.save()

    def capability_start(self):
        return self.product_trees.first()

    def get_photo_url(self):
        return self.photo.url if self.photo else f"{settings.STATIC_URL}images/product-empty.png"

    @staticmethod
    def check_slug_from_name(product_name: str):
        """Checks if the given product name already exists. If so, it returns an error message."""
        slug = slugify(product_name)

        if Product.objects.filter(slug=slug):
            return f"The name {product_name} is not available currently. Please pick something different."

    def __str__(self):
        return self.name

    def ensure_point_account(self):
        ProductPointAccount = apps.get_model('commerce', 'ProductPointAccount')
        ProductPointAccount.objects.get_or_create(product=self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.ensure_point_account()

    @property
    def point_account(self):
        return self.product_point_account

    @property
    def point_balance(self):
        try:
            return self.product_point_account.balance
        except AttributeError:
            return 0

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
        default=InitiativeStatus.ACTIVE,
    )
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # TODO: move the below method to a utility class
        from .services import ProductService

        self.video_url = ProductService.convert_youtube_link_to_embed(self.video_url)
        super(Initiative, self).save(*args, **kwargs)

    def get_available_challenges_count(self):
        return self.challenge_set.filter(status=Challenge.ChallengeStatus.ACTIVE).count()

    def get_completed_challenges_count(self):
        return self.challenge_set.filter(status=Challenge.ChallengeStatus.COMPLETED).count()

    def get_challenge_tags(self):
        return Challenge.objects.filter(task_tags__initiative=self).distinct("id").all()

    @staticmethod
    def get_filtered_data(input_data, filter_data=None, exclude_data=None):
        if filter_data is None:
            filter_data = {}
        if not filter_data:
            filter_data = dict()

        if not input_data:
            input_data = dict()

        statuses = input_data.get("statuses", [])
        tags = input_data.get("tags", [])
        categories = input_data.get("categories", None)

        if statuses:
            filter_data["status__in"] = statuses

        if tags:
            filter_data["challenge__tag__in"] = tags

        if categories:
            filter_data["challenge__category__parent__in"] = categories

        queryset = Initiative.objects.filter(**filter_data)
        if exclude_data:
            queryset = queryset.exclude(**exclude_data)

        return queryset.distinct("id").all()


class Challenge(TimeStampMixin, common.AttachmentAbstract):
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
    title = models.TextField()
    description = models.TextField()
    short_description = models.TextField(max_length=256)
    status = models.CharField(
        max_length=255,
        choices=ChallengeStatus.choices,
        default=ChallengeStatus.DRAFT,
    )
    blocked = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=50,
        choices=ChallengePriority.choices,
        default=ChallengePriority.HIGH,
    )
    auto_approve_bounty_claims = models.BooleanField(default=False)
    tracker = FieldTracker()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    video_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Challenges"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("challenge_detail", kwargs={"product_slug": self.product.slug, "pk": self.pk})

    def get_total_reward(self):
        return sum(bounty.reward_in_usd_cents or 0 for bounty in self.bounties.all())

    def can_delete_challenge(self, person):
        from apps.security.models import ProductRoleAssignment

        product = self.product
        # That should not happen because every challenge should have a product.
        # We could remove null=True statement from the product field and this
        # if statement to prevent having challenges without a product.
        if product is None:
            return False

        try:
            product_role_assignment = ProductRoleAssignment.objects.get(person=person, product=product)

            if product_role_assignment.role == ProductRoleAssignment.ProductRoles.CONTRIBUTOR:
                return False

        except ProductRoleAssignment.DoesNotExist:
            return False

        return True

    def has_bounty(self):
        return self.bounties.count() > 0

    def get_bounty_points(self):
        total = 0
        queryset = self.bounties.all()
        for elem in queryset:
            total += elem.points

        return total

    @staticmethod
    def get_filtered_data(input_data, filter_data=None, exclude_data=None):
        if not filter_data:
            filter_data = {}

        if not input_data:
            input_data = {}

        sorted_by = input_data.get("sorted_by", "title")
        statuses = input_data.get("statuses", [])
        tags = input_data.get("tags", [])
        priority = input_data.get("priority", [])
        assignee = input_data.get("assignee", [])
        task_creator = input_data.get("task_creator", [])
        skills = input_data.get("skils", [])

        if statuses:
            filter_data["status__in"] = statuses

        if tags:
            filter_data["tag__in"] = tags

        if priority:
            filter_data["priority__in"] = priority

        if assignee:
            filter_data["bountyclaim__status__in"] = [0, 1]
            filter_data["bountyclaim__person_id__in"] = assignee

        if skills:
            filter_data["skill__parent__in"] = skills

        queryset = Challenge.objects.filter(**filter_data)
        if exclude_data:
            queryset = queryset.exclude(**exclude_data)

        return queryset.order_by(sorted_by).all()

    def get_short_description(self):
        # return a shortened version of the description text
        MAX_LEN = 90
        if len(self.description) > MAX_LEN:
            return f"{self.description[0:MAX_LEN]}..."

        return self.description

    def update_status(self):
        if all(bounty.status == Bounty.BountyStatus.COMPLETED for bounty in self.bounties.all()):
            self.status = self.ChallengeStatus.COMPLETED
            self.save()

    @property
    def total_bounties(self):
        return self.bounties.count()


class Competition(TimeStampMixin, common.AttachmentAbstract):
    class CompetitionStatus(models.TextChoices):
        DRAFT = "Draft"
        ACTIVE = "Active"
        ENTRIES_CLOSED = "Entries Closed"
        JUDGING = "Judging"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    product_area = models.ForeignKey("ProductArea", on_delete=models.SET_NULL, blank=True, null=True)
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    short_description = models.CharField(max_length=256)
    status = models.CharField(max_length=20, choices=CompetitionStatus.choices, default=CompetitionStatus.DRAFT)
    entry_deadline = models.DateTimeField()
    judging_deadline = models.DateTimeField()
    max_entries = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("competition_detail", kwargs={"product_slug": self.product.slug, "pk": self.pk})

    def get_total_reward(self):
        return self.bounty_set.aggregate(Sum("reward_amount"))["reward_amount__sum"] or 0

    def update_status(self):
        now = timezone.now()
        new_status = self.status
        if now >= self.entry_deadline and self.status == self.CompetitionStatus.ACTIVE:
            new_status = self.CompetitionStatus.ENTRIES_CLOSED
        elif now >= self.judging_deadline and self.status == self.CompetitionStatus.ENTRIES_CLOSED:
            new_status = self.CompetitionStatus.JUDGING
        
        if new_status != self.status:
            self.status = new_status
            self.save(update_fields=['status'])

    @property
    def has_bounty(self):
        return hasattr(self, 'bounty')

    def get_bounty(self):
        return self.bounty if self.has_bounty else None


class Bounty(TimeStampMixin, common.AttachmentAbstract):
    class BountyStatus(models.TextChoices):
        DRAFT = "Draft"
        OPEN = "Open"
        IN_PROGRESS = "In Progress"
        IN_REVIEW = "In Review"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='bounties')  # Restored association
    challenge = models.ForeignKey('Challenge', on_delete=models.SET_NULL, null=True, blank=True, related_name='bounties')
    competition = models.OneToOneField('Competition', on_delete=models.SET_NULL, null=True, blank=True, related_name='bounty')
    title = models.CharField(max_length=400)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=BountyStatus.choices,
        default=BountyStatus.DRAFT,
    )
    reward_type = models.CharField(max_length=10, choices=[('USD', 'USD'), ('Points', 'Points')])
    reward_in_usd_cents = models.IntegerField(null=True, blank=True)
    reward_in_points = models.IntegerField(null=True, blank=True)
    final_reward_in_usd_cents = models.IntegerField(null=True, blank=True)
    final_reward_in_points = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Bounties"
        
    def clean(self):
        if self.reward_type == 'USD' and self.reward_in_points is not None:
            raise ValidationError("For USD rewards, reward_in_points should be None")
        if self.reward_type == 'Points' and self.reward_in_usd_cents is not None:
            raise ValidationError("For Points rewards, reward_in_usd_cents should be None")
        if self.reward_type == 'USD' and self.final_reward_in_points is not None:
            raise ValidationError("For USD rewards, final_reward_in_points should be None")
        if self.reward_type == 'Points' and self.final_reward_in_usd_cents is not None:
            raise ValidationError("For Points rewards, final_reward_in_usd_cents should be None")
        if self.is_part_of_challenge and self.is_part_of_competition:
            raise ValidationError("A Bounty cannot be part of both a Challenge and a Competition.")

    @property
    def has_claimed(self):
        return self.status in [
            self.BountyStatus.COMPLETED,
            self.BountyStatus.IN_REVIEW,
            self.BountyStatus.CLAIMED,
        ]

    def get_reward_display(self):
        if self.reward_type == 'USD':
            return f"{self.reward_in_usd_cents/100:.2f} USD"
        else:
            return f"{self.reward_in_points} Points"

    def get_expertise_as_str(self):
        return ", ".join([exp.name.title() for exp in self.expertise.all()])

    def __str__(self):
        reward = f"{self.reward_in_usd_cents/100:.2f} USD" if self.reward_type == 'USD' else f"{self.reward_in_points} Points"
        return f"{self.title} - {reward}"

    def clean(self):
        super().clean()
        if (self.challenge is None) == (self.competition is None):
            raise ValidationError("Bounty must be associated with either a Challenge or a Competition, but not both.")

    def update_status_from_claim(self):
        from apps.talent.models import BountyClaim  # Import here to avoid circular imports

        latest_claim = BountyClaim.objects.filter(bounty=self).order_by("-created_at").first()

        if not latest_claim:
            new_status = self.BountyStatus.OPEN
        elif latest_claim.status == BountyClaim.Status.ACTIVE:
            new_status = self.BountyStatus.IN_PROGRESS
        elif latest_claim.status == BountyClaim.Status.COMPLETED:
            new_status = self.BountyStatus.COMPLETED
        elif latest_claim.status == BountyClaim.Status.FAILED:
            new_status = self.BountyStatus.OPEN
        else:
            return  # No status change needed

        if self.status != new_status:
            self.status = new_status
            self.save()

    @property
    def is_part_of_challenge(self):
        return self.challenge is not None

    @property
    def is_part_of_competition(self):
        return self.competition is not None


class BountySkill(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    bounty = models.ForeignKey(Bounty, related_name="skills", on_delete=models.CASCADE)
    skill = models.ForeignKey("talent.Skill", on_delete=models.CASCADE)
    expertise = models.ManyToManyField("talent.Expertise", blank=True)

    def __str__(self):
        expertises = ", ".join(self.expertise.values_list('name', flat=True))
        return f"{self.bounty.title} - {self.skill} - Expertises: {expertises or 'None'}"

    def clean(self):
        super().clean()
        if self.expertise.exists():
            valid_expertises = Expertise.objects.filter(skill=self.skill)
            invalid_expertises = self.expertise.exclude(id__in=valid_expertises)
            if invalid_expertises.exists():
                raise ValidationError("Some expertises do not belong to the selected skill.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


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
    status = models.CharField(max_length=20, choices=EntryStatus.choices, default=EntryStatus.SUBMITTED)

    def __str__(self):
        return f"Entry for {self.competition.title} by {self.submitter.full_name}"

    def can_user_rate(self, user):
        from apps.security.models import ProductRoleAssignment

        is_admin_or_judge = ProductRoleAssignment.objects.filter(
            person=user.person,
            product=self.competition.product,
            role__in=[ProductRoleAssignment.ProductRoles.ADMIN, ProductRoleAssignment.ProductRoles.JUDGE],
        ).exists()
        has_rated = self.ratings.filter(rater=user.person).exists()
        return is_admin_or_judge and not has_rated


class CompetitionEntryRating(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    entry = models.ForeignKey(CompetitionEntry, on_delete=models.CASCADE, related_name="ratings")
    rater = models.ForeignKey("talent.Person", on_delete=models.CASCADE, related_name="given_ratings")
    rating = models.PositiveSmallIntegerField(help_text="Rating from 1 to 5")
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"Rating for {self.entry} by {self.rater.full_name}"  # Change 'name' to 'full_name'

    class Meta:
        unique_together = ("entry", "rater")


class ChallengeDependency(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    preceding_challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE)
    subsequent_challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE, related_name="Challenge")

    class Meta:
        db_table = "product_management_challenge_dependencies"


class ContributorGuide(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey(
        to=Product,
        on_delete=models.CASCADE,
        related_name="product_contributor_guide",
    )
    title = models.CharField(max_length=60, unique=True)
    description = models.TextField(null=True, blank=True)
    skill = models.ForeignKey(
        "talent.Skill",
        on_delete=models.CASCADE,
        related_name="skill_contributor_guide",
        blank=True,
        null=True,
        default=None,
    )

    def __str__(self):
        return self.title


class Idea(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    title = models.CharField(max_length=256)
    description = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse("add_product_idea", kwargs={"pk": self.pk})

    def __str__(self):
        return f"{self.person} - {self.title}"


class Bug(TimeStampMixin,models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    title = models.CharField(max_length=256)
    description = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse("add_product_bug", kwargs={"product_slug": self.product.slug})

    def __str__(self):
        return f"{self.person} - {self.title}"


class ProductContributorAgreementTemplate(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey(
        "product_management.Product",
        related_name="contributor_agreement_templates",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=256)
    content = models.TextField()
    effective_date = models.DateField()

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} ({self.product})"


class IdeaVote(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    voter = models.ForeignKey("talent.Person", on_delete=models.CASCADE)
    idea = models.ForeignKey(Idea, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("voter", "idea")


class ProductContributorAgreement(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    agreement_template = models.ForeignKey(to=ProductContributorAgreementTemplate, on_delete=models.CASCADE)
    person = models.ForeignKey(
        to="talent.Person",
        on_delete=models.CASCADE,
        related_name="contributor_agreement",
    )
    accepted_at = models.DateTimeField(auto_now_add=True, null=True)


# Signal receivers
@receiver(post_save, sender=Bounty)
def update_challenge_status(sender, instance, **kwargs):
    if instance.challenge:
        instance.challenge.update_status()


@receiver(post_save, sender="talent.BountyClaim")
def update_bounty_status_from_claim(sender, instance, **kwargs):
    instance.bounty.update_status_from_claim()


@receiver(post_save, sender="talent.BountyBid")
def update_bounty_status_from_bid(sender, instance, **kwargs):
    if instance.status == "ACCEPTED":
        if instance.bounty.status != Bounty.BountyStatus.IN_PROGRESS:
            instance.bounty.status = Bounty.BountyStatus.IN_PROGRESS
            instance.bounty.save()


@receiver(pre_save, sender="product_management.Product")
def _pre_save(sender, instance, **kwargs):
    from .services import ProductService

    instance.video_url = ProductService.convert_youtube_link_to_embed(instance.video_url)


@receiver(post_save, sender="product_management.Competition")
def update_competition_status(sender, instance, **kwargs):
    instance.update_status()
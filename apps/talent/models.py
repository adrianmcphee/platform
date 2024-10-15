import os
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from treebeard.mp_tree import MP_Node

from apps.common.fields import Base58UUIDv5Field
from apps.common.models import AttachmentAbstract
from django.apps import apps
from apps.common.mixins import AncestryMixin, TimeStampMixin
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist


class Person(TimeStampMixin):
    class PersonStatus(models.TextChoices):
        DRONE = "Drone"
        HONEYBEE = "Honeybee"
        TRUSTED_BEE = "Trusted Bee"
        QUEEN_BEE = "Queen Bee"
        BEEKEEPER = "Beekeeper"

    STATUS_POINT_MAPPING = {
        PersonStatus.DRONE: 0,
        PersonStatus.HONEYBEE: 50,
        PersonStatus.TRUSTED_BEE: 500,
        PersonStatus.QUEEN_BEE: 2000,
        PersonStatus.BEEKEEPER: 8000,
    }

    STATUS_PRIVILEGES_MAPPING = {
        PersonStatus.DRONE: _("Earn points by completing bounties, submitting Ideas & Bugs"),
        PersonStatus.HONEYBEE: _("Earn payment for payment-eligible bounties on openunited.com"),
        PersonStatus.TRUSTED_BEE: _("Early Access to claim top tasks"),
        PersonStatus.QUEEN_BEE: _("A grant of 1000 points for your own open product on OpenUnited"),
        PersonStatus.BEEKEEPER: _("Invite new products to openunited.com and grant points"),
    }
    
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

    @property
    def points_status(self):
        return self.get_points_status()

    def get_points_privileges(self):
        return self.STATUS_PRIVILEGES_MAPPING.get(self.get_points_status())

    def add_points(self, points):
        self.points += points
        self.save()

    def get_points_status(self):
        for status in reversed(self.STATUS_POINT_MAPPING.keys()):
            current_points = self.STATUS_POINT_MAPPING.get(status)
            if current_points <= self.points:
                return status
        return self.PersonStatus.DRONE

    def get_display_points(self):
        status = self.get_points_status()
        statuses = list(self.STATUS_POINT_MAPPING.keys())
        # if `status` is the last one in `statuses`
        if status == statuses[-1]:
            return f">= {self.STATUS_POINT_MAPPING.get(status)}"
        # +1 is to get the next status
        index = statuses.index(status) + 1
        return f"< {self.STATUS_POINT_MAPPING.get(statuses[index])}"

    def get_initial_data(self):
        initial = {
            "full_name": self.full_name,
            "preferred_name": self.preferred_name,
            "headline": self.headline,
            "overview": self.overview,
            "github_link": self.github_link,
            "twitter_link": self.twitter_link,
            "linkedin_link": self.linkedin_link,
            "website_link": self.website_link,
            "send_me_bounties": self.send_me_bounties,
            "current_position": self.current_position,
            "location": self.location,
        }
        return initial

    def get_username(self):
        return self.user.username if self.user else ""

    def get_photo_url(self):
        return self.photo.url if self.photo else f"{settings.STATIC_URL}images/profile-empty.png"

    def get_products(self):
        return self.products.all()

    def get_absolute_url(self):
        return reverse("portfolio", args=(self.user.username,))

    def delete_photo(self) -> None:
        path = self.photo.path
        if os.path.exists(path):
            os.remove(path)

        self.photo.delete(save=True)

    def toggle_bounties(self):
        self.send_me_bounties = not self.send_me_bounties
        self.save()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.preferred_name

    def __str__(self):
        return self.full_name


class PersonSkill(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey(Person, related_name="skills", on_delete=models.CASCADE)
    skill = models.ForeignKey("talent.Skill", on_delete=models.CASCADE)
    expertise = models.ManyToManyField("talent.Expertise")

    def __str__(self):
        return f"{self.person} - {self.skill} - {self.expertise}"


class Skill(AncestryMixin):
    id = Base58UUIDv5Field(primary_key=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="children",
    )
    active = models.BooleanField(default=False, db_index=True)
    selectable = models.BooleanField(default=False)
    display_boost_factor = models.PositiveSmallIntegerField(default=1)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    @property
    def get_children(self):
        return self.children.filter(active=True)

    @classmethod
    def get_roots(cls):
        return cls.objects.filter(parent=None, active=True)

    @staticmethod
    def get_active_skills(active=True, parent=None):
        return Skill.objects.filter(active=active, parent=parent).all()

    @staticmethod
    def get_active_skill_list(active=True):
        return Skill.objects.filter(active=active, parent=None).values("id", "name")


class Expertise(AncestryMixin):
    id = Base58UUIDv5Field(primary_key=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
        related_name="expertise_children",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="skill_expertise",
    )
    selectable = models.BooleanField(default=False)
    name = models.CharField(max_length=100)
    fa_icon = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    @classmethod
    def get_roots(cls):
        return cls.objects.filter(parent=None)

    @property
    def get_children(self):
        return self.expertise_children.filter()

    @staticmethod
    def get_skill_expertise(skill):
        return Expertise.objects.filter(skill=skill).values("id", "name")

    @staticmethod
    def get_all_expertise(parent=None):
        return Expertise.objects.filter(parent=parent).all()

    @staticmethod
    def get_all_expertise_list():
        return Expertise.objects.filter(parent=None).values("id", "name")


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

    def clean(self):
        if self.bounty.reward_type == 'USD' and self.amount_in_usd_cents is None:
            raise ValidationError("For USD bounties, amount_in_usd_cents is required")
        if self.bounty.reward_type == 'Points' and self.amount_in_points is None:
            raise ValidationError("For Points bounties, amount_in_points is required")

    def __str__(self):
        if self.bounty.reward_type == 'USD':
            amount = f"{self.amount_in_usd_cents/100:.2f} USD" if self.amount_in_usd_cents is not None else "N/A USD"
        else:
            amount = f"{self.amount_in_points} Points" if self.amount_in_points is not None else "N/A Points"
        return f"Bid for {self.bounty.title} - {amount}"

    @transaction.atomic
    def accept_bid(self):
        if self.status != self.Status.PENDING:
            raise ValidationError("Only pending bids can be accepted.")
        
        self.status = self.Status.ACCEPTED
        self.save()
        
        # Create a BountyClaim if it doesn't already exist
        BountyClaim.objects.get_or_create(
            bounty=self.bounty,
            person=self.person,
            defaults={'accepted_bid': self}
        )
        
        # Update the Bounty
        if self.bounty.reward_type == 'USD':
            self.bounty.final_reward_in_usd_cents = self.amount_in_usd_cents
        else:
            self.bounty.final_reward_in_points = self.amount_in_points
        self.bounty.status = self.bounty.BountyStatus.IN_PROGRESS
        self.bounty.save()
        
        # Process the reward adjustment
        self._process_reward_adjustment()

    def _process_reward_adjustment(self):
        from apps.commerce.models import SalesOrder
        try:
            original_order = SalesOrder.objects.get(cart__items__bounty=self.bounty, adjustment_type="INITIAL")
            if self.bounty.reward_type == 'USD':
                difference = self.amount_in_usd_cents - self.bounty.reward_in_usd_cents
            else:
                difference = self.amount_in_points - self.bounty.reward_in_points
            if difference > 0:
                self._create_increase_adjustment(original_order, difference)
            elif difference < 0:
                self._create_decrease_adjustment(original_order, abs(difference))
        except SalesOrder.DoesNotExist:
            # Handle the case where there's no original order (e.g., for point-based bounties)
            pass
    
    @transaction.atomic
    def _create_increase_adjustment(self, original_order, amount):
        Cart = apps.get_model('commerce', 'Cart')
        new_cart = Cart.objects.create(
            user=original_order.cart.user,
            organisation=original_order.cart.organisation,
            product=self.bounty.product,
            status=Cart.CartStatus.COMPLETED
        )
        
        SalesOrder = apps.get_model('commerce', 'SalesOrder')
        new_order = SalesOrder.objects.create(
            cart=new_cart,
            status=SalesOrder.OrderStatus.COMPLETED,
            total_usd_cents=amount * 100,  # Convert to cents
            parent_sales_order=original_order
        )
        
        SalesOrderLineItem = apps.get_model('commerce', 'SalesOrderLineItem')
        SalesOrderLineItem.objects.create(
            sales_order=new_order,
            item_type=SalesOrderLineItem.ItemType.INCREASE_ADJUSTMENT,
            quantity=1,
            unit_price_cents=amount * 100,
            bounty=self.bounty,
            related_bounty_bid=self
        )
        
        # Process payment for increase
        new_order.process_payment()

    @transaction.atomic
    def _create_decrease_adjustment(self, original_order, amount):
        Cart = apps.get_model('commerce', 'Cart')
        new_cart = Cart.objects.create(
            user=original_order.cart.user,
            organisation=original_order.cart.organisation,
            product=self.bounty.product,
            status=Cart.CartStatus.COMPLETED
        )
        
        SalesOrder = apps.get_model('commerce', 'SalesOrder')
        new_order = SalesOrder.objects.create(
            cart=new_cart,
            status=SalesOrder.OrderStatus.COMPLETED,
            total_usd_cents=amount * 100,  # Convert to cents
            parent_sales_order=original_order
        )
        
        SalesOrderLineItem = apps.get_model('commerce', 'SalesOrderLineItem')
        SalesOrderLineItem.objects.create(
            sales_order=new_order,
            item_type=SalesOrderLineItem.ItemType.DECREASE_ADJUSTMENT,
            quantity=1,
            unit_price_cents=amount * 100,
            bounty=self.bounty,
            related_bounty_bid=self
        )
        
        # Process refund for decrease
        organisation_wallet = original_order.cart.organisation.wallet
        organisation_wallet.add_funds(
            amount_cents=amount * 100,
            description=f"Refund for bounty adjustment: {self.bounty.title}",
            related_order=new_order
        )


class BountyClaim(TimeStampMixin):
    class Status(models.TextChoices):
        ACTIVE = "Active"
        COMPLETED = "Completed"
        FAILED = "Failed"

    id = Base58UUIDv5Field(primary_key=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    accepted_bid = models.ForeignKey('BountyBid', on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        unique_together = ("bounty", "person")
        ordering = ("-created_at",)

    def __str__(self):
        return f"Claim on {self.bounty.title} by {self.person.get_full_name()}"

    @property
    def expected_finish_date(self):
        return self.accepted_bid.expected_finish_date if self.accepted_bid else None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.bounty.update_status_from_claim()

class BountyDeliveryAttempt(TimeStampMixin, AttachmentAbstract):
    class BountyDeliveryStatus(models.TextChoices):
        NEW = "New"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        CANCELLED = "Cancelled"

    id = Base58UUIDv5Field(primary_key=True)
    status = models.CharField(choices=BountyDeliveryStatus.choices, default=BountyDeliveryStatus.NEW)
    bounty_claim = models.ForeignKey(
        BountyClaim,
        on_delete=models.CASCADE,
        related_name="delivery_attempts",
    )
    delivery_message = models.CharField(max_length=2000, default=None)
    review_message = models.CharField(max_length=2000, null=True, blank=True)
    reviewed_by = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_deliveries")

    class Meta:
        ordering = ("-created_at",)

    def get_absolute_url(self):
        return reverse(
            "bounty-delivery-attempt-detail",
            kwargs={
                "product_slug": self.bounty_claim.bounty.challenge.product.slug,
                "challenge_id": self.bounty_claim.bounty.challenge.id,
                "bounty_id": self.bounty_claim.bounty.id,
                "pk": self.pk,
            },
        )

    def __str__(self):
        return f"{self.bounty_claim.person} - {self.get_status_display()}"

class Feedback(models.Model):
    id = Base58UUIDv5Field(primary_key=True)
    # Person who recevies the feedback
    recipient = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="feedback_recipient")
    # Person who sends the feedback
    provider = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="feedback_provider")
    message = models.TextField()
    stars = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    def save(self, *args, **kwargs):
        if self.recipient == self.provider:
            raise ValidationError(_("The recipient and the provider cannot be the same."))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.recipient} - {self.provider} - {self.stars} - {self.message[:10]}..."

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from polymorphic.models import PolymorphicModel
from apps.common.fields import Base58UUIDv5Field
from apps.common.mixins import TimeStampMixin
from apps.talent.models import BountyBid, Person
from django.db.models import Sum
from django.apps import apps
from django.db import transaction
from abc import ABC, abstractmethod
from apps.common.models import TreeNode
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.product_management.models import Bounty, Product, Challenge, Competition  # Add this import at the top of the file
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)


class Organisation(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=512, unique=True)
    country = models.CharField(max_length=2, default="US", help_text="ISO 3166-1 alpha-2 country code")
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")

    def __str__(self):
        return self.name


class OrganisationWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="wallet")
    balance_usd_cents = models.IntegerField(default=0)

    def __str__(self):
        return f"Wallet for {self.organisation.name}: ${self.balance_usd_cents / 100:.2f}"


class OrganisationWalletTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        DEBIT = "DEBIT", "Debit"

    id = Base58UUIDv5Field(primary_key=True)
    wallet = models.ForeignKey(OrganisationWallet, on_delete=models.CASCADE, related_name="transactions")
    amount_cents = models.IntegerField()
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField()
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    related_order = models.ForeignKey('SalesOrder', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount_cents / 100:.2f} for {self.wallet.organisation.name}"


class Cart(TimeStampMixin):
    class CartStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"
        ABANDONED = "ABANDONED", "Abandoned"

    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="carts")
    status = models.CharField(max_length=20, choices=CartStatus.choices, default=CartStatus.OPEN)
    total_usd_cents_excluding_fees_and_taxes = models.PositiveIntegerField(default=0)
    total_usd_cents_including_fees_and_taxes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Cart {self.id} - {self.get_status_display()}"


class BaseLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd_cents = models.PositiveIntegerField(null=True, blank=True)
    unit_price_points = models.PositiveIntegerField(null=True, blank=True)
    bounty = models.ForeignKey(Bounty, on_delete=models.CASCADE, null=True, blank=True)
    related_bounty_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)
    description_text = models.TextField(blank=True, help_text="Additional description or details for this line item")

    class Meta:
        abstract = True

    @property
    def total_price_usd_cents(self):
        return self.quantity * (self.unit_price_usd_cents or 0)

    @property
    def total_price_points(self):
        return self.quantity * (self.unit_price_points or 0)


class CartLineItem(BaseLineItem):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="line_items")

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.quantity} x ${self.unit_price_usd_cents / 100:.2f}"


class SalesOrder(TimeStampMixin):
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name="sales_order")
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="sales_orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_usd_cents_excluding_fees_and_taxes = models.PositiveIntegerField(default=0)
    total_usd_cents_including_fees_and_taxes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Order {self.id} - {self.get_status_display()}"


class SalesOrderLineItem(BaseLineItem):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="line_items")

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.quantity} x ${self.unit_price_usd_cents / 100:.2f}"


class ProductPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="product_point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.product.name}"


class OrganisationPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.organisation.name}"


class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance}"


class PointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        GRANT = "GRANT", "Grant"
        USE = "USE", "Use"
        REFUND = "REFUND", "Refund"
        TRANSFER = "TRANSFER", "Transfer"

    id = Base58UUIDv5Field(primary_key=True)
    account = models.ForeignKey(OrganisationPointAccount, on_delete=models.CASCADE, related_name="org_transactions", null=True, blank=True)
    product_account = models.ForeignKey(ProductPointAccount, on_delete=models.CASCADE, related_name="product_transactions", null=True, blank=True)
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        account_name = self.account.organisation.name if self.account else self.product_account.product.name
        return f"{self.get_transaction_type_display()} of {self.amount} points for {account_name}"


class ContributorPointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        EARN = "EARN", "Earn"
        USE = "USE", "Use"
        TRANSFER = "TRANSFER", "Transfer"
        REFUND = "REFUND", "Refund"

    id = Base58UUIDv5Field(primary_key=True)
    point_account = models.ForeignKey(ContributorPointAccount, on_delete=models.CASCADE, related_name="transactions")
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} points for {self.point_account.person.full_name}"


class PointOrder(TimeStampMixin):
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name="point_order")
    product_account = models.ForeignKey(ProductPointAccount, on_delete=models.CASCADE, related_name="point_orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Order {self.id} - {self.get_status_display()}"


class TaxRate(models.Model):
    country_code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2 country code")
    rate = models.DecimalField(max_digits=5, decimal_places=4, help_text="Tax rate as a decimal (e.g., 0.20 for 20%)")
    name = models.CharField(max_length=100, help_text="Name of the tax (e.g., VAT, GST)")

    def __str__(self):
        return f"{self.country_code} - {self.name}: {self.rate:.2%}"


    def __str__(self):
        return f"Order {self.id} - {self.get_status_display()}"

class SalesOrderLineItem(BaseLineItem):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="line_items")

    def __str__(self):
        return f"{self.get_item_type_display()} - {self.quantity} x ${self.unit_price_usd_cents / 100:.2f}"

class ProductPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="product_point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.product.name}"

class OrganisationPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.organisation.name}"

class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance}"

class PointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        GRANT = "GRANT", "Grant"
        USE = "USE", "Use"
        REFUND = "REFUND", "Refund"
        TRANSFER = "TRANSFER", "Transfer"

    id = Base58UUIDv5Field(primary_key=True)
    account = models.ForeignKey(OrganisationPointAccount, on_delete=models.CASCADE, related_name="org_transactions", null=True, blank=True)
    product_account = models.ForeignKey(ProductPointAccount, on_delete=models.CASCADE, related_name="product_transactions", null=True, blank=True)
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        account_name = self.account.organisation.name if self.account else self.product_account.product.name
        return f"{self.get_transaction_type_display()} of {self.amount} points for {account_name}"

class ContributorPointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        EARN = "EARN", "Earn"
        USE = "USE", "Use"
        TRANSFER = "TRANSFER", "Transfer"
        REFUND = "REFUND", "Refund"

    id = Base58UUIDv5Field(primary_key=True)
    point_account = models.ForeignKey(ContributorPointAccount, on_delete=models.CASCADE, related_name="transactions")
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount} points for {self.point_account.person.full_name}"

class PointOrder(TimeStampMixin):
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name="point_order")
    product_account = models.ForeignKey(ProductPointAccount, on_delete=models.CASCADE, related_name="point_orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Order {self.id} - {self.get_status_display()}"

class TaxRate(models.Model):
    country_code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2 country code")
    rate = models.DecimalField(max_digits=5, decimal_places=4, help_text="Tax rate as a decimal (e.g., 0.20 for 20%)")
    name = models.CharField(max_length=100, help_text="Name of the tax (e.g., VAT, GST)")

    def __str__(self):
        return f"{self.country_code} - {self.name}: {self.rate:.2%}"


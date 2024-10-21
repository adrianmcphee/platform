from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from polymorphic.models import PolymorphicModel
from apps.common.fields import Base58UUIDv5Field
from apps.common.mixins import TimeStampMixin
from apps.talent.models import BountyBid
from django.db.models import Sum
from django.apps import apps
from django.db import transaction
from abc import ABC, abstractmethod
from apps.common.models import TreeNode
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.product_management.models import Bounty  # Add this import at the top of the file

import logging

logger = logging.getLogger(__name__)

class Organisation(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=512, unique=True)
    country = models.CharField(max_length=2, default='US', help_text="ISO 3166-1 alpha-2 country code")
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")

    def clean(self):
        if not self.id:
            self.id = Base58UUIDv5Field().get_prep_value(None)
        if self.tax_id:
            self.tax_id = self.tax_id.upper().replace(" ", "")
            if not self.is_valid_tax_id():
                raise ValidationError("Invalid Tax Identification Number for the specified country.")

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = Base58UUIDv5Field().generate_id()
        skip_clean = kwargs.pop('skip_clean', False)
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def is_valid_tax_id(self):
        if self.country == "US":
            return self.is_valid_us_ein()
        elif self.country in ["GB", "IE"]:  # UK and Ireland
            return self.is_valid_vat_number()
        return True  # Default to True if no specific validation is implemented

    def is_valid_us_ein(self):
        return len(self.tax_id) == 9 and self.tax_id.isdigit()

    def is_valid_vat_number(self):
        country_prefix = self.tax_id[:2]
        number = self.tax_id[2:]
        if country_prefix != self.country:
            return False
        return len(number) >= 5 and number.isalnum()

    def get_tax_id_display(self):
        if self.country == "US":
            return f"EIN: {self.tax_id}"
        elif self.country in ["GB", "IE"]:
            return f"VAT: {self.tax_id}"
        return f"Tax ID: {self.tax_id}"

    def __str__(self):
        return self.name


class OrganisationWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="wallet")
    balance_usd_cents = models.IntegerField(default=0)

    def add_funds(self, amount_cents, description, related_order=None):
        self.balance_usd_cents += amount_cents
        self.save()
        OrganisationWalletTransaction.objects.create(
            wallet=self,
            amount_cents=amount_cents,
            transaction_type=OrganisationWalletTransaction.TransactionType.CREDIT,
            description=description,
            related_order=related_order,
        )

    @classmethod
    def deduct_funds(cls, wallet, amount_cents, description):
        if wallet.balance_usd_cents >= amount_cents:
            wallet.balance_usd_cents -= amount_cents
            wallet.save()
            return True
        return False

    def __str__(self):
        return f"Wallet for {self.organisation.name}: ${self.balance_usd_cents / 100:.2f}"


class OrganisationWalletTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        CREDIT = "Credit", "Credit"
        DEBIT = "Debit", "Debit"

    class PaymentMethod(models.TextChoices):
        PAYPAL = "PayPal", "PayPal"
        USDT = "USDT", "USDT"
        CREDIT_CARD = "CreditCard", "Credit Card"
        ORGANISATION_WALLET = "OrganisationWallet", "Organisation Wallet"  # For debiting from the wallet directly

    id = Base58UUIDv5Field(primary_key=True)
    wallet = models.ForeignKey(OrganisationWallet, on_delete=models.CASCADE, related_name="transactions")
    amount_cents = models.IntegerField()  # Storing amount in cents for better precision
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField()
    related_order = models.ForeignKey("SalesOrder", null=True, blank=True, on_delete=models.SET_NULL)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)
    transaction_id = models.CharField(
        max_length=255, null=True, blank=True
    )  # External transaction ID (e.g., PayPal or crypto transaction hash)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount_cents / 100:.2f} for {self.wallet.organisation.name}"


class OrganisationPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE, related_name="point_account")
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.organisation.name}"

    def add_points(self, amount):
        try:
            amount_int = int(amount)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount}. Amount must be a valid integer.")

        if amount_int < 0:
            raise ValueError(f"Invalid amount: {amount_int}. Amount must be non-negative.")

        self.balance += amount_int
        self.save()

    def use_points(self, amount):
        try:
            amount_int = int(amount)
        except ValueError:
            raise ValueError(f"Invalid amount: {amount}. Amount must be a valid integer.")

        if amount_int < 0:
            raise ValueError(f"Invalid amount: {amount_int}. Amount must be non-negative.")

        if self.balance >= amount_int:
            self.balance -= amount_int
            self.save()
            return True
        return False

    @transaction.atomic
    def transfer_points_to_product(self, product, amount):
        if self.use_points(amount):
            product_account, created = ProductPointAccount.objects.get_or_create(product=product)
            product_account.add_points(amount)
            PointTransaction.objects.create(
                account=self,
                product_account=product_account,
                amount=amount,
                transaction_type="TRANSFER",
                description=f"Transfer from {self.organisation.name} to {product.name}",
            )
            return True
        return False


class ProductPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.OneToOneField(
        "product_management.Product", on_delete=models.CASCADE, related_name="product_point_account"
    )
    balance = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Point Account for {self.product.name}"

    def add_points(self, amount):
        self.balance += amount
        self.save()

    def use_points(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False


class PointTransaction(TimeStampMixin):
    TRANSACTION_TYPES = [("GRANT", "Grant"), ("USE", "Use"), ("REFUND", "Refund"), ("TRANSFER", "Transfer")]
    id = Base58UUIDv5Field(primary_key=True)
    account = models.ForeignKey(
        OrganisationPointAccount, on_delete=models.CASCADE, related_name="org_transactions", null=True, blank=True
    )
    product_account = models.ForeignKey(
        ProductPointAccount, on_delete=models.CASCADE, related_name="product_transactions", null=True, blank=True
    )
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)

    def __str__(self):
        account_name = self.account.organisation.name if self.account else self.product_account.product.name
        return f"{self.get_transaction_type_display()} of {self.amount} points for {account_name}"

    def clean(self):
        if (self.account is None) == (self.product_account is None):
            raise ValidationError(
                "Transaction must be associated with either an OrganisationPointAccount or a ProductPointAccount, but not both."
            )


class OrganisationPointGrant(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="point_grants")
    amount = models.PositiveIntegerField()
    granted_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="granted_points"
    )
    rationale = models.TextField()
    grant_request = models.OneToOneField(
        'OrganisationPointGrantRequest', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="resulting_grant"
    )

    def __str__(self):
        return f"Grant of {self.amount} points to {self.organisation.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.organisation.point_account.add_points(self.amount)
        PointTransaction.objects.create(
            account=self.organisation.point_account,
            amount=self.amount,
            transaction_type="GRANT",
            description=f"Grant: {self.rationale}",
        )


class OrganisationPointGrantRequest(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="point_grant_requests")
    amount_points = models.PositiveIntegerField()
    requested_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="point_grant_requests"
    )
    rationale = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending",
    )

    def approve(self):
        if self.status == "Pending":
            self.status = "Approved"
            self.save()
            
            # Create the OrganisationPointGrant
            grant = OrganisationPointGrant.objects.create(
                organisation=self.organisation,
                amount=self.amount_points,
                granted_by=self.requested_by,
                rationale=self.rationale,
                grant_request=self
            )
            
            # The point addition and transaction creation are now handled in the OrganisationPointGrant.save() method

    def reject(self):
        if self.status == "Pending":
            self.status = "Rejected"
            self.save()


class ProductPointRequest(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey("product_management.Product", on_delete=models.CASCADE, related_name="point_requests")
    amount_points = models.PositiveIntegerField()
    requested_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="product_point_requests"
    )
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending",
    )
    resulting_transaction = models.OneToOneField(
        PointTransaction, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="product_point_request"
    )

    def approve(self):
        if self.status == "Pending":
            self.status = "Approved"
            self.save()
            
            # Add points to the product's point account
            product_account, created = ProductPointAccount.objects.get_or_create(product=self.product)
            product_account.add_points(self.amount_points)
            
            # Create the PointTransaction
            transaction = PointTransaction.objects.create(
                product_account=product_account,
                amount=self.amount_points,
                transaction_type="TRANSFER",
                description=f"Transfer to product: {self.product.name}",
            )
            
            # Link the transaction to this request
            self.resulting_transaction = transaction
            self.save()

    def reject(self):
        if self.status == "Pending":
            self.status = "Rejected"
            self.save()


class ContributorWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="wallet")
    balance_usd_in_cents = models.IntegerField(default=0)  # Balance stored as cents for precision

    def __str__(self):
        # Format the balance as dollars for readability
        return f"Wallet for {self.person.full_name} - USD: ${self.balance_usd_in_cents / 100:.2f}"

    def add_funds(self, amount_cents):
        self.balance_usd_in_cents += amount_cents
        self.save()

    def deduct_funds(self, amount_cents):
        if self.balance_usd_in_cents >= amount_cents:
            self.balance_usd_in_cents -= amount_cents
            self.save()
            return True
        return False


class ContributorWalletTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        CREDIT = "Credit", "Credit"
        DEBIT = "Debit", "Debit"
        WITHDRAWAL = "Withdrawal", "Withdrawal"

    class PaymentMethod(models.TextChoices):
        PAYPAL = "PayPal", "PayPal"
        USDT = "USDT", "USDT"
        CREDIT_CARD = "CreditCard", "Credit Card"
        CONTRIBUTOR_WALLET = "ContributorWallet", "Contributor Wallet"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"

    id = Base58UUIDv5Field(primary_key=True)
    wallet = models.ForeignKey(ContributorWallet, on_delete=models.CASCADE, related_name="transactions")
    amount_cents = models.IntegerField()  # Amount stored as cents for precision
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)  # External transaction ID

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount_cents / 100:.2f} for {self.wallet.person.full_name}"

    def process(self):
        if self.status != self.Status.PENDING:
            return False

        try:
            if self.transaction_type == self.TransactionType.CREDIT:
                self.wallet.add_funds(self.amount_cents)
            elif self.transaction_type in [self.TransactionType.DEBIT, self.TransactionType.WITHDRAWAL]:
                if not self.wallet.deduct_funds(self.amount_cents):
                    raise ValueError("Insufficient funds")

            self.status = self.Status.COMPLETED
            self.save()
            return True
        except Exception as e:
            self.status = self.Status.FAILED
            self.save()
            raise e


class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="point_account")
    balance_points = models.IntegerField(default=0)  # Balance stored as integer points

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance_points}"

    def add_points(self, amount_points):
        self.balance_points += amount_points
        self.save()


class ContributorPointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        EARN = "Earn", "Earn"
        USE = "Use", "Use"
        TRANSFER = "Transfer", "Transfer"
        REFUND = "Refund", "Refund"

    id = Base58UUIDv5Field(primary_key=True)
    point_account = models.ForeignKey(ContributorPointAccount, on_delete=models.CASCADE, related_name="transactions")
    amount_points = models.IntegerField()  # Points being transacted
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount_points} points for {self.point_account.person.full_name}"


class PlatformFeeConfiguration(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    percentage = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)])
    applies_from_date = models.DateTimeField()

    @classmethod
    def get_active_configuration(cls):
        return cls.objects.filter(applies_from_date__lte=timezone.now()).order_by("-applies_from_date").first()

    @property
    def percentage_decimal(self):
        return self.percentage / 100

    def __str__(self):
        return f"{self.percentage}% Platform Fee (from {self.applies_from_date})"

    class Meta:
        get_latest_by = "applies_from_date"


class CartLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.ForeignKey("Cart", related_name="line_items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd_cents = models.PositiveIntegerField(null=True, blank=True)
    unit_price_points = models.PositiveIntegerField(null=True, blank=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    related_bounty_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)
    funding_type = models.CharField(max_length=10, choices=[('USD', 'USD'), ('POINTS', 'Points')], default='USD')

    def clean(self):
        super().clean()
        if self.bounty:
            if self.bounty.reward_type == 'USD' and self.unit_price_points:
                raise ValidationError("USD bounties should not have point prices.")
            elif self.bounty.reward_type == 'POINTS' and self.unit_price_usd_cents:
                raise ValidationError("Point bounties should not have USD prices.")
            
            if self.funding_type != self.bounty.reward_type:
                raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if self.bounty:
            self.funding_type = self.bounty.reward_type
            if self.funding_type == 'USD':
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
                self.unit_price_points = None
            else:  # POINTS
                self.unit_price_points = self.bounty.reward_in_points
                self.unit_price_usd_cents = None
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        if self.funding_type == 'USD':
            return self.unit_price_usd_cents * self.quantity
        else:  # POINTS
            return self.unit_price_points * self.quantity

    def __str__(self):
        return f"{self.get_item_type_display()} for Cart {self.cart.id}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.related_bounty_bid:
                raise ValidationError("Adjustment line items must be associated with a bounty bid.")
        elif self.related_bounty_bid:
            raise ValidationError("Only adjustment line items can be associated with a bounty bid.")
        super().clean()
        if self.bounty and self.funding_type != self.bounty.reward_type:
            raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if not self.unit_price_usd_cents and hasattr(self, 'bounty') and self.bounty:
            if hasattr(self.bounty, 'reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
            elif hasattr(self.bounty, 'final_reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.final_reward_in_usd_cents
        if self.bounty and not self.funding_type:
            self.funding_type = self.bounty.reward_type
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("cart", "bounty")

    @classmethod
    def create(cls, **kwargs):
        if kwargs.get('item_type') == cls.ItemType.PLATFORM_FEE:
            kwargs['bounty'] = None
        return cls.objects.create(**kwargs)


class ContributorWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="wallet")
    balance_usd_in_cents = models.IntegerField(default=0)  # Balance stored as cents for precision

    def __str__(self):
        # Format the balance as dollars for readability
        return f"Wallet for {self.person.full_name} - USD: ${self.balance_usd_in_cents / 100:.2f}"

    def add_funds(self, amount_cents):
        self.balance_usd_in_cents += amount_cents
        self.save()

    def deduct_funds(self, amount_cents):
        if self.balance_usd_in_cents >= amount_cents:
            self.balance_usd_in_cents -= amount_cents
            self.save()
            return True
        return False


class ContributorWalletTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        CREDIT = "Credit", "Credit"
        DEBIT = "Debit", "Debit"
        WITHDRAWAL = "Withdrawal", "Withdrawal"

    class PaymentMethod(models.TextChoices):
        PAYPAL = "PayPal", "PayPal"
        USDT = "USDT", "USDT"
        CREDIT_CARD = "CreditCard", "Credit Card"
        CONTRIBUTOR_WALLET = "ContributorWallet", "Contributor Wallet"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"

    id = Base58UUIDv5Field(primary_key=True)
    wallet = models.ForeignKey(ContributorWallet, on_delete=models.CASCADE, related_name="transactions")
    amount_cents = models.IntegerField()  # Amount stored as cents for precision
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)  # External transaction ID

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount_cents / 100:.2f} for {self.wallet.person.full_name}"

    def process(self):
        if self.status != self.Status.PENDING:
            return False

        try:
            if self.transaction_type == self.TransactionType.CREDIT:
                self.wallet.add_funds(self.amount_cents)
            elif self.transaction_type in [self.TransactionType.DEBIT, self.TransactionType.WITHDRAWAL]:
                if not self.wallet.deduct_funds(self.amount_cents):
                    raise ValueError("Insufficient funds")

            self.status = self.Status.COMPLETED
            self.save()
            return True
        except Exception as e:
            self.status = self.Status.FAILED
            self.save()
            raise e


class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="point_account")
    balance_points = models.IntegerField(default=0)  # Balance stored as integer points

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance_points}"

    def add_points(self, amount_points):
        self.balance_points += amount_points
        self.save()


class ContributorPointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        EARN = "Earn", "Earn"
        USE = "Use", "Use"
        TRANSFER = "Transfer", "Transfer"
        REFUND = "Refund", "Refund"

    id = Base58UUIDv5Field(primary_key=True)
    point_account = models.ForeignKey(ContributorPointAccount, on_delete=models.CASCADE, related_name="transactions")
    amount_points = models.IntegerField()  # Points being transacted
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount_points} points for {self.point_account.person.full_name}"


class PlatformFeeConfiguration(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    percentage = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)])
    applies_from_date = models.DateTimeField()

    @classmethod
    def get_active_configuration(cls):
        return cls.objects.filter(applies_from_date__lte=timezone.now()).order_by("-applies_from_date").first()

    @property
    def percentage_decimal(self):
        return self.percentage / 100

    def __str__(self):
        return f"{self.percentage}% Platform Fee (from {self.applies_from_date})"

    class Meta:
        get_latest_by = "applies_from_date"


class CartLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.ForeignKey("Cart", related_name="line_items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd_cents = models.PositiveIntegerField(null=True, blank=True)
    unit_price_points = models.PositiveIntegerField(null=True, blank=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    related_bounty_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)
    funding_type = models.CharField(max_length=10, choices=[('USD', 'USD'), ('POINTS', 'Points')], default='USD')

    def clean(self):
        super().clean()
        if self.bounty:
            if self.bounty.reward_type == 'USD' and self.unit_price_points:
                raise ValidationError("USD bounties should not have point prices.")
            elif self.bounty.reward_type == 'POINTS' and self.unit_price_usd_cents:
                raise ValidationError("Point bounties should not have USD prices.")
            
            if self.funding_type != self.bounty.reward_type:
                raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if self.bounty:
            self.funding_type = self.bounty.reward_type
            if self.funding_type == 'USD':
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
                self.unit_price_points = None
            else:  # POINTS
                self.unit_price_points = self.bounty.reward_in_points
                self.unit_price_usd_cents = None
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_price(self):
        if self.funding_type == 'USD':
            return self.unit_price_usd_cents * self.quantity
        else:  # POINTS
            return self.unit_price_points * self.quantity

    def __str__(self):
        return f"{self.get_item_type_display()} for Cart {self.cart.id}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.related_bounty_bid:
                raise ValidationError("Adjustment line items must be associated with a bounty bid.")
        elif self.related_bounty_bid:
            raise ValidationError("Only adjustment line items can be associated with a bounty bid.")
        super().clean()
        if self.bounty and self.funding_type != self.bounty.reward_type:
            raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if not self.unit_price_usd_cents and hasattr(self, 'bounty') and self.bounty:
            if hasattr(self.bounty, 'reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
            elif hasattr(self.bounty, 'final_reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.final_reward_in_usd_cents
        if self.bounty and not self.funding_type:
            self.funding_type = self.bounty.reward_type
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("cart", "bounty")

    @classmethod
    def create(cls, **kwargs):
        if kwargs.get('item_type') == cls.ItemType.PLATFORM_FEE:
            kwargs['bounty'] = None
        return cls.objects.create(**kwargs)


class PointTransaction(TimeStampMixin):
    TRANSACTION_TYPES = [("GRANT", "Grant"), ("USE", "Use"), ("REFUND", "Refund"), ("TRANSFER", "Transfer")]
    id = Base58UUIDv5Field(primary_key=True)
    account = models.ForeignKey(
        OrganisationPointAccount, on_delete=models.CASCADE, related_name="org_transactions", null=True, blank=True
    )
    product_account = models.ForeignKey(
        ProductPointAccount, on_delete=models.CASCADE, related_name="product_transactions", null=True, blank=True
    )
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)

    def __str__(self):
        account_name = self.account.organisation.name if self.account else self.product_account.product.name
        return f"{self.get_transaction_type_display()} of {self.amount} points for {account_name}"

    def clean(self):
        if (self.account is None) == (self.product_account is None):
            raise ValidationError(
                "Transaction must be associated with either an OrganisationPointAccount or a ProductPointAccount, but not both."
            )


class OrganisationPointGrant(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="point_grants")
    amount = models.PositiveIntegerField()
    granted_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="granted_points"
    )
    rationale = models.TextField()
    grant_request = models.OneToOneField(
        'OrganisationPointGrantRequest', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="resulting_grant"
    )

    def __str__(self):
        return f"Grant of {self.amount} points to {self.organisation.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.organisation.point_account.add_points(self.amount)
        PointTransaction.objects.create(
            account=self.organisation.point_account,
            amount=self.amount,
            transaction_type="GRANT",
            description=f"Grant: {self.rationale}",
        )


class OrganisationPointGrantRequest(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="point_grant_requests")
    amount_points = models.PositiveIntegerField()
    requested_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="point_grant_requests"
    )
    rationale = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending",
    )

    def approve(self):
        if self.status == "Pending":
            self.status = "Approved"
            self.save()
            
            # Create the OrganisationPointGrant
            grant = OrganisationPointGrant.objects.create(
                organisation=self.organisation,
                amount=self.amount_points,
                granted_by=self.requested_by,
                rationale=self.rationale,
                grant_request=self
            )
            
            # The point addition and transaction creation are now handled in the OrganisationPointGrant.save() method

    def reject(self):
        if self.status == "Pending":
            self.status = "Rejected"
            self.save()


class ProductPointRequest(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    product = models.ForeignKey("product_management.Product", on_delete=models.CASCADE, related_name="point_requests")
    amount_points = models.PositiveIntegerField()
    requested_by = models.ForeignKey(
        "talent.Person", on_delete=models.SET_NULL, null=True, related_name="product_point_requests"
    )
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
        default="Pending",
    )
    resulting_transaction = models.OneToOneField(
        PointTransaction, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="product_point_request"
    )

    def approve(self):
        if self.status == "Pending":
            self.status = "Approved"
            self.save()
            
            # Add points to the product's point account
            product_account, created = ProductPointAccount.objects.get_or_create(product=self.product)
            product_account.add_points(self.amount_points)
            
            # Create the PointTransaction
            transaction = PointTransaction.objects.create(
                product_account=product_account,
                amount=self.amount_points,
                transaction_type="TRANSFER",
                description=f"Transfer to product: {self.product.name}",
            )
            
            # Link the transaction to this request
            self.resulting_transaction = transaction
            self.save()

    def reject(self):
        if self.status == "Pending":
            self.status = "Rejected"
            self.save()


class ContributorWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="wallet")
    balance_usd_in_cents = models.IntegerField(default=0)  # Balance stored as cents for precision

    def __str__(self):
        # Format the balance as dollars for readability
        return f"Wallet for {self.person.full_name} - USD: ${self.balance_usd_in_cents / 100:.2f}"

    def add_funds(self, amount_cents):
        self.balance_usd_in_cents += amount_cents
        self.save()

    def deduct_funds(self, amount_cents):
        if self.balance_usd_in_cents >= amount_cents:
            self.balance_usd_in_cents -= amount_cents
            self.save()
            return True
        return False


class ContributorWalletTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        CREDIT = "Credit", "Credit"
        DEBIT = "Debit", "Debit"
        WITHDRAWAL = "Withdrawal", "Withdrawal"

    class PaymentMethod(models.TextChoices):
        PAYPAL = "PayPal", "PayPal"
        USDT = "USDT", "USDT"
        CREDIT_CARD = "CreditCard", "Credit Card"
        CONTRIBUTOR_WALLET = "ContributorWallet", "Contributor Wallet"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        COMPLETED = "Completed", "Completed"
        FAILED = "Failed", "Failed"

    id = Base58UUIDv5Field(primary_key=True)
    wallet = models.ForeignKey(ContributorWallet, on_delete=models.CASCADE, related_name="transactions")
    amount_cents = models.IntegerField()  # Amount stored as cents for precision
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)  # External transaction ID

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount_cents / 100:.2f} for {self.wallet.person.full_name}"

    def process(self):
        if self.status != self.Status.PENDING:
            return False

        try:
            if self.transaction_type == self.TransactionType.CREDIT:
                self.wallet.add_funds(self.amount_cents)
            elif self.transaction_type in [self.TransactionType.DEBIT, self.TransactionType.WITHDRAWAL]:
                if not self.wallet.deduct_funds(self.amount_cents):
                    raise ValueError("Insufficient funds")

            self.status = self.Status.COMPLETED
            self.save()
            return True
        except Exception as e:
            self.status = self.Status.FAILED
            self.save()
            raise e


class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField("talent.Person", on_delete=models.CASCADE, related_name="point_account")
    balance_points = models.IntegerField(default=0)  # Balance stored as integer points

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance_points}"

    def add_points(self, amount_points):
        self.balance_points += amount_points
        self.save()


class ContributorPointTransaction(TimeStampMixin):
    class TransactionType(models.TextChoices):
        EARN = "Earn", "Earn"
        USE = "Use", "Use"
        TRANSFER = "Transfer", "Transfer"
        REFUND = "Refund", "Refund"

    id = Base58UUIDv5Field(primary_key=True)
    point_account = models.ForeignKey(ContributorPointAccount, on_delete=models.CASCADE, related_name="transactions")
    amount_points = models.IntegerField()  # Points being transacted
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of {self.amount_points} points for {self.point_account.person.full_name}"


class PlatformFeeConfiguration(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    percentage = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1), MaxValueValidator(100)])
    applies_from_date = models.DateTimeField()

    @classmethod
    def get_active_configuration(cls):
        return cls.objects.filter(applies_from_date__lte=timezone.now()).order_by("-applies_from_date").first()

    @property
    def percentage_decimal(self):
        return self.percentage / 100

    def __str__(self):
        return f"{self.percentage}% Platform Fee (from {self.applies_from_date})"

    class Meta:
        get_latest_by = "applies_from_date"


class CartLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.ForeignKey("Cart", related_name="line_items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd_cents = models.PositiveIntegerField(null=True, blank=True)
    unit_price_points = models.PositiveIntegerField(null=True, blank=True)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.CASCADE, related_name='cart_items', null=True, blank=True)
    related_bounty_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)
    funding_type = models.CharField(max_length=10, choices=[('USD', 'USD'), ('POINTS', 'Points')], default='USD')

    @property
    def total_price_usd_cents(self):
        if self.funding_type == 'USD':
            return self.unit_price_usd_cents * self.quantity
        else:  # POINTS
            return 0  # or convert points to USD if needed

    def clean(self):
        super().clean()
        if self.bounty:
            if self.bounty.reward_type == 'USD' and self.unit_price_points:
                raise ValidationError("USD bounties should not have point prices.")
            elif self.bounty.reward_type == 'POINTS' and self.unit_price_usd_cents:
                raise ValidationError("Point bounties should not have USD prices.")
            
            if self.funding_type != self.bounty.reward_type:
                raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if self.bounty:
            self.funding_type = self.bounty.reward_type
            if self.funding_type == 'USD':
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
                self.unit_price_points = None
            else:  # POINTS
                self.unit_price_points = self.bounty.reward_in_points
                self.unit_price_usd_cents = None
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_item_type_display()} for Cart {self.cart.id}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.related_bounty_bid:
                raise ValidationError("Adjustment line items must be associated with a bounty bid.")
        elif self.related_bounty_bid:
            raise ValidationError("Only adjustment line items can be associated with a bounty bid.")
        super().clean()
        if self.bounty and self.funding_type != self.bounty.reward_type:
            raise ValidationError(f"Funding type must match the bounty's reward type: {self.bounty.reward_type}")

    def save(self, *args, **kwargs):
        if not self.unit_price_usd_cents and hasattr(self, 'bounty') and self.bounty:
            if hasattr(self.bounty, 'reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.reward_in_usd_cents
            elif hasattr(self.bounty, 'final_reward_in_usd_cents'):
                self.unit_price_usd_cents = self.bounty.final_reward_in_usd_cents
        if self.bounty and not self.funding_type:
            self.funding_type = self.bounty.reward_type
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ("cart", "bounty")

    @classmethod
    def create(cls, **kwargs):
        if kwargs.get('item_type') == cls.ItemType.PLATFORM_FEE:
            kwargs['bounty'] = None
        return cls.objects.create(**kwargs)


class Cart(TimeStampMixin):
    class CartStatus(models.TextChoices):
        OPEN = "OPEN", _("Open")
        CHECKED_OUT = "CHECKED_OUT", _("Checked Out")
        ABANDONED = "ABANDONED", _("Abandoned")

    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey("talent.Person", on_delete=models.CASCADE, related_name="carts")
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name="carts")
    status = models.CharField(
        max_length=20,
        choices=CartStatus.choices,
        default=CartStatus.OPEN,
    )
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 country code of the user")

    total_usd_cents_excluding_fees_and_taxes = models.PositiveIntegerField(default=0)
    total_fees_usd_cents = models.PositiveIntegerField(default=0)
    total_taxes_usd_cents = models.PositiveIntegerField(default=0)
    total_usd_cents_including_fees_and_taxes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Cart {self.id} - ({self.status})"

    def calculate_platform_fee_rate(self):
        active_config = PlatformFeeConfiguration.get_active_configuration()
        if active_config:
            return active_config.percentage_decimal
        return 0  # Default to 0 if no configuration is found

    def update_totals(self):
        line_items = self.line_items.all()
        
        self.total_usd_cents_excluding_fees_and_taxes = sum(
            item.total_price_usd_cents for item in line_items 
            if item.item_type not in [CartLineItem.ItemType.PLATFORM_FEE, CartLineItem.ItemType.SALES_TAX]
        )
        
        fee_rate = self.calculate_platform_fee_rate()
        platform_fee = int(self.total_usd_cents_excluding_fees_and_taxes * fee_rate)
        
        # Create or update the platform fee line item
        platform_fee_item, created = CartLineItem.objects.get_or_create(
            cart=self,
            item_type=CartLineItem.ItemType.PLATFORM_FEE,
            defaults={'unit_price_usd_cents': platform_fee, 'quantity': 1}
        )
        if not created:
            platform_fee_item.unit_price_usd_cents = platform_fee
            platform_fee_item.save()

        self.total_fees_usd_cents = platform_fee
        self.total_taxes_usd_cents = sum(
            item.total_price_usd_cents for item in line_items 
            if item.item_type == CartLineItem.ItemType.SALES_TAX
        )
        
        self.total_usd_cents_including_fees_and_taxes = self.calculate_total_amount()
        self.save(updating_totals=True)

    def calculate_sales_tax(self):
        # Implement sales tax calculation logic here
        # This is a placeholder, adjust as needed
        return 0

    @property
    def total_usd_cents(self):
        return sum(item.unit_price_cents * item.quantity for item in self.items.all())

    @property
    def total_amount_cents(self):
        return self.total_usd_cents + self.calculate_platform_fee() + self.calculate_sales_tax()

    @property
    def total_amount(self):
        return self.total_amount_cents / 100

    def add_adjustment(self, bounty_bid, amount_cents, is_increase=True):
        item_type = (
            CartLineItem.ItemType.INCREASE_ADJUSTMENT if is_increase else CartLineItem.ItemType.DECREASE_ADJUSTMENT
        )
        adjustment = CartLineItem.objects.create(
            cart=self,
            item_type=item_type,
            quantity=1,
            unit_price_cents=abs(amount_cents),
            related_bounty_bid=bounty_bid,
        )
        return adjustment

    def remove_adjustment(self, bounty_bid):
        self.items.filter(
            item_type__in=[CartLineItem.ItemType.INCREASE_ADJUSTMENT, CartLineItem.ItemType.DECREASE_ADJUSTMENT],
            related_bounty_bid=bounty_bid,
        ).delete()

    def is_user_in_europe(self):
        european_countries = [
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
            "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
        ]
        return self.user_country in european_countries

    def total_points(self):
        return sum(item.points for item in self.items.all() if item.bounty.reward_type == "Points")

    def total_usd_cents(self):
        return sum(item.funding_amount for item in self.items.all() if item.bounty.reward_type == "USD")

    def calculate_total_amount(self):
        """
        Calculate the total amount for the cart, including fees and taxes.
        """
        subtotal = self.total_usd_cents_excluding_fees_and_taxes
        total = subtotal + self.total_fees_usd_cents + self.total_taxes_usd_cents
        return total

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        updating_totals = kwargs.pop('updating_totals', False)
        super().save(*args, **kwargs)
        if is_new and not updating_totals:
            self.update_totals()

    def update_sales_order(self):
        sales_order, created = SalesOrder.objects.get_or_create(cart=self)
        sales_order.total_usd_cents_excluding_fees_and_taxes = self.total_usd_cents_excluding_fees_and_taxes
        sales_order.total_fees_usd_cents = self.total_fees_usd_cents
        sales_order.total_taxes_usd_cents = self.total_taxes_usd_cents
        sales_order.total_usd_cents_including_fees_and_taxes = self.total_usd_cents_including_fees_and_taxes
        sales_order.save()

    @property
    def salesorder(self):
        return self.salesorders.first()


class SalesOrder(TimeStampMixin):
    class OrderStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        PAYMENT_PROCESSING = "Payment Processing", "Payment Processing"
        COMPLETED = "Completed", "Completed"
        PAYMENT_FAILED = "Payment Failed", "Payment Failed"
        REFUNDED = "Refunded", "Refunded"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField('Cart', on_delete=models.CASCADE, related_name='salesorder')
    organisation = models.ForeignKey('Organisation', on_delete=models.CASCADE)
    total_usd_cents_excluding_fees_and_taxes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_fees_usd_cents = models.PositiveIntegerField(default=0)
    total_taxes_usd_cents = models.PositiveIntegerField(default=0)
    total_usd_cents_including_fees_and_taxes = models.PositiveIntegerField(default=0)
    parent_order = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='child_orders')

    def __str__(self):
        return f"Sales Order {self.id} for Cart {self.cart.id}"

    def calculate_total_amount(self):
        """
        Calculate the total amount for the order, including fees and taxes.
        """
        subtotal = self.total_usd_cents_excluding_fees_and_taxes
        total = subtotal + self.total_fees_usd_cents + self.total_taxes_usd_cents
        return total

    def update_totals(self):
        """
        Update the order totals based on the associated line items.
        """
        line_items = self.line_items.all()
        
        self.total_usd_cents_excluding_fees_and_taxes = sum(
            item.total_price_cents for item in line_items 
            if item.item_type not in [SalesOrderLineItem.ItemType.PLATFORM_FEE, SalesOrderLineItem.ItemType.SALES_TAX]
        )
        
        self.total_fees_usd_cents = sum(
            item.total_price_cents for item in line_items 
            if item.item_type == SalesOrderLineItem.ItemType.PLATFORM_FEE
        )
        
        self.total_taxes_usd_cents = sum(
            item.total_price_cents for item in line_items 
            if item.item_type == SalesOrderLineItem.ItemType.SALES_TAX
        )
        
        self.total_usd_cents_including_fees_and_taxes = self.calculate_total_amount()
        self.save()

    def validate_order(self):
        """
        Validate the order before processing payment.
        Raises ValidationError if the order is invalid.
        """
        if self.status != self.OrderStatus.PENDING:
            raise ValidationError(f"Cannot process payment for order {self.id}. Current status: {self.status}")

        if not self.line_items.exists():
            raise ValidationError(f"Order {self.id} has no line items.")

        self.update_totals()
        total_amount = self.calculate_total_amount()

        if total_amount <= 0:
            raise ValidationError(f"Order {self.id} has an invalid total amount: {total_amount} cents")

        wallet = self.organisation.wallet
        if wallet.balance_usd_cents < total_amount:
            raise ValidationError(f"Insufficient funds for order {self.id}. Required: {total_amount} cents, Available: {wallet.balance_usd_cents} cents")

    @transaction.atomic
    def process_payment(self):
        try:
            self.validate_order()
        except ValidationError as e:
            error_msg = str(e)
            logger.error(error_msg)
            self.status = self.OrderStatus.PAYMENT_FAILED
            self.save()
            return False, error_msg

        try:
            wallet = self.organisation.wallet
            total_amount = self.calculate_total_amount()

            deduction_successful = OrganisationWallet.deduct_funds(
                wallet,
                total_amount,
                f"Payment for order {self.id}"
            )

            if deduction_successful:
                self.status = self.OrderStatus.COMPLETED
                self.save()
                self.cart.status = 'CHECKED_OUT'
                self.cart.save()

                OrganisationWalletTransaction.objects.create(
                    wallet=wallet,
                    amount_cents=total_amount,
                    transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
                    description=f"Payment for order {self.id}",
                    related_order=self
                )

                self._activate_purchases()
                success_msg = f"Payment processed successfully for order {self.id}"
                logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = f"Failed to deduct funds for order {self.id}. Please try again or contact support."
                logger.error(error_msg)
                self.status = self.OrderStatus.PAYMENT_FAILED
                self.save()
                return False, error_msg

        except Exception as e:
            error_msg = f"Error processing payment for order {self.id}: {str(e)}"
            logger.exception(error_msg)
            self.status = self.OrderStatus.PAYMENT_FAILED
            self.save()
            return False, error_msg

    def _activate_purchases(self):
        for item in self.line_items.filter(item_type=SalesOrderLineItem.ItemType.BOUNTY):
            bounty = item.bounty
            Bounty = apps.get_model("product_management", "Bounty")
            bounty.status = Bounty.BountyStatus.OPEN
            bounty.save()
            if bounty.challenge:
                self._activate_challenge(bounty.challenge)
            elif bounty.competition:
                self._activate_competition(bounty.competition)

    def _activate_challenge(self, challenge):
        Challenge = apps.get_model("product_management", "Challenge")
        if challenge.status != Challenge.ChallengeStatus.ACTIVE:
            challenge.status = Challenge.ChallengeStatus.ACTIVE
            challenge.save()

    def _activate_competition(self, competition):
        Competition = apps.get_model("product_management", "Competition")
        if competition.status == Competition.CompetitionStatus.DRAFT:
            competition.status = Competition.CompetitionStatus.ACTIVE
            competition.save()
        # TODO: Add additional activation logic (e.g., setting start date, notifications)

    def save(self, *args, **kwargs):
        if not self.organisation_id and self.cart:
            self.organisation = self.cart.organisation
        super().save(*args, **kwargs)


class SalesOrderLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    sales_order = models.ForeignKey(SalesOrder, related_name="line_items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_usd_cents = models.PositiveIntegerField()
    unit_price_points = models.PositiveIntegerField(default=0)
    bounty = models.ForeignKey("product_management.Bounty", on_delete=models.SET_NULL, null=True, blank=True)
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    related_bounty_bid = models.ForeignKey("talent.BountyBid", on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_price_cents(self):
        if self.quantity is None or self.unit_price_usd_cents is None:
            return 0
        return self.quantity * self.unit_price_usd_cents

    def __str__(self):
        if self.item_type == "BOUNTY":
            price = (
                f"{self.unit_price_usd_cents/100:.2f} USD"
                if self.bounty.reward_type == "USD"
                else f"{self.unit_price_points} Points"
            )
        else:
            price = f"{self.unit_price_usd_cents/100:.2f} USD"
        return f"{self.item_type} - {price}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.sales_order.parent_order:
                raise ValidationError(
                    "Adjustment line items must be associated with a sales order that has a parent order."
                )
            if not self.related_bounty_bid:
                raise ValidationError("Adjustment line items must be associated with a bounty bid.")
        elif self.related_bounty_bid:
            raise ValidationError("Only adjustment line items can be associated with a bounty bid.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PointOrder(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE, related_name="point_order")
    product_account = models.ForeignKey(ProductPointAccount, on_delete=models.CASCADE, related_name="point_orders")
    total_points = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("COMPLETED", "Completed"),
            ("REFUNDED", "Refunded"),
        ],
        default="PENDING",
    )
    parent_order = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="adjustments"
    )

    def __str__(self):
        return f"Point Order of {self.total_points} points for Cart {self.cart.id}"

    @transaction.atomic
    def complete(self):
        if self.status != "PENDING":
            return False

        if self.product_account.use_points(self.total_points):
            self.status = "COMPLETED"
            self.save()
            self._create_point_transactions()
            self._activate_purchases()
            return True
        return False

    @transaction.atomic
    def refund(self):
        if self.status != "COMPLETED":
            return False

        self.product_account.balance += self.total_points
        self.product_account.save()
        self.status = "REFUNDED"
        self.save()
        self._create_refund_transactions()
        self._deactivate_purchases()
        return True

    def _create_point_transactions(self):
        for item in self.cart.line_items.filter(funding_type="POINTS"):
            PointTransaction.objects.create(
                product_account=self.product_account,
                amount=item.unit_price_points,
                transaction_type="PURCHASE",
                description=f"Points used for Bounty: {item.bounty.title}",
            )

    def _create_refund_transactions(self):
        for item in self.cart.line_items.filter(funding_type="POINTS"):
            PointTransaction.objects.create(
                product_account=self.product_account,
                amount=item.unit_price_points,
                transaction_type="REFUND",
                description=f"Points refunded for Bounty: {item.bounty.title}",
            )

    def _activate_purchases(self):
        for item in self.cart.line_items.filter(funding_type="POINTS"):
            bounty = item.bounty
            bounty.status = Bounty.BountyStatus.OPEN
            bounty.save()

    def _deactivate_purchases(self):
        for item in self.cart.line_items.filter(funding_type="POINTS"):
            bounty = item.bounty
            bounty.status = Bounty.BountyStatus.DRAFT
            bounty.save()

    def _activate_challenge(self, challenge):
        Challenge = apps.get_model("product_management", "Challenge")
        if challenge.status != Challenge.ChallengeStatus.ACTIVE:
            challenge.status = Challenge.ChallengeStatus.ACTIVE
            challenge.save()

    def _activate_competition(self, competition):
        Competition = apps.get_model("product_management", "Competition")
        if competition.status == Competition.CompetitionStatus.DRAFT:
            competition.status = Competition.CompetitionStatus.ACTIVE
            competition.save()
        # TODO: Add additional activation logic (e.g., setting start date, notifications)

    def _deactivate_challenge(self, challenge):
        Challenge = apps.get_model("product_management", "Challenge")
        if challenge.status == Challenge.ChallengeStatus.ACTIVE:
            challenge.status = Challenge.ChallengeStatus.DRAFT
            challenge.save()

    def _deactivate_competition(self, competition):
        Competition = apps.get_model("product_management", "Competition")
        if competition.status == Competition.CompetitionStatus.ACTIVE:
            competition.status = Competition.CompetitionStatus.DRAFT
            competition.save()
        # TODO: Add additional deactivation logic if needed


class PaymentStrategy(ABC):

    @abstractmethod
    def process_payment(self, organisation_wallet, amount, **kwargs):
        """
        Processes the payment and updates the OrganisationWalletTransaction.
        """
        pass

    @abstractmethod
    def validate_payment(self, **kwargs):
        """
        Validates payment details before processing.
        """
        pass


class PayPalPaymentStrategy(PaymentStrategy):

    def process_payment(self, organisation_wallet, amount_cents, **kwargs):
        # Simulate PayPal payment processing (replace with actual PayPal API integration)
        print(f"Processing PayPal payment of {amount_cents / 100:.2f} USD")

        OrganisationWalletTransaction = apps.get_model("commerce", "OrganisationWalletTransaction")

        # Update the OrganisationWalletTransaction
        OrganisationWalletTransaction.objects.create(
            wallet=organisation_wallet,
            amount_cents=amount_cents,
            transaction_type="Credit",
            payment_method="PayPal",
            transaction_id="PayPal-Transaction-ID",
        )

    def validate_payment(self, paypal_email, **kwargs):
        if not paypal_email:
            raise ValueError("PayPal email is required for PayPal payments.")
        return True


class USDTPaymentStrategy(PaymentStrategy):

    def process_payment(self, organisation_wallet, amount_cents, crypto_wallet_address, **kwargs):
        # Simulate USDT payment processing (replace with actual USDT blockchain integration)
        print(f"Processing USDT payment of {amount_cents / 100:.2f} USD to wallet {crypto_wallet_address}")

        OrganisationWalletTransaction = apps.get_model("commerce", "OrganisationWalletTransaction")
        # Update the OrganisationWalletTransaction
        OrganisationWalletTransaction.objects.create(
            wallet=organisation_wallet,
            amount_cents=amount_cents,
            transaction_type="Credit",
            payment_method="USDT",
            transaction_id="USDT-Transaction-Hash",
        )

    def validate_payment(self, crypto_wallet_address, **kwargs):
        if not crypto_wallet_address:
            raise ValueError("Crypto wallet address is required for USDT payments.")
        return True


class ContributorWithdrawalStrategy(ABC):
    @abstractmethod
    def process_withdrawal(self, contributor_wallet, amount_cents, **kwargs):
        """
        Processes the contributor withdrawal and updates the ContributorWalletTransaction.
        """
        pass

    @abstractmethod
    def validate_withdrawal(self, **kwargs):
        """
        Validates contributor withdrawal details before processing.
        """
        pass


class ContributorPayPalWithdrawalStrategy(ContributorWithdrawalStrategy):
    def process_withdrawal(self, contributor_wallet, amount_cents, **kwargs):
        print(f"Processing contributor PayPal withdrawal of ${amount_cents / 100:.2f}")

        ContributorWalletTransaction = apps.get_model("commerce", "ContributorWalletTransaction")
        ContributorWalletTransaction.objects.create(
            wallet=contributor_wallet,
            amount_cents=amount_cents,
            transaction_type="Debit",
            payment_method="PayPal",
            transaction_id="PayPal-Withdrawal-ID",
        )

    def validate_withdrawal(self, paypal_email, **kwargs):
        if not paypal_email:
            raise ValueError("PayPal email is required for contributor PayPal withdrawals.")
        return True


class ContributorUSDTWithdrawalStrategy(ContributorWithdrawalStrategy):
    def process_withdrawal(self, contributor_wallet, amount_cents, crypto_wallet_address, **kwargs):
        print(f"Processing contributor USDT withdrawal of ${amount_cents / 100:.2f} to wallet {crypto_wallet_address}")

        ContributorWalletTransaction = apps.get_model("commerce", "ContributorWalletTransaction")
        ContributorWalletTransaction.objects.create(
            wallet=contributor_wallet,
            amount_cents=amount_cents,
            transaction_type="Debit",
            payment_method="USDT",
            transaction_id="USDT-Withdrawal-Hash",
        )

    def validate_withdrawal(self, crypto_wallet_address, **kwargs):
        if not crypto_wallet_address:
            raise ValueError("Crypto wallet address is required for contributor USDT withdrawals.")
        return True

@receiver(post_save, sender=Cart)
def create_or_update_sales_order(sender, instance, created, **kwargs):
    instance.update_sales_order()





























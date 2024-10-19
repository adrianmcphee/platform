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


class Organisation(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    name = models.CharField(max_length=512, unique=True)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 country code")
    tax_id = models.CharField(max_length=50, blank=True, null=True, help_text="Tax Identification Number")

    def clean(self):
        if self.tax_id:
            self.tax_id = self.tax_id.upper().replace(" ", "")
            if not self.is_valid_tax_id():
                raise ValidationError("Invalid Tax Identification Number for the specified country.")

    def save(self, *args, **kwargs):
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

    def deduct_funds(self, amount_cents, description, related_order=None):
        if self.balance_usd_cents >= amount_cents:
            self.balance_usd_cents -= amount_cents
            self.save()
            OrganisationWalletTransaction.objects.create(
                wallet=self,
                amount_cents=amount_cents,
                transaction_type=OrganisationWalletTransaction.TransactionType.DEBIT,
                description=description,
                related_order=related_order,
            )
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
    transaction_id = models.CharField(max_length=255, null=True, blank=True)  # External transaction ID (e.g., PayPal or crypto transaction hash)

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

class ContributorWallet(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField('talent.Person', on_delete=models.CASCADE, related_name="wallet")
    balance_usd_in_cents = models.IntegerField(default=0)  # Balance stored as cents for precision

    def __str__(self):
        # Format the balance as dollars for readability
        return f"Wallet for {self.person.full_name} - USD: ${self.balance_usd_in_cents / 100:.2f}"
    
class ContributorPointAccount(TimeStampMixin):
    id = Base58UUIDv5Field(primary_key=True)
    person = models.OneToOneField('talent.Person', on_delete=models.CASCADE, related_name="point_account")
    balance_points = models.IntegerField(default=0)  # Balance stored as integer points

    def __str__(self):
        return f"Point Account for {self.person.full_name} - Points: {self.balance_points}"


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
    cart = models.ForeignKey('Cart', related_name='items', on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_cents = models.IntegerField()
    unit_price_points = models.PositiveIntegerField(default=0)
    bounty = models.ForeignKey('product_management.Bounty', on_delete=models.SET_NULL, null=True, blank=True)
    related_bounty_bid = models.ForeignKey(BountyBid, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_price_cents(self):
        if self.quantity is None or self.unit_price_cents is None:
            return 0
        return self.quantity * self.unit_price_cents

    @property
    def total_price_points(self):
        if self.quantity is None or self.unit_price_points is None:
            return 0
        return self.quantity * self.unit_price_points

    def __str__(self):
        return f"{self.get_item_type_display()} for Cart {self.cart.id}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.related_bounty_bid:
                raise ValidationError("Adjustment line items must be associated with a bounty bid.")
        elif self.related_bounty_bid:
            raise ValidationError("Only adjustment line items can be associated with a bounty bid.")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('cart', 'bounty')

class Cart(TimeStampMixin):
    class CartStatus(models.TextChoices):
        OPEN = "Open", "Open"
        CHECKOUT = "Checkout", "Checkout"
        COMPLETED = "Completed", "Completed"
        ABANDONED = "Abandoned", "Abandoned"

    id = Base58UUIDv5Field(primary_key=True)
    person = models.ForeignKey("talent.Person", on_delete=models.SET_NULL, null=True, blank=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=CartStatus.choices, default=CartStatus.OPEN)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2 country code of the user")

    def __str__(self):
        return f"Cart {self.id} - ({self.status})"

    def calculate_platform_fee(self):
        PlatformFeeConfiguration = apps.get_model("commerce", "PlatformFeeConfiguration")
        SalesOrderLineItem = apps.get_model("commerce", "SalesOrderLineItem")

        usd_items = self.sales_order.line_items.filter(item_type=SalesOrderLineItem.ItemType.BOUNTY)
        if usd_items.exists():
            config = PlatformFeeConfiguration.get_active_configuration()
            if config:
                total_usd_cents = usd_items.aggregate(total=Sum("unit_price_cents"))["total"] or 0
                fee_amount_cents = int(total_usd_cents * config.percentage_decimal)

                # Create or update the platform fee line item
                SalesOrderLineItem.objects.update_or_create(
                    sales_order=self.sales_order,
                    item_type=SalesOrderLineItem.ItemType.PLATFORM_FEE,
                    defaults={
                        "unit_price_cents": fee_amount_cents,
                        "fee_rate": config.percentage_decimal,
                        "quantity": 1,
                    },
                )
                return fee_amount_cents, config.percentage_decimal
        else:
            # Remove platform fee if no USD items
            self.sales_order.line_items.filter(item_type=SalesOrderLineItem.ItemType.PLATFORM_FEE).delete()
        return 0, 0

    def calculate_sales_tax(self):
        SalesOrderLineItem = apps.get_model("commerce", "SalesOrderLineItem")

        taxable_amount = self.total_usd_cents()

        if self.organisation:
            tax_rate = self.get_organisation_tax_rate()
        elif self.is_user_in_europe():
            tax_rate = self.get_default_european_tax_rate()
        else:
            tax_rate = 0

        tax_amount = int(taxable_amount * tax_rate)

        if tax_amount > 0:
            SalesOrderLineItem.objects.update_or_create(
                sales_order=self.sales_order,
                item_type=SalesOrderLineItem.ItemType.SALES_TAX,
                defaults={"unit_price_cents": tax_amount, "tax_rate": tax_rate, "quantity": 1},
            )
        else:
            self.sales_order.line_items.filter(item_type=SalesOrderLineItem.ItemType.SALES_TAX).delete()

        return tax_amount, tax_rate

    def total_usd_cents(self):
        SalesOrderLineItem = apps.get_model("commerce", "SalesOrderLineItem")
        return (
            self.sales_order.line_items.filter(item_type=SalesOrderLineItem.ItemType.BOUNTY).aggregate(
                total=Sum("unit_price_cents")
            )["total"]
            or 0
        )

    def get_organisation_tax_rate(self):
        # Placeholder implementation
        return 0.2  # 20% tax rate as an example

    def get_default_european_tax_rate(self):
        # Placeholder implementation
        return 0.21  # 21% tax rate as an example
    
    def add_adjustment(self, bounty_bid, amount_cents, is_increase=True):
        item_type = CartLineItem.ItemType.INCREASE_ADJUSTMENT if is_increase else CartLineItem.ItemType.DECREASE_ADJUSTMENT
        adjustment = CartLineItem.objects.create(
            cart=self,
            item_type=item_type,
            quantity=1,
            unit_price_cents=abs(amount_cents),
            related_bounty_bid=bounty_bid
        )
        return adjustment

    def remove_adjustment(self, bounty_bid):
        self.items.filter(
            item_type__in=[CartLineItem.ItemType.INCREASE_ADJUSTMENT, CartLineItem.ItemType.DECREASE_ADJUSTMENT],
            related_bounty_bid=bounty_bid
        ).delete()

    @property
    def total_amount_cents(self):
        total = sum(item.total_price_cents for item in self.items.exclude(
            item_type=CartLineItem.ItemType.DECREASE_ADJUSTMENT
        ))
        deductions = sum(item.total_price_cents for item in self.items.filter(
            item_type=CartLineItem.ItemType.DECREASE_ADJUSTMENT
        ))
        return total - deductions

    def is_user_in_europe(self):
        european_countries = [
            "AT",
            "BE",
            "BG",
            "HR",
            "CY",
            "CZ",
            "DK",
            "EE",
            "FI",
            "FR",
            "DE",
            "GR",
            "HU",
            "IE",
            "IT",
            "LV",
            "LT",
            "LU",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SK",
            "SI",
            "ES",
            "SE",
        ]
        return self.user_country in european_countries

    def total_points(self):
        return sum(item.points for item in self.items.all() if item.bounty.reward_type == "Points")

    def total_usd_cents(self):
        return sum(item.funding_amount for item in self.items.all() if item.bounty.reward_type == "USD")

    @property
    def total_amount_cents(self):
        total = self.items.aggregate(total=Sum("funding_amount"))["total"] or 0
        platform_fee = getattr(self.platform_fee_item, "amount_cents", 0) if hasattr(self, "platform_fee_item") else 0
        sales_tax = getattr(self.sales_tax_item, "amount_cents", 0) if hasattr(self, "sales_tax_item") else 0
        return total + platform_fee + sales_tax

    @property
    def total_amount(self):
        return self.total_amount_cents / 100


class SalesOrder(TimeStampMixin):
    class OrderStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        PAYMENT_PROCESSING = "Payment Processing", "Payment Processing"
        COMPLETED = "Completed", "Completed"
        PAYMENT_FAILED = "Payment Failed", "Payment Failed"
        REFUNDED = "Refunded", "Refunded"

    id = Base58UUIDv5Field(primary_key=True)
    cart = models.OneToOneField(Cart, on_delete=models.PROTECT, related_name="sales_order")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total_usd_cents_excluding_fees_and_taxes = models.PositiveIntegerField(default=0)
    total_fees_usd_cents = models.PositiveIntegerField(default=0)
    total_taxes_usd_cents = models.PositiveIntegerField(default=0)
    total_usd_cents_including_fees_and_taxes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Sales Order {self.id} for Cart {self.cart.id}"

    def save(self, *args, **kwargs):
        self.total_usd_cents_including_fees_and_taxes = (
            self.total_usd_cents_excluding_fees_and_taxes +
            self.total_fees_usd_cents +
            self.total_taxes_usd_cents
        )
        super().save(*args, **kwargs)

    def create_line_items(self):
        for cart_item in self.cart.items.filter(funding_type="USD"):
            SalesOrderLineItem.objects.create(
                sales_order=self,
                item_type=SalesOrderLineItem.ItemType.BOUNTY,
                bounty=cart_item.bounty,
                quantity=1,
                unit_price_cents=cart_item.funding_amount,
            )

        platform_fee = getattr(self.cart, "platform_fee_item", None)
        if platform_fee:
            SalesOrderLineItem.objects.create(
                sales_order=self,
                item_type=SalesOrderLineItem.ItemType.PLATFORM_FEE,
                quantity=1,
                unit_price_cents=platform_fee.amount_cents,
                fee_rate=platform_fee.fee_rate,
            )

        sales_tax = getattr(self.cart, "sales_tax_item", None)
        if sales_tax:
            SalesOrderLineItem.objects.create(
                sales_order=self,
                item_type=SalesOrderLineItem.ItemType.SALES_TAX,
                quantity=1,
                unit_price_cents=sales_tax.amount_cents,
                tax_rate=sales_tax.tax_rate,
            )

    def update_totals(self):
        self.total_usd_cents = (
            self.line_items.aggregate(total=Sum("unit_price_cents", field="unit_price_cents * quantity"))["total"] or 0
        )

    @transaction.atomic
    def process_payment(self):
        if self.status != self.OrderStatus.PENDING:
            return False

        self.status = self.OrderStatus.PAYMENT_PROCESSING
        self.save()

        try:
            if self.total_usd_cents > 0 and not self._process_usd_payment():
                raise ValueError("USD payment failed")

            self.status = self.OrderStatus.COMPLETED
            self.save()
            self._activate_purchases()
            self.cart.status = Cart.CartStatus.COMPLETED
            self.cart.save()
            return True

        except Exception as e:
            self.status = self.OrderStatus.PAYMENT_FAILED
            self.save()
            return False

    def _process_usd_payment(self):
        # Implement USD payment processing logic here
        # Return True if successful, False otherwise
        return True  # Placeholder implementation

    def _activate_purchases(self):
        for item in self.cart.items.all():
            bounty = item.bounty
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


class SalesOrderLineItem(PolymorphicModel, TimeStampMixin):
    class ItemType(models.TextChoices):
        BOUNTY = "BOUNTY", "Bounty"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee"
        SALES_TAX = "SALES_TAX", "Sales Tax"
        INCREASE_ADJUSTMENT = "INCREASE_ADJUSTMENT", "Increase Adjustment"
        DECREASE_ADJUSTMENT = "DECREASE_ADJUSTMENT", "Decrease Adjustment"

    id = Base58UUIDv5Field(primary_key=True)
    sales_order = models.ForeignKey(SalesOrder, related_name='line_items', on_delete=models.CASCADE)
    item_type = models.CharField(max_length=25, choices=ItemType.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_cents = models.IntegerField(help_text="Price in cents for USD items, or number of points for Point items")
    bounty = models.ForeignKey('product_management.Bounty', on_delete=models.SET_NULL, null=True, blank=True)
    fee_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    related_bounty_bid = models.ForeignKey('talent.BountyBid', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_price_cents(self):
        if self.quantity is None or self.unit_price_cents is None:
            return 0
        return self.quantity * self.unit_price_cents

    def __str__(self):
        if self.item_type == 'BOUNTY':
            price = f"{self.unit_price_cents/100:.2f} USD" if self.bounty.reward_type == 'USD' else f"{self.unit_price_cents} Points"
        else:
            price = f"{self.unit_price_cents/100:.2f} USD"
        return f"{self.item_type} - {price}"

    def clean(self):
        if self.item_type in [self.ItemType.INCREASE_ADJUSTMENT, self.ItemType.DECREASE_ADJUSTMENT]:
            if not self.sales_order.parent_sales_order:
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

        self.product_account.add_points(self.total_points)
        self.status = "REFUNDED"
        self.save()
        self._create_refund_transactions()
        self._deactivate_purchases()
        return True

    def _create_point_transactions(self):
        for item in self.cart.items.filter(funding_type="Points"):
            PointTransaction.objects.create(
                product_account=self.product_account,
                amount=item.funding_amount,
                transaction_type="USE",
                description=f"Points used for Bounty: {item.bounty.title}",
            )

    def _create_refund_transactions(self):
        for item in self.cart.items.filter(funding_type="Points"):
            PointTransaction.objects.create(
                product_account=self.product_account,
                amount=item.funding_amount,
                transaction_type="REFUND",
                description=f"Points refunded for Bounty: {item.bounty.title}",
            )

    def _activate_purchases(self):
        for item in self.cart.items.filter(funding_type="Points"):
            bounty = item.bounty
            if bounty.challenge:
                self._activate_challenge(bounty.challenge)
            elif bounty.competition:
                self._activate_competition(bounty.competition)

    def _deactivate_purchases(self):
        for item in self.cart.items.filter(funding_type="Points"):
            bounty = item.bounty
            if bounty.challenge:
                self._deactivate_challenge(bounty.challenge)
            elif bounty.competition:
                self._deactivate_competition(bounty.competition)

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

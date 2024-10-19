# Generated by Django 5.1.1 on 2024-10-19 12:32

import apps.common.fields
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Open", "Open"),
                            ("Checkout", "Checkout"),
                            ("Completed", "Completed"),
                            ("Abandoned", "Abandoned"),
                        ],
                        default="Open",
                        max_length=20,
                    ),
                ),
                ("country", models.CharField(help_text="ISO 3166-1 alpha-2 country code of the user", max_length=2)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CartLineItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "item_type",
                    models.CharField(
                        choices=[
                            ("BOUNTY", "Bounty"),
                            ("PLATFORM_FEE", "Platform Fee"),
                            ("SALES_TAX", "Sales Tax"),
                            ("INCREASE_ADJUSTMENT", "Increase Adjustment"),
                            ("DECREASE_ADJUSTMENT", "Decrease Adjustment"),
                        ],
                        max_length=25,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price_cents", models.IntegerField()),
                ("unit_price_points", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="ContributorPointAccount",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("balance_points", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ContributorPointTransaction",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_points", models.IntegerField()),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[("Earn", "Earn"), ("Use", "Use"), ("Transfer", "Transfer"), ("Refund", "Refund")],
                        max_length=10,
                    ),
                ),
                ("description", models.TextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ContributorWallet",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("balance_usd_in_cents", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ContributorWalletTransaction",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_cents", models.IntegerField()),
                (
                    "transaction_type",
                    models.CharField(choices=[("Credit", "Credit"), ("Debit", "Debit")], max_length=10),
                ),
                ("description", models.TextField()),
                (
                    "payment_method",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PayPal", "PayPal"),
                            ("USDT", "USDT"),
                            ("CreditCard", "Credit Card"),
                            ("ContributorWallet", "Contributor Wallet"),
                        ],
                        max_length=20,
                        null=True,
                    ),
                ),
                ("transaction_id", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Organisation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=512, unique=True)),
                ("country", models.CharField(help_text="ISO 3166-1 alpha-2 country code", max_length=2)),
                (
                    "tax_id",
                    models.CharField(blank=True, help_text="Tax Identification Number", max_length=50, null=True),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationPointAccount",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("balance", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationPointGrant",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount", models.PositiveIntegerField()),
                ("rationale", models.TextField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationPointGrantRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_points", models.PositiveIntegerField()),
                ("rationale", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
                        default="Pending",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationWallet",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("balance_usd_cents", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationWalletTransaction",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_cents", models.IntegerField()),
                (
                    "transaction_type",
                    models.CharField(choices=[("Credit", "Credit"), ("Debit", "Debit")], max_length=10),
                ),
                ("description", models.TextField()),
                (
                    "payment_method",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PayPal", "PayPal"),
                            ("USDT", "USDT"),
                            ("CreditCard", "Credit Card"),
                            ("OrganisationWallet", "Organisation Wallet"),
                        ],
                        max_length=20,
                        null=True,
                    ),
                ),
                ("transaction_id", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PlatformFeeConfiguration",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "percentage",
                    models.PositiveIntegerField(
                        default=10,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(100),
                        ],
                    ),
                ),
                ("applies_from_date", models.DateTimeField()),
            ],
            options={
                "get_latest_by": "applies_from_date",
            },
        ),
        migrations.CreateModel(
            name="PointOrder",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("total_points", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("COMPLETED", "Completed"), ("REFUNDED", "Refunded")],
                        default="PENDING",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PointTransaction",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount", models.PositiveIntegerField()),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[("GRANT", "Grant"), ("USE", "Use"), ("REFUND", "Refund"), ("TRANSFER", "Transfer")],
                        max_length=10,
                    ),
                ),
                ("description", models.TextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProductPointAccount",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("balance", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProductPointRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_points", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")],
                        default="Pending",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SalesOrder",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Payment Processing", "Payment Processing"),
                            ("Completed", "Completed"),
                            ("Payment Failed", "Payment Failed"),
                            ("Refunded", "Refunded"),
                        ],
                        default="Pending",
                        max_length=20,
                    ),
                ),
                ("total_usd_cents_excluding_fees_and_taxes", models.PositiveIntegerField(default=0)),
                ("total_fees_usd_cents", models.PositiveIntegerField(default=0)),
                ("total_taxes_usd_cents", models.PositiveIntegerField(default=0)),
                ("total_usd_cents_including_fees_and_taxes", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SalesOrderLineItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "item_type",
                    models.CharField(
                        choices=[
                            ("BOUNTY", "Bounty"),
                            ("PLATFORM_FEE", "Platform Fee"),
                            ("SALES_TAX", "Sales Tax"),
                            ("INCREASE_ADJUSTMENT", "Increase Adjustment"),
                            ("DECREASE_ADJUSTMENT", "Decrease Adjustment"),
                        ],
                        max_length=25,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "unit_price_cents",
                    models.IntegerField(help_text="Price in cents for USD items, or number of points for Point items"),
                ),
                ("fee_rate", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ("tax_rate", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="WithdrawalRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount_cents", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Failed", "Failed")],
                        default="Pending",
                        max_length=20,
                    ),
                ),
                ("payment_method", models.CharField(choices=[("PayPal", "PayPal"), ("USDT", "USDT")], max_length=20)),
                ("transaction_id", models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]

# Generated by Django 5.1.1 on 2024-10-09 22:28

import django.core.validators
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                (
                    "user_country",
                    models.CharField(help_text="ISO 3166-1 alpha-2 country code of the user", max_length=2),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Organisation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
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
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("balance", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationPointGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("amount", models.PositiveIntegerField()),
                ("rationale", models.TextField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationWallet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("balance_usd_cents", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OrganisationWalletTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("amount_cents", models.IntegerField()),
                (
                    "transaction_type",
                    models.CharField(choices=[("Credit", "Credit"), ("Debit", "Debit")], max_length=10),
                ),
                ("description", models.TextField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PlatformFeeConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("balance", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SalesOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                ("total_usd_cents", models.PositiveIntegerField(default=0)),
                ("fee_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SalesOrderLineItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False)),
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
                        max_length=20,
                    ),
                ),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price_cents", models.IntegerField()),
                ("unit_price_tax_cents", models.PositiveIntegerField(default=0)),
                ("unit_price_tax_label", models.CharField(blank=True, max_length=255, null=True)),
                ("fee_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("tax_rate", models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
    ]

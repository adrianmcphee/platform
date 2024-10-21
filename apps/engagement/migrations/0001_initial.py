# Generated by Django 5.1.1 on 2024-10-21 20:34

import apps.common.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailNotification",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(editable=False, primary_key=True, serialize=False)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("BOUNTY_CREATED", "Bounty Created"),
                            ("BOUNTY_CLAIMED", "Bounty Claimed"),
                            ("BOUNTY_COMPLETED", "Bounty Completed"),
                            ("BOUNTY_AWARDED", "Bounty Awarded"),
                            ("CHALLENGE_STARTED", "Challenge Started"),
                            ("CHALLENGE_COMPLETED", "Challenge Completed"),
                            ("COMPETITION_OPENED", "Competition Opened"),
                            ("COMPETITION_CLOSED", "Competition Closed"),
                            ("ENTRY_SUBMITTED", "Entry Submitted"),
                            ("WINNER_ANNOUNCED", "Winner Announced"),
                            ("ORDER_PLACED", "Order Placed"),
                            ("PAYMENT_RECEIVED", "Payment Received"),
                            ("FUNDS_ADDED", "Funds Added to Wallet"),
                            ("POINTS_TRANSFERRED", "Points Transferred"),
                            ("PRODUCT_MADE_PUBLIC", "Product Made Public"),
                        ],
                        max_length=30,
                    ),
                ),
                ("permitted_params", models.CharField(max_length=500)),
                ("title", models.CharField(max_length=400)),
                ("template", models.CharField(max_length=4000)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]

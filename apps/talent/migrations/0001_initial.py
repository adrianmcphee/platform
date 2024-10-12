# Generated by Django 5.1.1 on 2024-10-12 17:24

import apps.common.fields
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("product_management", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BountyBid",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("amount", models.PositiveIntegerField()),
                ("expected_finish_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Accepted", "Accepted"),
                            ("Rejected", "Rejected"),
                            ("Withdrawn", "Withdrawn"),
                        ],
                        default="Pending",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField(blank=True, null=True)),
                (
                    "bounty",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bids",
                        to="product_management.bounty",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="BountyClaim",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("Active", "Active"), ("Completed", "Completed"), ("Failed", "Failed")],
                        default="Active",
                        max_length=20,
                    ),
                ),
                (
                    "accepted_bid",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resulting_claim",
                        to="talent.bountybid",
                    ),
                ),
                (
                    "bounty",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="product_management.bounty"),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="Expertise",
            fields=[
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("selectable", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=100)),
                ("fa_icon", models.CharField(max_length=100)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expertise_children",
                        to="talent.expertise",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("full_name", models.CharField(max_length=256)),
                ("preferred_name", models.CharField(max_length=128)),
                ("photo", models.ImageField(blank=True, null=True, upload_to="avatars/")),
                ("headline", models.TextField()),
                ("overview", models.TextField(blank=True)),
                ("location", models.TextField(blank=True, max_length=128, null=True)),
                ("send_me_bounties", models.BooleanField(default=True)),
                ("current_position", models.CharField(blank=True, max_length=256, null=True)),
                ("twitter_link", models.URLField(blank=True, default="", null=True)),
                ("linkedin_link", models.URLField(blank=True, null=True)),
                ("github_link", models.URLField(blank=True, null=True)),
                ("website_link", models.URLField(blank=True, null=True)),
                ("completed_profile", models.BooleanField(default=False)),
                ("points", models.PositiveIntegerField(default=0)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="person", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "People",
                "db_table": "talent_person",
            },
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField()),
                (
                    "stars",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                    ),
                ),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback_provider",
                        to="talent.person",
                    ),
                ),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback_recipient",
                        to="talent.person",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BountyDeliveryAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("New", "New"),
                            ("Approved", "Approved"),
                            ("Rejected", "Rejected"),
                            ("Cancelled", "Cancelled"),
                        ],
                        default="New",
                    ),
                ),
                ("delivery_message", models.CharField(default=None, max_length=2000)),
                ("review_message", models.CharField(blank=True, max_length=2000, null=True)),
                ("attachments", models.ManyToManyField(blank=True, to="product_management.fileattachment")),
                (
                    "bounty_claim",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="delivery_attempts",
                        to="talent.bountyclaim",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_deliveries",
                        to="talent.person",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddField(
            model_name="bountyclaim",
            name="person",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="talent.person"),
        ),
        migrations.AddField(
            model_name="bountybid",
            name="person",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="bounty_bids", to="talent.person"
            ),
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("active", models.BooleanField(db_index=True, default=False)),
                ("selectable", models.BooleanField(default=False)),
                ("display_boost_factor", models.PositiveSmallIntegerField(default=1)),
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="talent.skill",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PersonSkill",
            fields=[
                ("id", apps.common.fields.Base58UUIDv5Field(primary_key=True, serialize=False)),
                ("expertise", models.ManyToManyField(to="talent.expertise")),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="skills", to="talent.person"
                    ),
                ),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="talent.skill")),
            ],
        ),
        migrations.AddField(
            model_name="expertise",
            name="skill",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="skill_expertise",
                to="talent.skill",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="bountyclaim",
            unique_together={("bounty", "person")},
        ),
        migrations.AlterUniqueTogether(
            name="bountybid",
            unique_together={("bounty", "person")},
        ),
    ]

# Generated by Django 5.1.1 on 2024-10-26 19:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("product_management", "0002_initial"),
        ("security", "0001_initial"),
        ("talent", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisationpersonroleassignment",
            name="person",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="talent.person"),
        ),
        migrations.AddField(
            model_name="productroleassignment",
            name="person",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="talent.person"),
        ),
        migrations.AddField(
            model_name="productroleassignment",
            name="product",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="product_management.product"),
        ),
        migrations.AddField(
            model_name="signinattempt",
            name="user",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="signuprequest",
            name="user",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterUniqueTogether(
            name="organisationpersonroleassignment",
            unique_together={("person", "organisation")},
        ),
    ]

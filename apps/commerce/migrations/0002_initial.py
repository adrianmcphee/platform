# Generated by Django 5.1.1 on 2024-10-12 17:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("commerce", "0001_initial"),
        ("product_management", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cart",
            name="product",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="product_management.product"),
        ),
    ]

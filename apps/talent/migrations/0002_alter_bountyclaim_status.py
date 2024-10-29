# Generated by Django 5.1.1 on 2024-10-29 10:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("talent", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bountyclaim",
            name="status",
            field=models.CharField(
                choices=[
                    ("Active", "Active"),
                    ("Completed", "Completed"),
                    ("Failed", "Failed"),
                    ("Cancelled", "Cancelled"),
                ],
                default="Active",
                max_length=20,
            ),
        ),
    ]
# Generated by Django 4.2.2 on 2023-08-21 12:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("talent", "0004_alter_person_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="skill",
            name="display_boost_factor",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]

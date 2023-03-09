# Generated by Django 3.2.2 on 2023-03-08 22:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="claimed",
            field=models.BooleanField(
                default=True,
                help_text="Designates whether this user has been claimed.",
                verbose_name="claimed",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="valid_email",
            field=models.BooleanField(
                default=True,
                help_text="Designates whether this user's email address is valid, to the best of our knowledge.",
                verbose_name="valid_email",
            ),
        ),
    ]
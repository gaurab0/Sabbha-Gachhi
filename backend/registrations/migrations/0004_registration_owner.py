import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("registrations", "0003_matchattemptlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registrations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

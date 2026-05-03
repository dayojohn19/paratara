from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0062_requestpagesummary"),
    ]

    operations = [
        migrations.AddField(
            model_name="requestpagesummary",
            name="city",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="requestpagesummary",
            name="region",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]

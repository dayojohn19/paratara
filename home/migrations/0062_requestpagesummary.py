from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0061_alter_allschedules_detailscontact"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestPageSummary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requesting_ip", models.GenericIPAddressField(unique=True)),
                ("ip_location_json", models.JSONField(blank=True, null=True)),
                ("pages_json", models.JSONField(blank=True, default=dict)),
                ("total_requests", models.PositiveIntegerField(default=0)),
                ("unique_pages", models.PositiveIntegerField(default=0)),
                ("earliest_timesmtamp", models.DateTimeField(blank=True, null=True)),
                ("latest_timesmtamp", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]

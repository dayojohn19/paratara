from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0004_subscriptionplan_paypalproduct_and_m2m"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="PayPalSubscription",
            new_name="PayPalCustomerSubscription",
        ),
    ]

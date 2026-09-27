from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resortManagement', '0011_remove_resortbookingpayment_payment_button_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='resortbookingpayment',
            name='paypal_order_id',
            field=models.CharField(blank=True, max_length=120, null=True, unique=True),
        ),
    ]
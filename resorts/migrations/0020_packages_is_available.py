from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resorts', '0019_inactiveresortitem_accepts_cash_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='packages',
            name='is_available',
            field=models.BooleanField(default=True),
        ),
    ]

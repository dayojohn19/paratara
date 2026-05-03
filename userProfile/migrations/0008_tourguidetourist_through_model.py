# Generated manually for TourGuideTourist through model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('userProfile', '0007_tourguide_primary_place'),
    ]

    operations = [
        migrations.CreateModel(
            name='TourGuideTourist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True, help_text='When this tourist started being guided')),
                ('tour_guide', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tourist_assignments', to='userProfile.tourguide')),
                ('tourist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tour_guide_assignments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('tour_guide', 'tourist')},
            },
        ),
        migrations.RemoveField(
            model_name='tourguide',
            name='guided_tourists',
        ),
        migrations.AddField(
            model_name='tourguide',
            name='guided_tourists',
            field=models.ManyToManyField(blank=True, help_text='Tourists currently being guided by this tour guide', related_name='guided_by', through='userProfile.TourGuideTourist', to=settings.AUTH_USER_MODEL),
        ),
    ]
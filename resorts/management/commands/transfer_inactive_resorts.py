from django.core.management.base import BaseCommand
from django.utils import timezone
from resorts.models import resortItem, InactiveResortItem
from datetime import timedelta

class Command(BaseCommand):
    help = 'Transfer inactive resortItem objects to InactiveResortItem if not visited/updated in X days.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=90, help='Number of days of inactivity before transfer (default: 90)')

    def handle(self, *args, **options):
        days = options['days']
        threshold = timezone.now() - timedelta(days=days)
        count = 0
        for resort in resortItem.objects.all():
            # Use last_visited if present, else fallback to timestamp
            last_time = resort.last_visited if resort.last_visited else resort.timestamp
            if last_time < threshold:
                # Create InactiveResortItem with identical fields
                inactive = InactiveResortItem.objects.create(
                    resortQRLink=resort.resortQRLink,
                    websiteURL=resort.websiteURL,
                    resort_ID=resort.resort_ID,
                    name=resort.name,
                    RealName=resort.RealName,
                    address=resort.address,
                    place=resort.place,
                    contactNumber=resort.contactNumber,
                    contactEmail=resort.contactEmail,
                    whatsappNumber=resort.whatsappNumber,
                    open_hours=getattr(resort, 'open_hours', '') or '',
                    promotionalVideo=resort.promotionalVideo,
                    virtualpicture=resort.virtualpicture,
                    headerImage=resort.headerImage,
                    latitude=resort.latitude,
                    longitude=resort.longitude,
                    reviews=resort.reviews,
                    description=resort.description,
                    province=resort.province,
                    slug=resort.slug,
                    last_visited=resort.last_visited,
                )
                # Copy M2M fields
                inactive.save()
                inactive.resortGallery.set(resort.resortGallery.all())
                inactive.resortAccomodations.set(resort.resortAccomodations.all())
                inactive.resortSchedules.set(resort.resortSchedules.all())
                inactive.adminManager.set(resort.adminManager.all())
                if resort.registeredBy:
                    inactive.registeredBy = resort.registeredBy
                inactive.resortActivities.set(resort.resortActivities.all())
                inactive.resortTour.set(resort.resortTour.all())
                inactive.resortFood.set(resort.resortFood.all())
                inactive.save()
                resort.delete()
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Transferred resort: {resort.RealName}'))
        self.stdout.write(self.style.SUCCESS(f'Total transferred: {count}'))

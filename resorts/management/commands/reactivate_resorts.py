from django.core.management.base import BaseCommand
from resorts.models import resortItem, InactiveResortItem

class Command(BaseCommand):
    help = 'Reactivate resorts: move from InactiveResortItem back to resortItem.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, nargs='*', help='IDs of InactiveResortItem(s) to reactivate. If omitted, all will be reactivated.')

    def handle(self, *args, **options):
        ids = options['id']
        if ids:
            resorts = InactiveResortItem.objects.filter(id__in=ids)
        else:
            resorts = InactiveResortItem.objects.all()
        count = 0
        for inactive in resorts:
            active = resortItem.objects.create(
                resortQRLink=inactive.resortQRLink,
                websiteURL=inactive.websiteURL,
                resort_ID=inactive.resort_ID,
                name=inactive.name,
                RealName=inactive.RealName,
                address=inactive.address,
                place=inactive.place,
                contactNumber=inactive.contactNumber,
                contactEmail=inactive.contactEmail,
                whatsappNumber=inactive.whatsappNumber,
                open_hours=getattr(inactive, 'open_hours', '') or '',
                promotionalVideo=inactive.promotionalVideo,
                virtualpicture=inactive.virtualpicture,
                headerImage=inactive.headerImage,
                latitude=inactive.latitude,
                longitude=inactive.longitude,
                reviews=inactive.reviews,
                description=inactive.description,
                province=inactive.province,
                slug=inactive.slug,
                last_visited=inactive.last_visited,
            )
            active.save()
            active.resortGallery.set(inactive.resortGallery.all())
            active.resortAccomodations.set(inactive.resortAccomodations.all())
            active.resortSchedules.set(inactive.resortSchedules.all())
            active.adminManager.set(inactive.adminManager.all())
            if inactive.registeredBy:
                active.registeredBy = inactive.registeredBy
            active.resortActivities.set(inactive.resortActivities.all())
            active.resortTour.set(inactive.resortTour.all())
            active.resortFood.set(inactive.resortFood.all())
            active.save()
            inactive.delete()
            count += 1
            self.stdout.write(self.style.SUCCESS(f'Reactivated resort: {active.RealName}'))
        self.stdout.write(self.style.SUCCESS(f'Total reactivated: {count}'))

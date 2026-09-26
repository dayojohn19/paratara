from django.core.management.base import BaseCommand

from resortManagement.models import ResortBookingPayment


class Command(BaseCommand):
    help = 'Release room booking holds for unpaid PayMongo checkouts older than 30 minutes.'

    def handle(self, *args, **options):
        expired_count = ResortBookingPayment.expire_stale_pending()
        self.stdout.write(self.style.SUCCESS(f'Expired {expired_count} pending booking hold(s).'))
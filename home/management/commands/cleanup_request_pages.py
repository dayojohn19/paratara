from django.core.management.base import BaseCommand
from django.db.models import Count
from home.models import RequestPage


class Command(BaseCommand):
    help = 'Report RequestPage IPs with more than 30 requests without deleting rows'

    def handle(self, *args, **options):
        # Group by requesting_ip and count occurrences
        ip_counts = RequestPage.objects.values('requesting_ip').annotate(
            count=Count('requesting_ip')
        ).filter(count__gt=30)

        if not ip_counts.exists():
            self.stdout.write(
                self.style.WARNING('No IPs found with more than 30 requests.')
            )
            return

        for ip_data in ip_counts:
            ip_address = ip_data['requesting_ip']
            count = ip_data['count']

            self.stdout.write(
                self.style.WARNING(
                    f"Found IP with {count} requests: {ip_address}. No RequestPage rows deleted."
                )
            )

        self.stdout.write(
            self.style.SUCCESS("\nRequestPage cleanup is disabled so raw visit history is preserved.")
        )

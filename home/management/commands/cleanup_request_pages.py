from django.core.management.base import BaseCommand
from django.db.models import Count
from home.models import RequestPage


class Command(BaseCommand):
    help = 'Delete RequestPage objects where an IP has more than 30 requests'

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

        total_deleted = 0
        for ip_data in ip_counts:
            ip_address = ip_data['requesting_ip']
            count = ip_data['count']

            # Delete all RequestPage objects for this IP
            deleted_count, _ = RequestPage.objects.filter(
                requesting_ip=ip_address
            ).delete()

            total_deleted += deleted_count
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Deleted {deleted_count} requests from IP: {ip_address} (had {count} requests)"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Total deleted: {total_deleted} RequestPage objects")
        )

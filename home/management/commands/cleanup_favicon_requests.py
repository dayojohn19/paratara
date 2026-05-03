from django.core.management.base import BaseCommand
from home.models import RequestPage


class Command(BaseCommand):
    help = 'Delete RequestPage objects with page_name containing /favicon.ico'

    def handle(self, *args, **options):
        # Find all RequestPage objects where page_name is like '/favicon.ico'
        favicon_requests = RequestPage.objects.filter(page_name__icontains='/favicon.ico')

        if not favicon_requests.exists():
            self.stdout.write(
                self.style.WARNING('No RequestPage objects found with "/favicon.ico" in page_name.')
            )
            return

        count = favicon_requests.count()
        self.stdout.write(f"Found {count} RequestPage object(s) with '/favicon.ico' in page_name")
        self.stdout.write("-" * 80)

        # Display the requests before deletion
        for request in favicon_requests:
            self.stdout.write(
                f"  • IP: {request.requesting_ip} | Page: {request.page_name} | Time: {request.readable_last_request()}"
            )

        self.stdout.write("-" * 80)

        # Delete them
        deleted_count, _ = favicon_requests.delete()

        self.stdout.write(
            self.style.SUCCESS(f"✓ Successfully deleted {deleted_count} favicon requests")
        )

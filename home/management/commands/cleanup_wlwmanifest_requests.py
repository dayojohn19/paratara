from django.core.management.base import BaseCommand
from home.models import RequestPage


class Command(BaseCommand):
    help = 'Delete RequestPage objects with page_name containing wlwmanifest.xml'

    def handle(self, *args, **options):
        # Find all RequestPage objects where page_name is like 'wlwmanifest.xml'
        manifest_requests = RequestPage.objects.filter(page_name__icontains='wlwmanifest.xml')

        if not manifest_requests.exists():
            self.stdout.write(
                self.style.WARNING('No RequestPage objects found with "wlwmanifest.xml" in page_name.')
            )
            return

        count = manifest_requests.count()
        self.stdout.write(f"Found {count} RequestPage object(s) with 'wlwmanifest.xml' in page_name")
        self.stdout.write("-" * 80)

        # Display the requests before deletion
        for request in manifest_requests:
            self.stdout.write(
                f"  • IP: {request.requesting_ip} | Page: {request.page_name} | Time: {request.readable_last_request()}"
            )

        self.stdout.write("-" * 80)

        # Delete them
        deleted_count, _ = manifest_requests.delete()

        self.stdout.write(
            self.style.SUCCESS(f"✓ Successfully deleted {deleted_count} wlwmanifest.xml requests")
        )

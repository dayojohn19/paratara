from django.core.management.base import BaseCommand
from home.models import Visit
from django.utils import timezone

class Command(BaseCommand):
    help = 'Reset all visits to start fresh daily'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete all visits instead of just old ones',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        deleted_count, _ = Visit.objects.filter(timestamp__date__lt=today).delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} old visits.'))
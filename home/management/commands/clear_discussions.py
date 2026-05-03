from django.core.management.base import BaseCommand
from home.models import PlaceDiscussion

class Command(BaseCommand):
    help = 'Clear all PlaceDiscussion records from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        count = PlaceDiscussion.objects.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No discussions found to delete.'))
            return

        if not options['force']:
            self.stdout.write(self.style.WARNING(f'⚠️  This will delete {count} PlaceDiscussion records!'))
            confirm = input('Are you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        PlaceDiscussion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {count} PlaceDiscussion records.'))

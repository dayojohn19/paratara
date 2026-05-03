from django.core.management.base import BaseCommand
from home.models import RequestPage

class Command(BaseCommand):
    help = 'Clear all RequestPage records with IP starting with 127 (localhost)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Find records where requesting_ip starts with 127 (localhost)
        records_to_delete = RequestPage.objects.filter(
            requesting_ip__startswith='127'
        )
        
        count = records_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No RequestPage records with localhost IP (127.*) found.'))
            return

        if not options['force']:
            self.stdout.write(self.style.WARNING(f'⚠️  This will delete {count} RequestPage records with IP starting with 127!'))
            confirm = input('Are you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        deleted_count, _ = records_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} RequestPage records with IP starting with 127.'))

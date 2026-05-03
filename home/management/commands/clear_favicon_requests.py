from django.core.management.base import BaseCommand
from home.models import RequestLog
from django.db.models import Q

class Command(BaseCommand):
    help = 'Clear all RequestLog records for favicon.ico and wlwmanifest.xml'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Find records where page contains favicon.ico or wlwmanifest.xml
        records_to_delete = RequestLog.objects.filter(
            Q(page__icontains='favicon.ico') |
            Q(page__icontains='wlwmanifest.xml')
        )
        
        count = records_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No RequestLog records for favicon.ico or wlwmanifest.xml found.'))
            return

        if not options['force']:
            self.stdout.write(self.style.WARNING(f'⚠️  This will delete {count} RequestLog records for favicon.ico/wlwmanifest.xml!'))
            confirm = input('Are you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        deleted_count, _ = records_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} RequestLog records for favicon.ico/wlwmanifest.xml.'))

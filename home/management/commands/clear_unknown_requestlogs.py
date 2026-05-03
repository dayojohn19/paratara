from django.core.management.base import BaseCommand
from home.models import RequestLog
from django.db.models import Q

class Command(BaseCommand):
    help = 'Clear all RequestLog records with unknown city and timezone'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Find records where either:
        # 1. ip_location_json is null/empty
        # 2. city_info.city is null/empty or contains "Unknown"
        # 3. city_info.time_zone is null/empty or contains "Unknown"
        
        records_to_delete = RequestLog.objects.filter(
            Q(ip_location_json__isnull=True) |
            Q(ip_location_json__city_info__isnull=True) |
            Q(ip_location_json__city_info__city__isnull=True) |
            Q(ip_location_json__city_info__city__exact='') |
            Q(ip_location_json__city_info__city__icontains='Unknown') |
            Q(ip_location_json__city_info__time_zone__isnull=True) |
            Q(ip_location_json__city_info__time_zone__exact='') |
            Q(ip_location_json__city_info__time_zone__icontains='Unknown')
        )
        
        count = records_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No RequestLog records with unknown city/timezone found.'))
            return

        if not options['force']:
            self.stdout.write(self.style.WARNING(f'⚠️  This will delete {count} RequestLog records with unknown city/timezone!'))
            confirm = input('Are you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        deleted_count, _ = records_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully deleted {deleted_count} RequestLog records with unknown city/timezone.'))

from django.core.management.base import BaseCommand
from django.db.models import F
from collections import defaultdict
from home.models import RequestLog, RequestPage


class Command(BaseCommand):
    help = 'Print RequestLog entries categorized by timezone region'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of entries per timezone'
        )

    def get_region(self, timezone):
        """Extract region from timezone string (e.g., 'America/New_York' -> 'America')"""
        if not timezone or timezone == "Unknown timezone":
            return "Unknown"
        
        if '/' in timezone:
            return timezone.split('/')[0]
        return "Other"

    def handle(self, *args, **options):
        limit = options.get('limit')
        
        # Fetch all RequestLog entries
        request_logs = RequestLog.objects.all()
        
        # Count and collect requestPages status
        with_pages = 0
        without_pages = 0
        logs_without_pages = []
        
        # Group by region, then by timezone
        region_groups = defaultdict(lambda: defaultdict(list))
        
        for log in request_logs:
            # Check if RequestPage records exist for this page and IP
            has_request_page = RequestPage.objects.filter(
                page_name=log.page,
                requesting_ip=log.ip_address
            ).exists()
            
            if has_request_page:
                with_pages += 1
            else:
                without_pages += 1
                logs_without_pages.append(log)
            
            timezone = (
                log.ip_location_json.get("city_info", {}).get("time_zone")
                if log.ip_location_json else None
            ) or "Unknown timezone"
            
            region = self.get_region(timezone)
            region_groups[region][timezone].append(log)
        
        # Print categorically by region
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('REQUEST LOG ENTRIES BY REGION & TIMEZONE'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        # Print requestPages status
        self.stdout.write(self.style.WARNING(f'📊 RequestPages Status:'))
        self.stdout.write(self.style.SUCCESS(f'   ✓ With RequestPages: {with_pages}'))
        self.stdout.write(self.style.ERROR(f'   ✗ Without RequestPages: {without_pages}'))
        self.stdout.write('')
        
        # Print entries without requestPages and delete them
        if logs_without_pages:
            self.stdout.write(self.style.ERROR('\n🗑️  ENTRIES WITHOUT REQUESTPAGES:\n'))
            for i, log in enumerate(logs_without_pages, 1):
                self.stdout.write(
                    f"  {i}. ID: {log.id} | IP: {log.ip_address} | Page: {log.page} | "
                    f"Method: {log.method} | Count: {log.count} | {log.last_request.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # Delete them one by one
            self.stdout.write(self.style.WARNING('\n⏳ Deleting entries one by one...\n'))
            for i, log in enumerate(logs_without_pages, 1):
                log.delete()
                self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted entry {i}/{len(logs_without_pages)} (ID: {log.id})"))
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ All {len(logs_without_pages)} RequestLog entries without requestPages have been deleted\n'))
        
        for region in sorted(region_groups.keys()):
            timezones = region_groups[region]
            total_region = sum(len(logs) for logs in timezones.values())
            
            self.stdout.write(self.style.WARNING(f'\n🌍 {region.upper()} ({total_region} entries)'))
            self.stdout.write('-' * 80)
            
            for timezone in sorted(timezones.keys()):
                logs = timezones[timezone]
                self.stdout.write(f"  └─ [{timezone}] ({len(logs)})")
        
        total = sum(sum(len(logs) for logs in tzs.values()) for tzs in region_groups.values())
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS(f'Total: {total} entries'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

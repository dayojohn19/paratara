from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from home.models import RequestPage


class Command(BaseCommand):
    help = 'Count RequestPage status codes - 404 vs non-404 and identify suspicious page_names'

    def is_suspicious_404_path(self, page_name):
        """Detect common 404 patterns in page_name"""
        suspicious_patterns = [
            'wp-content',
            'wp-admin',
            'xmlrpc.php',
            '.php',
            '.exe',
            '.jsp',
            '.aspx',
            'admin',
            'config',
            'backup',
            '.sql',
            '.tar',
            '.zip',
            '.txt',
            '/proc/',
            '/sys/',
            '../',
            'shell',
            'upload',
        ]
        
        page_lower = page_name.lower()
        return any(pattern in page_lower for pattern in suspicious_patterns)

    def handle(self, *args, **options):
        # Get counts
        total_requests = RequestPage.objects.count()
        count_404_by_status = RequestPage.objects.filter(status_code=404).count()
        count_not_404 = RequestPage.objects.exclude(status_code=404).count()

        # Display summary
        self.stdout.write(self.style.SUCCESS('=== REQUEST PAGE STATUS SUMMARY ===\n'))
        self.stdout.write(f'Total Requests: {total_requests}')
        self.stdout.write(self.style.ERROR(f'404 Errors (by status_code): {count_404_by_status}'))
        self.stdout.write(self.style.SUCCESS(f'Non-404 (Success/Other): {count_not_404}'))
        self.stdout.write('')

        # Get breakdown by status code
        status_breakdown = RequestPage.objects.values('status_code').annotate(
            count=Count('id')
        ).order_by('status_code')

        self.stdout.write(self.style.SUCCESS('Breakdown by Status Code:'))
        for item in status_breakdown:
            status = item['status_code']
            count = item['count']
            
            if status == 404:
                self.stdout.write(f"  {status}: {count} requests", self.style.ERROR)
            elif status == 200:
                self.stdout.write(f"  {status}: {count} requests", self.style.SUCCESS)
            else:
                self.stdout.write(f"  {status}: {count} requests")
        
        # Identify suspicious 404-like page_names
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('\n=== SUSPICIOUS PAGE_NAMES (Likely 404s) ===\n'))
        
        # Get all unique page_names
        all_pages = RequestPage.objects.values('page_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        suspicious_pages = []
        for page_obj in all_pages:
            page_name = page_obj['page_name']
            if self.is_suspicious_404_path(page_name):
                suspicious_pages.append({
                    'page_name': page_name,
                    'count': page_obj['count']
                })
        
        if suspicious_pages:
            self.stdout.write(self.style.ERROR(f'Found {len(suspicious_pages)} suspicious page_names:\n'))
            for i, page in enumerate(suspicious_pages[:20], 1):  # Show top 20
                self.stdout.write(f"{i}. {page['page_name']} - {page['count']} requests", self.style.WARNING)
        else:
            self.stdout.write('No suspicious page_names found')

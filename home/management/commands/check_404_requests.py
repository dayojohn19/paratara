from django.core.management.base import BaseCommand
from home.models import RequestLog


class Command(BaseCommand):
    help = 'Check if RequestLog entries have 404 errors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=int,
            help='Check a specific RequestLog by ID',
        )
        parser.add_argument(
            '--ip',
            type=str,
            help='Check all RequestLog entries for a specific IP address',
        )
        parser.add_argument(
            '--page',
            type=str,
            help='Check all RequestLog entries for a specific page',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Show all RequestLog entries with 404 errors',
        )

    def handle(self, *args, **options):
        if options['id']:
            self.check_by_id(options['id'])
        elif options['ip']:
            self.check_by_ip(options['ip'])
        elif options['page']:
            self.check_by_page(options['page'])
        elif options['all']:
            self.check_all_404s()
        else:
            self.stdout.write(self.style.WARNING('Please provide an option: --id, --ip, --page, or --all'))

    def check_by_id(self, log_id):
        try:
            log = RequestLog.objects.get(id=log_id)
            self.print_log_details(log)
        except RequestLog.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'RequestLog with ID {log_id} not found'))

    def check_by_ip(self, ip_address):
        logs = RequestLog.objects.filter(ip_address=ip_address)
        if not logs.exists():
            self.stdout.write(self.style.ERROR(f'No RequestLog entries found for IP {ip_address}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {logs.count()} RequestLog entries for IP {ip_address}:\n'))
        for log in logs:
            self.print_log_details(log)

    def check_by_page(self, page):
        logs = RequestLog.objects.filter(page=page)
        if not logs.exists():
            self.stdout.write(self.style.ERROR(f'No RequestLog entries found for page {page}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {logs.count()} RequestLog entries for page "{page}":\n'))
        for log in logs:
            self.print_log_details(log)

    def check_all_404s(self):
        logs = RequestLog.objects.all()
        count_with_404 = sum(1 for log in logs if log.check_if_404())
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal RequestLog entries with 404 errors: {count_with_404} out of {logs.count()}\n'))
        
        for log in logs:
            if log.check_if_404():
                self.print_log_details(log)

    def print_log_details(self, log):
        has_404 = log.check_if_404()
        status = self.style.ERROR('✗ HAS 404 ERRORS') if has_404 else self.style.SUCCESS('✓ No 404 errors')
        
        self.stdout.write(f'\n--- RequestLog ID: {log.id} ---')
        self.stdout.write(f'Full URL: {log.get_full_url()}')
        self.stdout.write(f'IP Address: {log.ip_address}')
        self.stdout.write(f'Page: {log.page}')
        self.stdout.write(f'Method: {log.method}')
        self.stdout.write(f'Request Count: {log.count}')
        self.stdout.write(f'Last Request: {log.readable_last_request()}')
        self.stdout.write(f'Status: {status}')
        
        if has_404:
            count = log.get_404_count()
            self.stdout.write(self.style.WARNING(f'404 Error Count: {count}'))

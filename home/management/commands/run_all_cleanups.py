from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Runs all cleanup and summary commands in sequence.'

    def handle(self, *args, **options):
        commands = [
            'cleanup_wlwmanifest_requests',
            'cleanup_request_pages',
            'cleanup_favicon_requests',
            'clear_unknown_requestlogs',
            'clear_favicon_requests',
            'summarize_request_pages',
            'cleanup_requestpagesummary_php',
        ]
        for cmd in commands:
            self.stdout.write(self.style.NOTICE(f'Running {cmd}...'))
            try:
                call_command(cmd)
                self.stdout.write(self.style.SUCCESS(f'Successfully ran {cmd}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error running {cmd}: {e}'))

from django.core.management.base import BaseCommand
from garden.models import Collection

class Command(BaseCommand):
    help = 'Count and delete Collection records with "test" in collectionName'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Find records where collectionName contains 'test' (case-insensitive)
        records_to_delete = Collection.objects.filter(
            collectionName__icontains='test'
        )
        
        count = records_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No Collection records with "test" in collectionName found.'))
            return

        # Display the collections that will be deleted
        self.stdout.write(self.style.WARNING(f'\n⚠️  Found {count} Collection(s) with "test" in collectionName:\n'))
        for idx, collection in enumerate(records_to_delete, 1):
            self.stdout.write(f'{idx}. {collection.collectionName} (ID: {collection.id})')
        
        if not options['force']:
            self.stdout.write(self.style.WARNING(f'\n⚠️  This will delete {count} Collection record(s)!'))
            confirm = input('\nAre you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        deleted_count, _ = records_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully deleted {deleted_count} Collection record(s) with "test" in collectionName.\n'))

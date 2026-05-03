from django.core.management.base import BaseCommand
from garden.models import Collection

class Command(BaseCommand):
    help = 'Delete all Collection records where collectionPlace.placeName is NOT Siargao'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        # Find records where collectionPlace.placeName is NOT 'Siargao'
        records_to_delete = Collection.objects.exclude(
            collectionPlace__placeName='Siargao'
        )
        
        count = records_to_delete.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('No Collection records found with placeName NOT equal to "Siargao".'))
            return

        # Display the collections that will be deleted
        self.stdout.write(self.style.WARNING(f'\n⚠️  Found {count} Collection(s) where collectionPlace.placeName is NOT "Siargao":\n'))
        for idx, collection in enumerate(records_to_delete[:10], 1):
            place_name = collection.collectionPlace.placeName if collection.collectionPlace else 'N/A'
            self.stdout.write(f'{idx}. {collection.collectionName} (Place: {place_name}, ID: {collection.id})')
        
        if count > 10:
            self.stdout.write(f'... and {count - 10} more')
        
        if not options['force']:
            self.stdout.write(self.style.WARNING(f'\n⚠️  This will delete {count} Collection record(s)!'))
            confirm = input('\nAre you sure? Type "yes" to confirm: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Deletion cancelled.'))
                return

        deleted_count, _ = records_to_delete.delete()
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully deleted {deleted_count} Collection record(s) where placeName is NOT "Siargao".\n'))

from django.core.management.base import BaseCommand
from garden.models import Collection

class Command(BaseCommand):
    help = 'Display Collection model statistics'

    def handle(self, *args, **options):
        # Total count of all Collection objects
        total_count = Collection.objects.count()
        
        # Count of Collections with collectionIsCollected = True
        collected_count = Collection.objects.filter(collectionIsCollected=True).count()
        
        # Count of Collections with collectionIsCollected = False
        not_collected_count = Collection.objects.filter(collectionIsCollected=False).count()
        
        # Calculate percentage
        if total_count > 0:
            collected_percentage = (collected_count / total_count) * 100
            not_collected_percentage = (not_collected_count / total_count) * 100
        else:
            collected_percentage = 0
            not_collected_percentage = 0
        
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(self.style.SUCCESS('📊 COLLECTION STATISTICS'))
        self.stdout.write(self.style.SUCCESS('═' * 60))
        self.stdout.write(f'\n📦 Total Collections: {self.style.SUCCESS(str(total_count))}')
        self.stdout.write(f'✅ Collected (True):  {self.style.SUCCESS(str(collected_count))} ({collected_percentage:.1f}%)')
        self.stdout.write(f'❌ Not Collected (False): {self.style.WARNING(str(not_collected_count))} ({not_collected_percentage:.1f}%)')
        self.stdout.write(f'\n{self.style.SUCCESS("═" * 60)}\n')

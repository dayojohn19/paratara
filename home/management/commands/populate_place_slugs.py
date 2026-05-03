from django.core.management.base import BaseCommand
from home.models import Places_v2
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Populate unique slugs for Places_v2 entries that are missing or non-unique. Use --dry-run to preview without saving.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        changed = 0
        for place in Places_v2.objects.all():
            base_slug = slugify(place.placename) or f"place-{place.id}"
            slug = base_slug
            i = 1
            while Places_v2.objects.filter(slug=slug).exclude(pk=place.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            if place.slug != slug:
                self.stdout.write(f'Will set slug for "{place.placename}" (id={place.id}) -> {slug}')
                changed += 1
                if not dry_run:
                    place.slug = slug
                    place.save(update_fields=['slug'])
        self.stdout.write(self.style.SUCCESS(f'Processed {changed} places{" (dry-run)" if dry_run else ""}.'))

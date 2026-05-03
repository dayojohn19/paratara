from django.core.management.base import BaseCommand
from home.models import Places_v2
import subprocess
# python manage.py fb_a_batch_import --place=Siargao
class Command(BaseCommand):
    help = 'Run fb_b_scrape_selenium and import_fb_posts for each Facebook page of a given place.'

    def add_arguments(self, parser):
        parser.add_argument('--place', type=str, required=True, help='Placename to process Facebook pages for')

    def handle(self, *args, **options):
        placename_input = options['place']
        # Prefer slug lookup (exact or slugified), fallback to placename contains
        from django.utils.text import slugify
        from django.db.models import Q
        slug_candidate = slugify(placename_input)
        place = Places_v2.objects.filter(Q(slug__iexact=placename_input) | Q(slug=slug_candidate)).first()
        if not place:
            # Fallback: search by placename
            place = Places_v2.objects.filter(placename__icontains=placename_input).first()
        if not place:
            self.stdout.write(self.style.ERROR(f'No Places_v2 found with placename or slug matching "{placename_input}".'))
            return
        # Ensure place has a unique slug (create one if blank)
        if not place.slug:
            base = slugify(place.placename) or f'place-{place.id or "new"}'
            candidate = base
            counter = 1
            while Places_v2.objects.filter(slug=candidate).exclude(id=place.id).exists():
                candidate = f"{base}-{counter}"
                counter += 1
            place.slug = candidate
            try:
                place.save(update_fields=['slug'])
                self.stdout.write(self.style.SUCCESS(f'Generated slug "{place.slug}" for place "{place.placename}"'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to save slug for place "{place.placename}": {e}'))
                return
        fb_pages = place.facebook_pages.all()
        if not fb_pages:
            self.stdout.write(self.style.WARNING(f'No Facebook pages linked to place "{place.placename}" (slug={place.slug}).'))
            return
        for fb_page in fb_pages:
            page_id = fb_page.page_id
            self.stdout.write(self.style.NOTICE(f'Processing Facebook page: {page_id} for place: {place.placename} (slug={place.slug})'))
            # Run fb_b_scrape_selenium
            scrape_cmd = [
                'python', 'manage.py', 'fb_b_scrape_selenium', f'--page_id={page_id}', f'--place={place.slug}'
            ]
            result_scrape = subprocess.run(scrape_cmd, capture_output=True, text=True)
            self.stdout.write(result_scrape.stdout)
            if result_scrape.stderr:
                self.stdout.write(self.style.ERROR(result_scrape.stderr))
            # Run import_fb_posts using slug so it finds the place
            import_cmd = [
                'python', 'manage.py', 'import_fb_posts', f'--place={place.slug}'
            ]
            result_import = subprocess.run(import_cmd, capture_output=True, text=True)
            self.stdout.write(result_import.stdout)
            if result_import.stderr:
                self.stdout.write(self.style.ERROR(result_import.stderr))
        self.stdout.write(self.style.SUCCESS(f'Completed processing all Facebook pages for place "{place.placename}" (slug={place.slug}).'))

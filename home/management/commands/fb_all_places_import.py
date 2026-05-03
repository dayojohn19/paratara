from django.core.management.base import BaseCommand
from home.models import Places_v2
from django.utils.text import slugify
import subprocess

class Command(BaseCommand):
    help = 'Iterate all Places_v2 and run fb_b_scrape_selenium and import_fb_posts for each Facebook page.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of places processed (0 = all)')
        parser.add_argument('--dry-run', action='store_true', help='Show actions without running commands')
        parser.add_argument('--continue-on-error', action='store_true', help='Continue to next page/place on error')

    def handle(self, *args, **options):
        limit = options.get('limit', 0)
        dry_run = options.get('dry_run', False)
        cont = options.get('continue_on_error', False)

        qs = Places_v2.objects.all().order_by('id')
        if limit > 0:
            qs = qs[:limit]

        total = qs.count()
        self.stdout.write(self.style.NOTICE(f'Starting processing {total} places (dry_run={dry_run})'))

        processed = 0
        for place in qs:
            fb_pages = place.facebook_pages.all()
            if not fb_pages:
                self.stdout.write(self.style.WARNING(f'Skipping place {place.placename} (id={place.id}) - no facebook_pages'))
                continue

            # Ensure place has a unique slug
            if not place.slug:
                base = slugify(place.placename) or f'place-{place.id}'
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
                    if not cont:
                        return

            self.stdout.write(self.style.NOTICE(f'Processing place {place.placename} (slug={place.slug}) - {fb_pages.count()} pages'))

            for fb_page in fb_pages:
                page_id = fb_page.page_id
                self.stdout.write(self.style.NOTICE(f'Processing page: {page_id}'))

                if dry_run:
                    self.stdout.write(self.style.SUCCESS(f'DRY RUN: would run fb_b_scrape_selenium --page_id={page_id} --place={place.slug}'))
                    self.stdout.write(self.style.SUCCESS(f'DRY RUN: would run import_fb_posts --place={place.slug}'))
                    continue

                try:
                    scrape_cmd = ['python', 'manage.py', 'fb_b_scrape_selenium', f'--page_id={page_id}', f'--place={place.slug}']
                    result_scrape = subprocess.run(scrape_cmd, capture_output=True, text=True)
                    self.stdout.write(result_scrape.stdout)
                    if result_scrape.returncode != 0:
                        self.stdout.write(self.style.ERROR(f'Scrape failed for {page_id}: {result_scrape.stderr}'))
                        if not cont:
                            return

                    import_cmd = ['python', 'manage.py', 'import_fb_posts', f'--place={place.slug}']
                    result_import = subprocess.run(import_cmd, capture_output=True, text=True)
                    self.stdout.write(result_import.stdout)
                    if result_import.returncode != 0:
                        self.stdout.write(self.style.ERROR(f'Import failed for {page_id}: {result_import.stderr}'))
                        if not cont:
                            return

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing page {page_id}: {e}'))
                    if not cont:
                        return

            processed += 1

        self.stdout.write(self.style.SUCCESS(f'Completed processing {processed} places.'))

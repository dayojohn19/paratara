from django.core.management.base import BaseCommand

from home.imageurl import get_image_url
from home.models import Places_v2


class Command(BaseCommand):
    help = "Populate missing Places_v2.placePhoto values using home.imageurl.get_image_url."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview photo URLs without saving them.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of missing-photo places to process.",
        )
        parser.add_argument(
            "--query-suffix",
            default="",
            help='Text appended to each place name when searching, e.g. "Philippines beach".',
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options.get("limit")
        query_suffix = options["query_suffix"].strip()

        places = Places_v2.objects.all().order_by("id")
        processed = 0
        updated = 0
        skipped = 0
        failed = 0

        for place in places.iterator():
            if place.placePhoto and place.placePhoto.strip():
                skipped += 1
                continue

            if limit is not None and processed >= limit:
                break

            processed += 1
            query = place.placename
            if query_suffix:
                query = f"{query} {query_suffix}"

            self.stdout.write(f'Searching photo for "{place.placename}" (id={place.id})')

            try:
                image_url = get_image_url(query)
            except Exception as exc:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  Failed "{place.placename}" (id={place.id}): {exc}'
                    )
                )
                continue

            if not image_url:
                failed += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  No image found for "{place.placename}" (id={place.id})'
                    )
                )
                continue

            self.stdout.write(f"  Found: {image_url}")
            updated += 1

            if not dry_run:
                place.placePhoto = image_url
                place.save(update_fields=["placePhoto"])

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                "Completed%s. processed=%s updated=%s skipped=%s failed=%s"
                % (suffix, processed, updated, skipped, failed)
            )
        )

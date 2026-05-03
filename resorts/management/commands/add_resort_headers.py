from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import resortItem


class Command(BaseCommand):
    help = "Populate/replace headerImage for resortItem records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing headerImage values",
        )
        parser.add_argument(
            "--place",
            type=str,
            default=None,
            help='Only update resorts in a specific place (e.g. "Siargao")',
        )

    def handle(self, *args, **kwargs):
        force: bool = kwargs.get("force", False)
        place = kwargs.get("place")

        resorts = resortItem.objects.all()
        if place:
            resorts = resorts.filter(place__placename__iexact=place)

        if not resorts.exists():
            self.stdout.write(self.style.WARNING("No resortItem records found."))
            return

        updated = 0
        with transaction.atomic():
            for resort in resorts:
                if (not force) and resort.headerImage:
                    continue

                base = resort.slug or slugify(resort.RealName or resort.name or f"resort-{resort.id}")
                # Picsum provides a real image response (with redirects) and is suitable for dev/demo data.
                resort.headerImage = f"https://picsum.photos/seed/{base}-header/1600/900"
                resort.save(update_fields=["headerImage"])
                updated += 1

        scope = f" for place={place}" if place else ""
        mode = "(forced overwrite)" if force else "(filled blanks only)"
        self.stdout.write(self.style.SUCCESS(f"Updated headerImage for {updated} resorts{scope} {mode}."))

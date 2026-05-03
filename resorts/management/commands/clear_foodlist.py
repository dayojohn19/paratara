from django.core.management.base import BaseCommand

from resorts.models import resortItem


class Command(BaseCommand):
    help = "Clear every resort's `resortFood` list (aka foodlist)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default=None,
            help='Limit the operation to resorts within the given place (case insensitive).',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be cleared but do not change the database.",
        )

    def handle(self, *args, **kwargs):
        place = kwargs.get("place")
        dry_run = bool(kwargs.get("dry_run"))

        resorts = resortItem.objects.all()
        if place:
            resorts = resorts.filter(place__placename__iexact=place)

        if not resorts.exists():
            self.stdout.write(self.style.WARNING("No resortItem records found for the given filter."))
            return

        total_links = 0
        total_resorts = 0

        for resort in resorts:
            food_count = resort.resortFood.count()
            if not food_count:
                continue

            total_links += food_count
            total_resorts += 1

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Resort {resort.id} ({resort.RealName or resort.name}) has {food_count} foodlist entries to clear."
                )
            else:
                resort.resortFood.clear()

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete; no database changes were made."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleared {total_links} foodlist links from {total_resorts} resort(s) (place={place or 'all'})."
                )
            )

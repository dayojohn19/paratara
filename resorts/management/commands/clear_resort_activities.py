from django.core.management.base import BaseCommand

from resorts.models import resortItem


class Command(BaseCommand):
    help = "Clear every resort's resortActivities list"

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default=None,
            help='Limit the operation to resorts within the given place (case insensitive).',
        )
        parser.add_argument(
            "--resort-id",
            type=int,
            default=None,
            help="Only clear a specific resortItem id.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be cleared but do not change the database.",
        )

    def handle(self, *args, **kwargs):
        place = kwargs.get("place")
        resort_id = kwargs.get("resort_id")
        dry_run = bool(kwargs.get("dry_run"))

        resorts = resortItem.objects.all().order_by("id")
        if place:
            resorts = resorts.filter(place__placename__iexact=place)
        if resort_id:
            resorts = resorts.filter(id=resort_id)

        if not resorts.exists():
            self.stdout.write(self.style.WARNING("No resortItem records found for the given filter."))
            return

        total_links = 0
        total_resorts = 0

        for resort in resorts:
            activities_count = resort.resortActivities.count()
            if not activities_count:
                continue

            total_links += activities_count
            total_resorts += 1

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Resort {resort.id} ({resort.RealName or resort.name}) has {activities_count} activity entries to clear."
                )
            else:
                resort.resortActivities.clear()

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete; no database changes were made."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleared {total_links} resortActivities links from {total_resorts} resort(s) (place={place or 'all'})."
                )
            )

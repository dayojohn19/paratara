from django.core.management.base import BaseCommand
from django.db import transaction

from resorts.models import resortItem, resortPackages


class Command(BaseCommand):
    help = "Ensure each resort has at least 3 activity resortPackages (e.g. board games, motorbike rentals, surfing)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default="Siargao",
            help='Only update resorts in a specific place (default: "Siargao")',
        )
        parser.add_argument(
            "--min",
            type=int,
            default=3,
            help="Minimum activities to attach to resortActivities (default: 3)",
        )

    def handle(self, *args, **kwargs):
        place: str = kwargs["place"]
        min_count: int = kwargs["min"]

        resorts = resortItem.objects.filter(place__placename__iexact=place)
        if not resorts.exists():
            self.stdout.write(self.style.WARNING(f"No resorts found for place '{place}'."))
            return

        activity_titles = [
            "Board Games",
            "Motorbike Rentals",
            "Surfing Lessons",
            "Island Hopping",
            "Yoga Session",
            "Snorkeling",
            "Kayak Rental",
        ]

        created = 0
        attached = 0

        with transaction.atomic():
            for resort in resorts:
                # Collect existing titles already attached to this resort's activities
                existing_titles = set(
                    resort.resortActivities.values_list("PackageTitle", flat=True)
                )

                # Attach up to min_count activities total
                for title in activity_titles:
                    if resort.resortActivities.count() >= min_count:
                        break

                    # Avoid duplicates per resort by title
                    if title in existing_titles:
                        continue

                    pkg = resortPackages.objects.create(
                        PackageTitle=title,
                        ItemOfResort=resort,
                    )
                    resort.resortActivities.add(pkg)
                    existing_titles.add(title)
                    created += 1
                    attached += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{resort.RealName or resort.name}: activities={resort.resortActivities.count()}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Done. Created/attached {attached} activity packages across {resorts.count()} resorts."))

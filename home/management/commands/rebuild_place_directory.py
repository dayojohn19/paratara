from django.core.management.base import BaseCommand

from home.models import Places_v2
from home.place_directory import bulk_sync_place_directory


class Command(BaseCommand):
    help = "Rebuild or update PlaceDirectory rows for Places_v2 in batches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of places to process per batch.",
        )
        parser.add_argument(
            "--start-id",
            type=int,
            help="Only process places with id >= this value.",
        )
        parser.add_argument(
            "--end-id",
            type=int,
            help="Only process places with id <= this value.",
        )
        parser.add_argument(
            "--missing-only",
            action="store_true",
            help="Create missing rows but do not update existing directory rows.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report planned creates/updates without writing changes.",
        )

    def handle(self, *args, **options):
        batch_size = max(1, options["batch_size"])
        queryset = Places_v2.objects.only("id", "reviewCount").order_by("id")

        if options.get("start_id") is not None:
            queryset = queryset.filter(id__gte=options["start_id"])
        if options.get("end_id") is not None:
            queryset = queryset.filter(id__lte=options["end_id"])

        dry_run = options["dry_run"]
        missing_only = options["missing_only"]

        self.stdout.write(
            "Rebuilding place directory "
            f"batch_size={batch_size} "
            f"missing_only={missing_only} "
            f"dry_run={dry_run}"
        )

        def progress(stats):
            self.stdout.write(
                "processed={processed} created={created} updated={updated} unchanged={unchanged}".format(
                    **stats
                )
            )

        totals = bulk_sync_place_directory(
            queryset,
            batch_size=batch_size,
            dry_run=dry_run,
            missing_only=missing_only,
            progress=progress,
        )

        suffix = " (dry-run)" if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                "Place directory complete%s. processed=%s created=%s updated=%s unchanged=%s"
                % (
                    suffix,
                    totals["processed"],
                    totals["created"],
                    totals["updated"],
                    totals["unchanged"],
                )
            )
        )

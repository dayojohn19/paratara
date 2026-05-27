import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apis.models import Blogs
from home.models import RequestPage


class Command(BaseCommand):
    help = "Seed RequestPage rows from existing blog localurlpath values."

    TEST_NET_PREFIXES = ("192.0.2", "198.51.100", "203.0.113")

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-visits",
            type=int,
            default=1,
            help="Minimum RequestPage rows to create per blog URL (default: 1).",
        )
        parser.add_argument(
            "--max-visits",
            type=int,
            default=5,
            help="Maximum RequestPage rows to create per blog URL (default: 5).",
        )
        parser.add_argument(
            "--days-back",
            type=int,
            default=30,
            help="Spread seeded timestamps across the last N days (default: 30).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional random seed for repeatable output.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create rows even when a RequestPage already exists for a blog URL.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing rows.",
        )

    def _random_ip(self):
        prefix = random.choice(self.TEST_NET_PREFIXES)
        return f"{prefix}.{random.randint(1, 254)}"

    def _random_timestamp(self, days_back):
        max_seconds = max(0, int(days_back)) * 24 * 60 * 60
        if max_seconds == 0:
            return timezone.now()
        return timezone.now() - timedelta(seconds=random.randint(0, max_seconds))

    def handle(self, *args, **options):
        min_visits = options["min_visits"]
        max_visits = options["max_visits"]
        days_back = options["days_back"]
        dry_run = options["dry_run"]
        force = options["force"]

        if options["seed"] is not None:
            random.seed(options["seed"])

        if min_visits < 0 or max_visits < 0:
            raise CommandError("--min-visits and --max-visits must be zero or greater.")
        if min_visits > max_visits:
            raise CommandError("--min-visits cannot be greater than --max-visits.")
        if days_back < 0:
            raise CommandError("--days-back must be zero or greater.")

        seen = set()
        blog_urls = []
        for raw_path in (
            Blogs.objects.exclude(localurlpath="")
            .exclude(localurlpath__isnull=True)
            .order_by("id")
            .values_list("localurlpath", flat=True)
        ):
            path = str(raw_path or "").strip()
            if not path:
                continue
            if not path.startswith("/"):
                path = f"/{path}"
            if path in seen:
                continue
            seen.add(path)
            blog_urls.append(path)

        if not force and blog_urls:
            existing_pages = set(
                RequestPage.objects.filter(page_name__in=blog_urls).values_list(
                    "page_name", flat=True
                )
            )
            blog_urls = [path for path in blog_urls if path not in existing_pages]

        rows = []
        for path in blog_urls:
            visits = random.randint(min_visits, max_visits)
            for _ in range(visits):
                rows.append(
                    RequestPage(
                        page_name=path,
                        requesting_ip=self._random_ip(),
                        status_code=200,
                    )
                )

        self.stdout.write(
            f"Blog URLs selected: {len(blog_urls)} | RequestPage rows to create: {len(rows)}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no rows created."))
            return

        created_rows = RequestPage.objects.bulk_create(rows, batch_size=500)

        timestamp_updates = []
        for row in created_rows:
            if row.id:
                row.timesmtamp = self._random_timestamp(days_back)
                timestamp_updates.append(row)

        if timestamp_updates:
            RequestPage.objects.bulk_update(
                timestamp_updates,
                fields=["timesmtamp"],
                batch_size=500,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created_rows)} RequestPage rows from blog URLs."
            )
        )

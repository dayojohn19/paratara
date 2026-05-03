from __future__ import annotations

import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from resortManagement.models import Checkins, ResortManager
from resorts.models import Packages


class Command(BaseCommand):
    help = "Create demo Checkins records for a specific resort package."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="How many Checkins to create (default: 100).",
        )
        parser.add_argument(
            "--package-id",
            type=int,
            default=None,
            help="ID of resorts.Packages to attach Checkins to.",
        )
        parser.add_argument(
            "--package-title-contains",
            type=str,
            default="Garden Villa Suite",
            help='Substring to match resorts.Packages.title (default: "Ocean Suite").',
        )
        parser.add_argument(
            "--manager-id",
            type=int,
            default=None,
            help="Optional ResortManager ID to set as checked_in_by.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Resolve the package and print what would happen, without inserting rows.",
        )

    def handle(self, *args, **options):
        count: int = options["count"]
        package_id = options["package_id"]
        title_contains: str = options["package_title_contains"]
        manager_id = options["manager_id"]
        dry_run: bool = options["dry_run"]

        if count <= 0:
            raise CommandError("--count must be a positive integer")

        package = self._resolve_package(package_id=package_id, title_contains=title_contains)
        resort = getattr(getattr(package, "packageName", None), "ItemOfResort", None)
        if resort is None:
            raise CommandError(
                f"Package id={package.id} ('{package.title}') does not have a linked resort via packageName.ItemOfResort"
            )

        manager = None
        if manager_id is not None:
            try:
                manager = ResortManager.objects.get(id=manager_id)
            except ResortManager.DoesNotExist as exc:
                raise CommandError(f"ResortManager id={manager_id} not found") from exc

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: would create {count} Checkins for package id={package.id} ('{package.title}') "
                    f"at resort id={resort.id} ('{getattr(resort, 'RealName', resort)}')."
                )
            )
            if manager is not None:
                self.stdout.write(self.style.WARNING(f"DRY RUN: checked_in_by would be ResortManager id={manager.id}"))
            return

        checkins = self._build_checkins(count=count, package=package, resort=resort, manager=manager)

        with transaction.atomic():
            created = Checkins.objects.bulk_create(checkins, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created)} Checkins for package id={package.id} ('{package.title}')."
            )
        )

    def _resolve_package(self, package_id, title_contains: str) -> Packages:
        if package_id is not None:
            try:
                return Packages.objects.select_related("packageName__ItemOfResort").get(id=package_id)
            except Packages.DoesNotExist as exc:
                raise CommandError(f"Packages id={package_id} not found") from exc

        qs = Packages.objects.select_related("packageName__ItemOfResort").filter(title__icontains=title_contains)
        print('QS: ',qs)
        matches = list(qs[:10])
        total = qs.count()
        print('total=', total)

        if total == 0:
            raise CommandError(f"No Packages found with title containing: {title_contains!r}")

        if total > 1:
            def _label(p: Packages) -> str:
                parent = getattr(p, "packageName", None)
                parent_title = getattr(parent, "PackageTitle", None)
                resort = getattr(parent, "ItemOfResort", None) if parent else None
                resort_name = getattr(resort, "RealName", None) if resort else None
                resort_id = getattr(resort, "id", None) if resort else None

                extra = []
                if parent_title:
                    extra.append(f"parent={parent_title}")
                if resort_name or resort_id:
                    extra.append(f"resort={resort_id}:{resort_name}")

                suffix = f" ({'; '.join(extra)})" if extra else ""
                return f"{p.id}:{p.title}{suffix}"

            preview = ", ".join([_label(p) for p in matches])
            more = "" if total <= len(matches) else f" (showing first {len(matches)} of {total})"
            raise CommandError(
                "Multiple Packages matched. Use --package-id to pick one. "
                f"Matches: {preview}{more}"
            )

        return matches[0]

    def _build_checkins(self, count: int, package: Packages, resort, manager):
        first_names = [
            "Alex",
            "Jamie",
            "Sam",
            "Taylor",
            "Jordan",
            "Casey",
            "Morgan",
            "Riley",
            "Avery",
            "Cameron",
            "Drew",
            "Quinn",
        ]
        last_names = [
            "Reyes",
            "Santos",
            "Garcia",
            "Cruz",
            "Dela Cruz",
            "Bautista",
            "Navarro",
            "Castillo",
            "Flores",
            "Ramos",
            "Mendoza",
            "Torres",
        ]

        now = timezone.now()
        objects: list[Checkins] = []

        for i in range(count):
            first = random.choice(first_names)
            last = random.choice(last_names)
            guest_name = f"{first} {last}"

            token = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
            guest_email = f"{first.lower()}.{last.lower().replace(' ', '')}.{token}@example.com"

            guest_phone = self._random_phone()

            # Spread check-ins around the past 14 days through next 30 days
            checkin_dt = now + timedelta(days=random.randint(-14, 30), hours=random.randint(0, 20))
            nights = random.randint(1, 4)
            checkout_dt = checkin_dt + timedelta(days=nights)

            objects.append(
                Checkins(
                    id_picture=None,
                    room=package,
                    resort=resort,
                    checkin_date=checkin_dt,
                    checkout_date=checkout_dt,
                    guest_name=guest_name,
                    guest_email=guest_email,
                    guest_phone=guest_phone,
                    special_requests="",
                    checked_in=True,
                    checked_in_by=manager,
                )
            )

        return objects

    def _random_phone(self) -> str:
        # Keeps it simple but looks like a PH mobile number.
        return "09" + "".join(random.choices(string.digits, k=9))

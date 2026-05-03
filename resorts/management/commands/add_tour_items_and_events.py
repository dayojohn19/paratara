from __future__ import annotations

import calendar

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from home.models import SiargaoEventSchedule
from resorts.models import Packages, resortItem, resortPackages


def _truncate(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


class Command(BaseCommand):
    help = (
        "Populate resortTour with resortPackages, ensure each tour package has at least N Packages items, "
        "and create/link K SiargaoEventSchedule events per item for a target month/year."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default="Siargao",
            help='Only update resorts in a specific place (default: "Siargao")',
        )
        parser.add_argument(
            "--min-tour-packages",
            type=int,
            default=3,
            help="Minimum resortPackages attached to resortTour per resort (default: 3)",
        )
        parser.add_argument(
            "--min-items",
            type=int,
            default=3,
            help="Minimum Packages items per tour resortPackage (default: 3)",
        )
        parser.add_argument(
            "--events-per-item",
            type=int,
            default=2,
            help="Number of SiargaoEventSchedule events to create per Packages item for the target month/year (default: 2)",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=1,
            help="Target month for generated events (default: 1 for January)",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Target year for generated events (default: 2026)",
        )

    def handle(self, *args, **kwargs):
        place: str = kwargs["place"]
        min_tour_packages: int = kwargs["min_tour_packages"]
        min_items: int = kwargs["min_items"]
        events_per_item: int = kwargs["events_per_item"]
        month: int = kwargs["month"]
        year: int = kwargs["year"]

        if month < 1 or month > 12:
            raise SystemExit("--month must be between 1 and 12")
        if year < 2000 or year > 2100:
            raise SystemExit("--year must be a reasonable 4-digit year")
        if min_tour_packages < 1 or min_items < 1 or events_per_item < 0:
            raise SystemExit("--min-tour-packages and --min-items must be >= 1; --events-per-item must be >= 0")

        resorts = resortItem.objects.filter(place__placename__iexact=place)
        if not resorts.exists():
            self.stdout.write(self.style.WARNING(f"No resorts found for place '{place}'."))
            return

        seed_titles = [
            "Island Hopping Tour",
            "Land Tour",
            "Sunset Cruise",
            "Lagoon & Cave Tour",
            "Surf & Beach Day",
            "Waterfalls Day Trip",
            "Food Crawl Tour",
        ]

        created_tour_packages = 0
        created_items = 0
        created_events = 0

        last_day = calendar.monthrange(year, month)[1]

        with transaction.atomic():
            for resort in resorts:
                resort_label = resort.RealName or resort.name or f"Resort {resort.id}"
                resort_slug = resort.slug or slugify(resort_label)

                existing_tour_packages = list(resort.resortTour.all().order_by("id"))
                needed_packages = max(0, min_tour_packages - len(existing_tour_packages))

                # Create missing top-level tour packages if needed
                for idx in range(len(existing_tour_packages) + 1, len(existing_tour_packages) + needed_packages + 1):
                    base_title = seed_titles[(idx - 1) % len(seed_titles)]
                    title = f"{base_title}"
                    existing = resort.resortTour.filter(PackageTitle__iexact=title).first()
                    pkg = existing or resortPackages.objects.create(
                        PackageTitle=title,
                        ItemOfResort=resort,
                    )
                    resort.resortTour.add(pkg)
                    existing_tour_packages.append(pkg)
                    if existing is None:
                        created_tour_packages += 1

                # Ensure each tour package has minimum items + events
                for pkg_index, pkg in enumerate(existing_tour_packages[:min_tour_packages], start=1):
                    items_qs = Packages.objects.filter(packageName=pkg).order_by("id")
                    existing_items = list(items_qs)
                    needed_items = max(0, min_items - len(existing_items))

                    for item_index in range(len(existing_items) + 1, len(existing_items) + needed_items + 1):
                        # Include resort name to avoid collisions when generating events in the same place
                        base_title = f"{pkg.PackageTitle} — {resort_label} #{item_index}"
                        item_title = _truncate(base_title, 64)
                        if Packages.objects.filter(packageName=pkg, title__iexact=item_title).exists():
                            item_title = _truncate(f"{pkg.PackageTitle} — {resort_label} ({pkg.id}) #{item_index}", 64)

                        item = Packages(
                            packageName=pkg,
                            title=item_title,
                            description=f"{pkg.PackageTitle} hosted by {resort_label}.",
                            information="Includes local guidance and standard inclusions. See manager notes for details.",
                            price=1200 + (pkg_index * 300) + (item_index * 200),
                            website=f"https://paratara.com/resorts/{resort_slug}/tour/{pkg.id}/{item_index}",
                        )

                        # Avoid triggering OpenAI-based auto-event creation in resorts/signals.py
                        item._skip_event_creation = True
                        item.save()

                        pkg.subPackages.add(item)
                        existing_items.append(item)
                        created_items += 1

                    # Keep item linked via M2M too (template uses subPackagesList)
                    for item in existing_items[:min_items]:
                        pkg.subPackages.add(item)

                        if events_per_item == 0:
                            continue

                        place_obj = resort.place
                        if not place_obj:
                            continue

                        existing_count = item.siargaoevents.filter(monthN=month, yearN=year).count()
                        missing_events = max(0, events_per_item - existing_count)
                        if missing_events == 0:
                            continue

                        # Deterministic-ish day selection per item to avoid duplicates; shifts forward if collision.
                        seed_day = 1 + ((item.id or 1) % max(1, last_day))

                        for k in range(missing_events):
                            day = seed_day + (k * 7)
                            while day > last_day:
                                day -= last_day

                            # Avoid duplicates for same place/title/day
                            tries = 0
                            while SiargaoEventSchedule.objects.filter(
                                place=place_obj,
                                scheduleTitle=item.title,
                                dateN=day,
                                monthN=month,
                                yearN=year,
                            ).exists():
                                day += 1
                                if day > last_day:
                                    day = 1
                                tries += 1
                                if tries > last_day:
                                    break

                            if tries > last_day:
                                continue

                            when = date(year, month, day)
                            ds = when.strftime("%b %d, %Y")

                            imgs = [img.urlField for img in item.images]
                            image_url = imgs[0] if imgs else (resort.headerImage or "")

                            schedule_place = resort.address or place_obj.placename
                            if getattr(resort, "latitude", None) and getattr(resort, "longitude", None):
                                schedule_place = (
                                    f"https://www.google.com/maps/dir/?api=1&destination={resort.latitude},{resort.longitude}"
                                )

                            event = SiargaoEventSchedule.objects.create(
                                package=item,
                                place=place_obj,
                                scheduleTitle=item.title,
                                schedulePlace=schedule_place,
                                posterName=resort.RealName or resort.name or "Anonymous",
                                posterURL=f"/resorts/{resort.slug or resort.name}/",
                                scheduleImageURL=image_url,
                                backgroundURL=image_url,
                                thumbnailURL=image_url,
                                scheduleCost=str(item.price) if item.price else "Free",
                                additionalDetails=(
                                    (item.description or "")
                                    + " "
                                    + (item.information or "")
                                    + " "
                                    + (resort.description or "")
                                ).strip()[:500],
                                otherDetails=f"Auto-generated tour event for {ds}",
                                host_name=resort.RealName or resort.name or "",
                                host_link=f"/resorts/{resort.slug or resort.name}/",
                                scheduleTypeAndMode="Resort Tour Package",
                                scheduleWebsite=f"https://paratara.com/resorts/{resort.slug or resort.name}/",
                                dateN=day,
                                monthN=month,
                                yearN=year,
                                exactDate=ds,
                            )

                            place_obj.eventSchedules.add(event)
                            item.siargaoevents.add(event)
                            created_events += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated tours for {resort_label}: tour_packages={resort.resortTour.count()}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Created tour_packages={created_tour_packages}, items={created_items}, events={created_events} "
                f"(target {calendar.month_name[month]} {year})."
            )
        )

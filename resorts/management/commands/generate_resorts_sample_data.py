from __future__ import annotations

import random
import string
from datetime import timedelta
from dataclasses import dataclass
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from home.models import Places_v2
from resorts.models import (
    EventRegistration,
    InactiveResortItem,
    Packages,
    contractTerms,
    feedback,
    resortItem,
    resortPackages,
    sideImagesURLs,
)


def _rand_token(n: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def _picsum(seed: str, width: int = 1200, height: int = 800) -> str:
    safe = slugify(seed) or _rand_token(10)
    return f"https://picsum.photos/seed/{safe}/{width}/{height}"


def _random_ph_coordinates() -> tuple[float, float]:
    # Rough bounding box around the Philippines.
    lat = random.uniform(5.0, 20.0)
    lng = random.uniform(116.0, 127.0)
    return (round(lat, 6), round(lng, 6))


def _choose_or_create_place(place_name: str) -> Places_v2:
    place_name = (place_name or "").strip()
    if place_name:
        place, _ = Places_v2.objects.get_or_create(placename=place_name, defaults={"placeID": 0})
        return place

    existing = Places_v2.objects.order_by("-id").first()
    if existing:
        return existing

    return Places_v2.objects.create(placename="Sample Place", placeID=0)


@dataclass(frozen=True)
class SampleCounts:
    resorts: int
    categories_per_resort: int
    items_per_category: int
    gallery_images_per_resort: int
    registrations_per_resort: int
    inactive_resorts: int
    side_images_pool: int
    feedback_rows: int
    contract_terms_rows: int


def generate_resorts_sample_data(
    *,
    place_name: str = "",
    counts: SampleCounts = SampleCounts(
        resorts=2,
        categories_per_resort=4,
        items_per_category=3,
        gallery_images_per_resort=6,
        registrations_per_resort=4,
        inactive_resorts=1,
        side_images_pool=30,
        feedback_rows=2,
        contract_terms_rows=2,
    ),
    clear_existing_samples: bool = False,
) -> dict[str, int]:
    """
    Generate random-but-realistic sample rows for *all* models in `resorts/models.py`.

    Creates:
    - `resortItem` (+ gallery images)
    - `resortPackages` (group buckets: accommodations, activities, tour, food)
    - `Packages` (sub-items for each resortPackages)
    - `EventRegistration`
    - `InactiveResortItem`
    - `sideImagesURLs`
    - `feedback`, `contractTerms`

    All rows created by this function are tagged with a "Sample:" prefix in relevant
    text fields so they can be safely deleted via `clear_existing_samples=True`.
    """

    if clear_existing_samples:
        # Delete in FK/M2M-friendly order.
        EventRegistration.objects.filter(full_name__startswith="Sample:").delete()
        Packages.objects.filter(title__startswith="Sample:").delete()
        resortPackages.objects.filter(PackageTitle__startswith="Sample:").delete()
        InactiveResortItem.objects.filter(RealName__startswith="Sample:").delete()
        resortItem.objects.filter(RealName__startswith="Sample:").delete()
        sideImagesURLs.objects.filter(urlField__contains="/seed/sample-").delete()

    place = _choose_or_create_place(place_name)

    created_counts: dict[str, int] = {
        "sideImagesURLs": 0,
        "resortItem": 0,
        "InactiveResortItem": 0,
        "resortPackages": 0,
        "Packages": 0,
        "EventRegistration": 0,
        "feedback": 0,
        "contractTerms": 0,
    }

    image_pool: list[sideImagesURLs] = []
    for i in range(max(0, int(counts.side_images_pool))):
        img = sideImagesURLs.objects.create(urlField=_picsum(f"sample-{_rand_token(6)}-{i}", 900, 650))
        image_pool.append(img)
    created_counts["sideImagesURLs"] += len(image_pool)

    def pick_images(n: int) -> list[sideImagesURLs]:
        n = max(0, int(n))
        if not image_pool or n == 0:
            return []
        return random.sample(image_pool, k=min(n, len(image_pool)))

    resorts: list[resortItem] = []
    for i in range(max(1, int(counts.resorts))):
        lat, lng = _random_ph_coordinates()
        real_name = f"Sample: {place.placename} Resort {i + 1}"
        email_slug = slugify(real_name)[:40] or f"sample-{_rand_token(6)}"

        resort = resortItem.objects.create(
            is_active=True,
            resortQRLink="",
            websiteURL=f"https://example.com/{email_slug}",
            RealName=real_name,
            address=f"{random.randint(10, 999)} Beach Road, {place.placename}",
            place=place,
            contactNumber=f"+63 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            contactEmail=f"hello+{email_slug}@example.com",
            whatsappNumber=f"+63 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            open_hours=random.choice(
                [
                    "Mon–Sun 8:00 AM – 9:00 PM",
                    "Mon–Sun 7:00 AM – 10:00 PM",
                    "Daily 9:00 AM – 6:00 PM",
                ]
            ),
            promotionalVideo="",
            virtualpicture="",
            headerImage=_picsum(f"{email_slug}-header", 1600, 900),
            latitude=lat,
            longitude=lng,
            reviews=random.randint(0, 200),
            description=random.choice(
                [
                    "Sample listing for testing resort pages, packages, galleries, and registrations.",
                    "Sample resort data with realistic fields for development and UI previews.",
                ]
            ),
            province="",
            last_visited=timezone.now(),
            # A handful of amenities toggled on for variety.
            has_wifi=True,
            has_pool=random.random() < 0.7,
            has_parking=random.random() < 0.5,
            has_restaurant=random.random() < 0.6,
            has_beach_access=True,
            has_air_conditioning=random.random() < 0.8,
            has_hot_water=random.random() < 0.7,
            has_breakfast=random.random() < 0.6,
            accepts_gcash=True,
            accepts_cash=True,
            accepts_debit_card=random.random() < 0.35,
            accepts_credit_card=random.random() < 0.35,
        )
        place.resortItem.add(resort)

        for img in pick_images(counts.gallery_images_per_resort):
            resort.resortGallery.add(img)

        resorts.append(resort)

    created_counts["resortItem"] += len(resorts)

    category_buckets: list[tuple[str, str]] = [
        ("resortAccomodations", "Accommodations"),
        ("resortActivities", "Activities"),
        ("resortTour", "Tours"),
        ("resortFood", "Food"),
    ]

    all_package_items: list[Packages] = []
    for resort in resorts:
        for bucket_field, label in category_buckets[: max(1, int(counts.categories_per_resort))]:
            group = resortPackages.objects.create(
                PackageTitle=f"Sample: {label}",
                ItemOfResort=resort,
            )
            created_counts["resortPackages"] += 1

            getattr(resort, bucket_field).add(group)

            for j in range(max(1, int(counts.items_per_category))):
                item = Packages.objects.create(
                    packageName=group,
                    title=f"Sample: {label} Item {j + 1}",
                    description=f"Sample {label.lower()} description for UI testing.",
                    information="Sample information and inclusions.",
                    price=random.randint(250, 9500),
                    website=resort.websiteURL or "",
                    is_available=True,
                    expires_at=None if random.random() < 0.8 else (timezone.now() + timedelta(days=30)),
                )
                created_counts["Packages"] += 1

                for img in pick_images(random.randint(1, 3)):
                    item.ImageURL.add(img)

                group.subPackages.add(item)
                all_package_items.append(item)

        resort.save()

    created_regs: list[EventRegistration] = []
    for resort in resorts:
        resort_packages = Packages.objects.filter(packageName__ItemOfResort=resort).order_by("?")[: int(counts.registrations_per_resort)]
        for pkg in resort_packages:
            reg = EventRegistration.objects.create(
                event=pkg,
                resort=resort,
                full_name=f"Sample: Guest {_rand_token(6)}",
                email=f"sample+{_rand_token(10)}@example.com",
                phone=f"+63 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                pax=random.randint(1, 6),
                notes="Sample registration for testing.",
                date=str(timezone.now().date()),
            )
            created_regs.append(reg)
    created_counts["EventRegistration"] += len(created_regs)

    inactive_created: list[InactiveResortItem] = []
    for i in range(max(0, int(counts.inactive_resorts))):
        lat, lng = _random_ph_coordinates()
        inactive = InactiveResortItem.objects.create(
            resort_ID=0,
            name="",
            RealName=f"Sample: Inactive Resort {i + 1}",
            address=f"{random.randint(10, 999)} Coastal Highway, {place.placename}",
            place=place,
            contactNumber="",
            contactEmail="",
            whatsappNumber="",
            open_hours="",
            promotionalVideo="",
            virtualpicture="",
            headerImage=_picsum(f"inactive-{_rand_token(6)}", 1600, 900),
            latitude=lat,
            longitude=lng,
            reviews=random.randint(0, 50),
            description="Sample inactive resort for testing reactivation/transfer flows.",
            province="",
            slug=slugify(f"sample-inactive-{place.placename}-{i + 1}"),
            has_wifi=random.random() < 0.5,
            has_pool=random.random() < 0.5,
            accepts_cash=True,
        )

        for img in pick_images(max(1, counts.gallery_images_per_resort // 2)):
            inactive.resortGallery.add(img)

        inactive_created.append(inactive)

    created_counts["InactiveResortItem"] += len(inactive_created)

    for _ in range(max(0, int(counts.feedback_rows))):
        feedback.objects.create()
    created_counts["feedback"] += max(0, int(counts.feedback_rows))

    for _ in range(max(0, int(counts.contract_terms_rows))):
        contractTerms.objects.create()
    created_counts["contractTerms"] += max(0, int(counts.contract_terms_rows))

    return created_counts


class Command(BaseCommand):
    help = "Generate random sample data for all models in resorts/models.py"

    def add_arguments(self, parser):
        parser.add_argument("--place", type=str, default="", help="Optional place name (Places_v2.placename).")
        parser.add_argument("--resorts", type=int, default=2, help="How many resortItem rows to create (default: 2).")
        parser.add_argument(
            "--items-per-category",
            type=int,
            default=3,
            help="How many Packages rows to create per category per resort (default: 3).",
        )
        parser.add_argument(
            "--gallery-per-resort",
            type=int,
            default=6,
            help="How many sideImagesURLs to attach to each resort gallery (default: 6).",
        )
        parser.add_argument(
            "--registrations-per-resort",
            type=int,
            default=4,
            help="How many EventRegistration rows to create per resort (default: 4).",
        )
        parser.add_argument(
            "--inactive-resorts",
            type=int,
            default=1,
            help="How many InactiveResortItem rows to create (default: 1).",
        )
        parser.add_argument(
            "--side-images-pool",
            type=int,
            default=30,
            help="How many sideImagesURLs to create for sampling (default: 30).",
        )
        parser.add_argument("--clear", action="store_true", help="Delete existing sample rows first.")

    @transaction.atomic
    def handle(self, *args, **options):
        counts = SampleCounts(
            resorts=max(1, int(options["resorts"])),
            categories_per_resort=4,
            items_per_category=max(1, int(options["items_per_category"])),
            gallery_images_per_resort=max(0, int(options["gallery_per_resort"])),
            registrations_per_resort=max(0, int(options["registrations_per_resort"])),
            inactive_resorts=max(0, int(options["inactive_resorts"])),
            side_images_pool=max(0, int(options["side_images_pool"])),
            feedback_rows=2,
            contract_terms_rows=2,
        )

        created = generate_resorts_sample_data(
            place_name=str(options.get("place") or ""),
            counts=counts,
            clear_existing_samples=bool(options.get("clear")),
        )

        self.stdout.write(self.style.SUCCESS("Sample resort data generated."))
        for k in sorted(created.keys()):
            self.stdout.write(f"- {k}: +{created[k]}")

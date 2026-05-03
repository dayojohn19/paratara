from __future__ import annotations

import random
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from home.models import Places_v2
from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


def _normalize_title(title: str) -> str:
    return (title or "").strip().lower()


def _ideas_for_base_title(base_title: str) -> list[dict]:
    t = _normalize_title(base_title)

    if "cake" in t:
        return [
            {
                "name": "Coconut Cloud Chiffon Slice",
                "desc": "Light, airy chiffon with toasted coconut and vanilla cream.",
                "info": "Served chilled. Great pair with iced coffee or mango shake.",
                "price": (180, 320),
                "image_keywords": ["coconut-cake", "chiffon", "dessert"],
            },
            {
                "name": "Calamansi Cheesecake Bar",
                "desc": "Creamy cheesecake with a bright calamansi twist.",
                "info": "Balanced sweet-tart flavor with a buttery crust.",
                "price": (220, 390),
                "image_keywords": ["cheesecake", "calamansi", "bar"],
            },
            {
                "name": "Dark Chocolate Lava Mini",
                "desc": "Warm molten center, rich cocoa finish.",
                "info": "Best enjoyed fresh. Add ice cream for an upgrade.",
                "price": (200, 420),
                "image_keywords": ["chocolate", "lava-cake", "sweet"],
            },
        ]

    if "surf" in t:
        return [
            {
                "name": "Beginner Surf Camp (3 Days)",
                "desc": "Daily coached sessions + ocean safety + board handling.",
                "info": "Includes soft-top board + rashguard during lessons.",
                "price": (4500, 9800),
                "image_keywords": ["surf", "lesson", "ocean"],
            },
            {
                "name": "1:1 Private Surf Coaching",
                "desc": "Personalized coaching focused on your level and goals.",
                "info": "Includes video feedback when conditions allow.",
                "price": (1800, 4200),
                "image_keywords": ["private-coaching", "surfboard", "wave"],
            },
            {
                "name": "Sunrise Paddle + Surf Warmup",
                "desc": "Gentle paddle conditioning + mobility + surf warmup.",
                "info": "Great add-on before your main lesson.",
                "price": (900, 1900),
                "image_keywords": ["sunrise", "paddle", "training"],
            },
        ]

    if "consult" in t:
        return [
            {
                "name": "Resort Discovery Consultation",
                "desc": "Plan the best stay: room choice, activities, and schedule.",
                "info": "Ideal for groups and first-time visitors.",
                "price": (0, 500),
                "image_keywords": ["consultation", "planning", "itinerary"],
            },
            {
                "name": "Wellness Consultation (30 mins)",
                "desc": "Lightweight wellness check-in and recommended routine.",
                "info": "Focus: recovery, sleep, hydration, and travel fatigue.",
                "price": (500, 1500),
                "image_keywords": ["wellness", "spa", "relax"],
            },
            {
                "name": "Private Island Photoshoot Consult",
                "desc": "Shoot planning: outfits, golden-hour spots, shot list.",
                "info": "Great before your resort photoshoot package.",
                "price": (500, 1200),
                "image_keywords": ["photoshoot", "beach", "sunset"],
            },
        ]

    # Fallback ideas for any other custom base titles.
    return [
        {
            "name": f"{base_title} Experience",
            "desc": f"Curated {base_title.lower()} option tailored to your stay.",
            "info": "Ask the front desk for availability and best time slots.",
            "price": (500, 2500),
            "image_keywords": ["experience", "tropical", "resort"],
        },
        {
            "name": f"{base_title} - Premium",
            "desc": "Upgraded inclusions and priority scheduling.",
            "info": "Limited slots depending on season.",
            "price": (1500, 6000),
            "image_keywords": ["premium", "service", "resort"],
        },
    ]


def _unique_resorts_for_place(place: Places_v2) -> list[resortItem]:
    # Your schema has BOTH:
    # - resortItem.place (FK to Places_v2)
    # - Places_v2.resortItem (M2M to resortItem)
    # To be safe, we consider both sources.
    by_fk = resortItem.objects.filter(place=place)
    by_m2m = place.resortItem.all()
    resort_ids = set(by_fk.values_list("id", flat=True)) | set(by_m2m.values_list("id", flat=True))
    return list(resortItem.objects.filter(id__in=resort_ids).order_by("id"))


class Command(BaseCommand):
    help = "Create random resortPackages and attach each to a random resortItem in a place"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=12,
            help="How many resortPackages to create (default: 12)",
        )
        parser.add_argument(
            "--place",
            type=str,
            default="",
            help="Place name (Places_v2.placename). If omitted, uses the latest place.",
        )
        parser.add_argument(
            "--titles",
            type=str,
            default="Cakes,Surf Camps,Consultations",
            help="Comma-separated base titles to use.",
        )
        parser.add_argument(
            "--packages-per",
            type=int,
            default=3,
            help="How many Packages (sub items) to create per resortPackages (default: 3)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = max(1, int(options["count"]))
        packages_per = max(1, int(options["packages_per"]))
        place_name = (options.get("place") or "").strip()
        titles_csv = (options.get("titles") or "").strip()

        base_titles = [t.strip() for t in titles_csv.split(",") if t.strip()]
        if not base_titles:
            base_titles = ["Cakes", "Surf Camps", "Consultations"]

        place = self._get_or_pick_place(place_name)
        resorts = _unique_resorts_for_place(place)

        if not resorts:
            self.stdout.write(self.style.ERROR(f"No resortItem found for place '{place.placename}'."))
            self.stdout.write("Create resorts first (e.g. `python manage.py create_random_resorts --count 2`).")
            return

        created: list[tuple[resortPackages, str, int]] = []
        for _ in range(count):
            rpkg, bucket, created_sub = self._create_one_package(resorts, base_titles, packages_per=packages_per)
            created.append((rpkg, bucket, created_sub))

        self.stdout.write(self.style.SUCCESS(f"Created {len(created)} resortPackages for place: {place.placename}"))
        for p, bucket, created_sub in created:
            self.stdout.write(
                f"- {p.PackageTitle} -> resort_id={p.ItemOfResort_id} | added_to={bucket} | subPackages+={created_sub}"
            )

    def _get_or_pick_place(self, requested_place_name: str) -> Places_v2:
        if requested_place_name:
            place = Places_v2.objects.filter(placename=requested_place_name).first()
            if place:
                return place
            return Places_v2.objects.create(placename=requested_place_name, placeID=0)

        existing = Places_v2.objects.order_by("-id").first()
        if existing:
            return existing

        return Places_v2.objects.create(placename="Siargao Island", placeID=1)

    def _create_one_package(
        self,
        resorts: list[resortItem],
        base_titles: list[str],
        *,
        packages_per: int,
    ) -> tuple[resortPackages, str, int]:
        item = random.choice(resorts)
        base = random.choice(base_titles)

        # Make the title a bit more realistic/varied.
        variants = [
            base,
            f"{base} (Promo)",
            f"{base} Package",
            f"{base} - Starter",
            f"{base} - Premium",
        ]
        title = random.choice(variants)

        pkg = resortPackages.objects.create(PackageTitle=title, ItemOfResort=item)

        # Also attach this package to ONE of the resortItem package buckets.
        # NOTE: resortSchedules is a M2M to home.allSchedules (not resortPackages),
        # so we attach to the actual resortPackages M2Ms here.
        bucket = random.choice(["resortActivities", "resortTour", "resortAccomodations", "resortFood"])
        if bucket == "resortActivities":
            item.resortActivities.add(pkg)
        elif bucket == "resortTour":
            item.resortTour.add(pkg)
        elif bucket == "resortAccomodations":
            item.resortAccomodations.add(pkg)
        else:
            item.resortFood.add(pkg)

        created_sub = self._create_subpackages_for_resortpackage(pkg, item, base_title=base, count=packages_per)
        return pkg, bucket, created_sub

    def _create_subpackages_for_resortpackage(
        self,
        rpkg: resortPackages,
        resort: resortItem,
        *,
        base_title: str,
        count: int,
    ) -> int:
        ideas = _ideas_for_base_title(base_title)
        created = 0

        for i in range(count):
            idea = ideas[i % len(ideas)]
            price_min, price_max = idea.get("price", (500, 2500))
            price = random.randint(int(price_min), int(price_max))

            p = Packages.objects.create(
                packageName=rpkg,
                title=str(idea.get("name", f"{base_title} Item"))[:64],
                description=str(idea.get("desc", "")),
                information=str(idea.get("info", "")),
                price=price,
                website=resort.websiteURL or "",
                is_available=True,
            )

            # Add 1–3 image URLs.
            keywords = idea.get("image_keywords") or ["resort"]
            random.shuffle(keywords)
            image_count = random.randint(1, 3)
            for k in keywords[:image_count]:
                seed = f"{rpkg.id}-{p.id}-{k}".replace(" ", "-")
                img_url = f"https://picsum.photos/seed/{seed}/900/650"
                img = sideImagesURLs.objects.create(urlField=img_url)
                p.ImageURL.add(img)

            # Ensure it is also present in resortPackages.subPackages.
            rpkg.subPackages.add(p)
            created += 1

        return created

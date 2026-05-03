from __future__ import annotations

import random
import re
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from home.models import Places_v2
from resorts.models import resortItem


def _clean_place_token(place_name: str) -> str:
    # Pull a short, human-friendly token from the place name.
    # e.g. "Siargao Island" -> "Siargao", "General Luna" -> "General Luna"
    cleaned = re.sub(r"\s+", " ", (place_name or "").strip())
    cleaned = re.sub(r"\b(island|city|municipality|province)\b", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def generate_resort_name(place_name: str) -> str:
    adjectives = [
        "Azure",
        "Coconut",
        "Coral",
        "Emerald",
        "Golden",
        "Hidden",
        "Lagoon",
        "Mango",
        "Moonlit",
        "Palm",
        "Pearl",
        "Saffron",
        "Seabreeze",
        "Serene",
        "Sunset",
        "Tide",
        "Tropical",
        "Wave",
        "Whispering",
    ]
    nouns = [
        "Bay",
        "Breeze",
        "Cove",
        "Garden",
        "Harbor",
        "Haven",
        "Hideaway",
        "Lagoon",
        "Oasis",
        "Point",
        "Retreat",
        "Sanctuary",
        "Shore",
        "Villas",
    ]
    suffixes = [
        "Resort",
        "Beach Resort",
        "Boutique Resort",
        "Eco Resort",
        "Beachfront Villas",
        "Retreat",
    ]

    place_token = _clean_place_token(place_name)
    parts = [random.choice(adjectives), random.choice(nouns)]

    # Add a location hint sometimes, but keep it clean.
    if place_token and random.random() < 0.55:
        # Prefer a single strong token (first word) for brevity.
        short_place = place_token.split(" ")[0]
        parts.append(short_place)

    parts.append(random.choice(suffixes))

    # Title Case while preserving words like "Eco".
    return " ".join(parts).strip()


def _random_siargao_coordinates() -> tuple[float, float]:
    # Rough bounding box around Siargao Island area.
    lat = random.uniform(9.65, 9.98)
    lng = random.uniform(125.95, 126.25)
    return (round(lat, 6), round(lng, 6))


def _random_ph_coordinates() -> tuple[float, float]:
    lat = random.uniform(5.0, 20.0)
    lng = random.uniform(116.0, 127.0)
    return (round(lat, 6), round(lng, 6))


class Command(BaseCommand):
    help = "Create random resortItem rows with good names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=2,
            help="How many resorts to create (default: 2)",
        )
        parser.add_argument(
            "--place",
            type=str,
            default="",
            help="Optional place name to attach resorts to (uses an existing place if available)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count: int = max(1, int(options["count"]))
        place_name: str = (options.get("place") or "").strip()

        place = self._get_or_pick_place(place_name)
        created_resorts: list[resortItem] = []

        for _ in range(count):
            resort = self._create_one_resort(place)
            created_resorts.append(resort)

        self.stdout.write(self.style.SUCCESS(f"Created {len(created_resorts)} resort(s) for place: {place.placename}"))
        for r in created_resorts:
            self.stdout.write(f"- {r.RealName} | slug={r.slug} | url={r.websiteURL or '(none)'}")

    def _get_or_pick_place(self, requested_place_name: str) -> Places_v2:
        if requested_place_name:
            place, _created = Places_v2.objects.get_or_create(
                placename=requested_place_name,
                defaults={"placeID": 0},
            )
            return place

        existing = Places_v2.objects.order_by("-id").first()
        if existing:
            return existing

        # Fallback: create a minimal place.
        return Places_v2.objects.create(placename="Siargao Island", placeID=1)

    def _create_one_resort(self, place: Places_v2) -> resortItem:
        # Generate a unique-ish name.
        base_name = generate_resort_name(place.placename)
        real_name = base_name

        # Ensure uniqueness by checking existing resorts.
        for i in range(1, 25):
            if not resortItem.objects.filter(RealName=real_name).exists():
                break
            real_name = f"{base_name} {i + 1}"

        place_hint = _clean_place_token(place.placename) or place.placename
        address = f"{random.randint(10, 999)} {random.choice(['Beach Road', 'Coastal Highway', 'Palm Street', 'Ocean Drive'])}, {place_hint}"

        email_slug = slugify(real_name)[:40] or "resort"
        contact_email = f"hello@{email_slug}.example"

        if "siargao" in (place.placename or "").lower():
            lat, lng = _random_siargao_coordinates()
            province = "Surigao del Norte"
        else:
            lat, lng = _random_ph_coordinates()
            province = ""

        resort = resortItem.objects.create(
            RealName=real_name,
            address=address,
            place=place,
            contactNumber=f"+63 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
            contactEmail=contact_email,
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
            headerImage="",
            latitude=lat,
            longitude=lng,
            reviews=random.randint(0, 120),
            description=random.choice(
                [
                    "A relaxed tropical hideaway with airy rooms, lush gardens, and easy beach access.",
                    "A boutique resort with a calm pool deck, modern cottages, and sunset views.",
                    "An eco-friendly retreat focused on comfort, local experiences, and island adventures.",
                ]
            ),
            province=province,
        )

        # Keep the redundant M2M on Places_v2 in sync (your schema has both FK + M2M).
        place.resortItem.add(resort)

        return resort

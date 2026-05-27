from __future__ import annotations

from urllib.parse import quote
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save
from django.utils import timezone
from django.utils.text import slugify

from home.models import Places_v2, SiargaoEventSchedule
from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


def img(photo_id: str, width: int = 1200) -> str:
    return f"https://images.unsplash.com/{photo_id}?w={width}&q=80"


DEMO_RESORTS = [
    {
        "place": {"name": "Demo Siargao Island", "slug": "demo-siargao"},
        "name": "Demo Siargao Surf Villas",
        "address": "Tourism Road, General Luna, Siargao Island",
        "province": "Surigao del Norte",
        "lat": 9.8067,
        "lng": 126.1586,
        "phone": "+63 900 000 1001",
        "email": "demo-siargao@paratara.com",
        "whatsapp": "+63 900 000 1001",
        "hours": "Daily 7:00 AM - 10:00 PM",
        "header": img("photo-1507525428034-b723cf961d3e", 1600),
        "gallery": [
            img("photo-1507525428034-b723cf961d3e"),
            img("photo-1519046904884-53103b34b206"),
            img("photo-1571003123894-1f0594d2b5d9"),
            img("photo-1520250497591-112f2f40a3f4"),
            img("photo-1539635278303-d4002c07eae3"),
            img("photo-1555396273-367ea4eb4db5"),
        ],
        "description": (
            "A polished demo listing for a surf-side resort: beachfront rooms, guided island "
            "experiences, food menus, QR sharing, booking inquiries, and payment-ready offers "
            "in one mobile-friendly page."
        ),
        "amenities": {
            "has_wifi": True,
            "has_pool": True,
            "has_bidet": True,
            "has_parking": True,
            "has_restaurant": True,
            "has_bar": True,
            "has_beach_access": True,
            "has_air_conditioning": True,
            "has_hot_water": True,
            "has_breakfast": True,
            "family_friendly": True,
            "has_generator": True,
            "accepts_gcash": True,
            "accepts_cash": True,
            "accepts_debit_card": True,
            "accepts_credit_card": True,
        },
        "groups": {
            "accommodations": {
                "title": "Beachfront Stays",
                "items": [
                    {
                        "title": "Ocean Balcony Studio",
                        "description": "King room facing the surf break with balcony seating and work desk.",
                        "information": "Breakfast, WiFi, Air conditioning, Hot shower, Beach access",
                        "price": 4200,
                        "images": [img("photo-1520250497591-112f2f40a3f4"), img("photo-1571003123894-1f0594d2b5d9")],
                    },
                    {
                        "title": "Family Garden Villa",
                        "description": "Two-bedroom villa with shaded patio, pantry, and easy pool access.",
                        "information": "Good for 5 guests, Kitchenette, Pool access, Generator backup, Parking",
                        "price": 7800,
                        "images": [img("photo-1500530855697-b586d89ba3ee"), img("photo-1540541338287-41700207dee6")],
                    },
                    {
                        "title": "Surfer Twin Room",
                        "description": "Compact twin room for riders who need clean beds and quick beach access.",
                        "information": "Twin beds, Board rack, WiFi, Shared lounge, Breakfast add-on",
                        "price": 2200,
                        "images": [img("photo-1571896349842-33c89424de2d"), img("photo-1519046904884-53103b34b206")],
                    },
                ],
            },
            "promotions": {
                "title": "Limited Surf Deals",
                "items": [
                    {
                        "title": "3D2N Surf Workation",
                        "description": "Room, breakfast, coworking table, and two beginner surf sessions.",
                        "information": "Two nights, Daily breakfast, Two lessons, Airport transfer discount",
                        "price": 9800,
                        "images": [img("photo-1539635278303-d4002c07eae3"), img("photo-1507525428034-b723cf961d3e")],
                    },
                    {
                        "title": "Private Sunset Dinner",
                        "description": "Beachfront table for two with grilled seafood and mocktails.",
                        "information": "Good for 2, Reservation required, Weather dependent, Photo spot included",
                        "price": 2600,
                        "images": [img("photo-1555396273-367ea4eb4db5"), img("photo-1519046904884-53103b34b206")],
                    },
                ],
            },
            "activities": {
                "title": "Surf and Island Activities",
                "items": [
                    {
                        "title": "Beginner Surf Lesson",
                        "description": "Two-hour guided lesson with board rental and beach safety briefing.",
                        "information": "Board rental, Rash guard, Instructor, Photos on request",
                        "price": 1500,
                        "images": [img("photo-1539635278303-d4002c07eae3"), img("photo-1507525428034-b723cf961d3e")],
                    },
                    {
                        "title": "Tri-Island Day Tour",
                        "description": "Shared boat tour to Guyam, Daku, and Naked Island.",
                        "information": "Boat, Guide, Lunch, Snorkel stop, Pickup available",
                        "price": 1850,
                        "images": [img("photo-1519046904884-53103b34b206"), img("photo-1507525428034-b723cf961d3e")],
                    },
                ],
            },
            "food": {
                "title": "Cafe and Bar Menu",
                "items": [
                    {
                        "title": "Island Breakfast Board",
                        "description": "Eggs, local fruit, toast, coconut jam, and brewed coffee.",
                        "information": "Breakfast, Vegetarian option, Served until 11 AM",
                        "price": 420,
                        "images": [img("photo-1555396273-367ea4eb4db5")],
                    },
                    {
                        "title": "Grilled Seafood Set",
                        "description": "Fresh catch, prawns, rice, salad, and house dipping sauces.",
                        "information": "Good for 2, GCash accepted, Subject to market catch",
                        "price": 1350,
                        "images": [img("photo-1551882547-ff40c63fe5fa")],
                    },
                ],
            },
        },
    },
    {
        "place": {"name": "Demo Panglao Island", "slug": "demo-panglao"},
        "name": "Demo Panglao Coral Garden Resort",
        "address": "Alona access road, Panglao Island, Bohol",
        "province": "Bohol",
        "lat": 9.5489,
        "lng": 123.7727,
        "phone": "+63 900 000 1002",
        "email": "demo-panglao@paratara.com",
        "whatsapp": "+63 900 000 1002",
        "hours": "Daily 8:00 AM - 9:30 PM",
        "header": img("photo-1540541338287-41700207dee6", 1600),
        "gallery": [
            img("photo-1540541338287-41700207dee6"),
            img("photo-1571896349842-33c89424de2d"),
            img("photo-1500530855697-b586d89ba3ee"),
            img("photo-1551882547-ff40c63fe5fa"),
            img("photo-1519046904884-53103b34b206"),
            img("photo-1571003123894-1f0594d2b5d9"),
        ],
        "description": (
            "A polished demo for a boutique Bohol stay with villa packages, diving-style "
            "activities, restaurant menu cards, QR sharing, and inquiry flow for direct bookings."
        ),
        "amenities": {
            "has_wifi": True,
            "has_pool": True,
            "has_bidet": True,
            "has_parking": True,
            "has_restaurant": True,
            "has_spa": True,
            "has_beach_access": True,
            "has_air_conditioning": True,
            "has_hot_water": True,
            "has_breakfast": True,
            "has_laundry": True,
            "family_friendly": True,
            "accepts_gcash": True,
            "accepts_cash": True,
            "accepts_debit_card": True,
            "accepts_credit_card": True,
        },
        "groups": {
            "accommodations": {
                "title": "Poolside Villas",
                "items": [
                    {
                        "title": "Coral Pool Suite",
                        "description": "Ground-floor suite with pool steps, king bed, and quiet garden view.",
                        "information": "Breakfast, Pool access, WiFi, Hot shower, Daily housekeeping",
                        "price": 5200,
                        "images": [img("photo-1540541338287-41700207dee6"), img("photo-1571896349842-33c89424de2d")],
                    },
                    {
                        "title": "Two-Bedroom Family Villa",
                        "description": "Spacious villa for families joining island tours and countryside trips.",
                        "information": "Good for 6 guests, Kitchenette, Private patio, Parking, Laundry service",
                        "price": 8900,
                        "images": [img("photo-1500530855697-b586d89ba3ee"), img("photo-1520250497591-112f2f40a3f4")],
                    },
                ],
            },
            "promotions": {
                "title": "Bohol Stay Offers",
                "items": [
                    {
                        "title": "Dive and Stay Starter",
                        "description": "Two nights, breakfast, gear orientation, and reef briefing.",
                        "information": "Two nights, Breakfast, Gear briefing, Transfer assistance",
                        "price": 11200,
                        "images": [img("photo-1519046904884-53103b34b206"), img("photo-1540541338287-41700207dee6")],
                    },
                    {
                        "title": "Family Pool Day Pass",
                        "description": "Pool use, snack credits, towels, and changing room access.",
                        "information": "Good for 4, Towels, Snack credit, Kids pool, Reservation required",
                        "price": 1800,
                        "images": [img("photo-1571003123894-1f0594d2b5d9"), img("photo-1540541338287-41700207dee6")],
                    },
                ],
            },
            "activities": {
                "title": "Bohol Experiences",
                "items": [
                    {
                        "title": "Balicasag Snorkel Assist",
                        "description": "Boat coordination and guide support for reef snorkeling guests.",
                        "information": "Boat assist, Guide, Mask rental, Safety briefing",
                        "price": 2400,
                        "images": [img("photo-1519046904884-53103b34b206"), img("photo-1507525428034-b723cf961d3e")],
                    },
                    {
                        "title": "Countryside Transfer",
                        "description": "Private car coordination for Chocolate Hills, Loboc, and tarsier stops.",
                        "information": "Private car, Driver, Pickup, Flexible stops",
                        "price": 3800,
                        "images": [img("photo-1506744038136-46273834b3fb"), img("photo-1500534314209-a25ddb2bd429")],
                    },
                ],
            },
            "food": {
                "title": "Pool Cafe Menu",
                "items": [
                    {
                        "title": "Bohol Breakfast Plate",
                        "description": "Garlic rice, eggs, local sausage, fruit, and tablea drink.",
                        "information": "Breakfast, Local favorite, Served until 10:30 AM",
                        "price": 390,
                        "images": [img("photo-1555396273-367ea4eb4db5")],
                    },
                    {
                        "title": "Poolside Pizza Set",
                        "description": "Stone-style pizza, fries, and two iced drinks.",
                        "information": "Good for 2, Pool snack, GCash accepted",
                        "price": 720,
                        "images": [img("photo-1551882547-ff40c63fe5fa")],
                    },
                ],
            },
        },
    },
    {
        "place": {"name": "Demo Baguio Highlands", "slug": "demo-baguio"},
        "name": "Demo Baguio Pine View Lodge",
        "address": "Outlook Drive, Baguio City",
        "province": "Benguet",
        "lat": 16.4145,
        "lng": 120.5996,
        "phone": "+63 900 000 1003",
        "email": "demo-baguio@paratara.com",
        "whatsapp": "+63 900 000 1003",
        "hours": "Front desk 6:00 AM - 11:00 PM",
        "header": img("photo-1500534314209-a25ddb2bd429", 1600),
        "gallery": [
            img("photo-1500534314209-a25ddb2bd429"),
            img("photo-1441974231531-c6227db76b6e"),
            img("photo-1501785888041-af3ef285b470"),
            img("photo-1520250497591-112f2f40a3f4"),
            img("photo-1555396273-367ea4eb4db5"),
            img("photo-1506744038136-46273834b3fb"),
        ],
        "description": (
            "A polished mountain-lodge demo showing how Paratara can sell beyond beach "
            "resorts: rooms, cafe items, guided city transfers, QR sharing, and booking inquiries."
        ),
        "amenities": {
            "has_wifi": True,
            "has_bidet": True,
            "has_parking": True,
            "has_restaurant": True,
            "has_bar": True,
            "has_spa": True,
            "has_gym": False,
            "has_air_conditioning": False,
            "has_hot_water": True,
            "has_breakfast": True,
            "has_laundry": True,
            "pet_friendly": True,
            "family_friendly": True,
            "has_generator": True,
            "accepts_gcash": True,
            "accepts_cash": True,
            "accepts_debit_card": True,
            "accepts_credit_card": True,
        },
        "groups": {
            "accommodations": {
                "title": "Cabin Rooms",
                "items": [
                    {
                        "title": "Pine View Queen Room",
                        "description": "Warm wood room with queen bed, work table, and foggy hillside view.",
                        "information": "Breakfast, WiFi, Hot shower, Parking, Coffee set",
                        "price": 3600,
                        "images": [img("photo-1501785888041-af3ef285b470"), img("photo-1520250497591-112f2f40a3f4")],
                    },
                    {
                        "title": "Family Fireplace Suite",
                        "description": "Large suite with lounge area for families and long-weekend groups.",
                        "information": "Good for 5 guests, Lounge, Hot shower, Breakfast, Pet friendly",
                        "price": 6800,
                        "images": [img("photo-1500530855697-b586d89ba3ee"), img("photo-1441974231531-c6227db76b6e")],
                    },
                ],
            },
            "promotions": {
                "title": "Highland Packages",
                "items": [
                    {
                        "title": "Foggy Weekend Escape",
                        "description": "Two-night stay with breakfast, late checkout, and cafe credits.",
                        "information": "Two nights, Breakfast, Cafe credit, Late checkout",
                        "price": 8500,
                        "images": [img("photo-1500534314209-a25ddb2bd429"), img("photo-1506744038136-46273834b3fb")],
                    },
                    {
                        "title": "Barkada Bonfire Add-On",
                        "description": "Evening fire pit setup with snacks and warm drinks.",
                        "information": "Good for 6, Snacks, Hot drinks, Weather dependent",
                        "price": 1900,
                        "images": [img("photo-1441974231531-c6227db76b6e"), img("photo-1501785888041-af3ef285b470")],
                    },
                ],
            },
            "activities": {
                "title": "City and Nature Services",
                "items": [
                    {
                        "title": "Baguio City Loop Transfer",
                        "description": "Driver-assisted half-day route for mines view, parks, and market stops.",
                        "information": "Private car, Driver, Pickup, Flexible stops",
                        "price": 2800,
                        "images": [img("photo-1506744038136-46273834b3fb"), img("photo-1500534314209-a25ddb2bd429")],
                    },
                    {
                        "title": "Cafe Workday Pass",
                        "description": "Quiet table, fast WiFi, bottomless coffee, and lunch set.",
                        "information": "WiFi, Power outlet, Coffee, Lunch set, Good for remote work",
                        "price": 650,
                        "images": [img("photo-1555396273-367ea4eb4db5"), img("photo-1520250497591-112f2f40a3f4")],
                    },
                ],
            },
            "food": {
                "title": "Highland Cafe Menu",
                "items": [
                    {
                        "title": "Strawberry Breakfast Tray",
                        "description": "Eggs, toast, jam, fresh strawberries, and Benguet coffee.",
                        "information": "Breakfast, Local produce, Served until 11 AM",
                        "price": 450,
                        "images": [img("photo-1555396273-367ea4eb4db5")],
                    },
                    {
                        "title": "Campfire Cocoa Set",
                        "description": "Hot cocoa, cookies, and roasted mallows for cool evenings.",
                        "information": "Good for 2, Evening menu, Kids favorite",
                        "price": 380,
                        "images": [img("photo-1551882547-ff40c63fe5fa")],
                    },
                ],
            },
        },
    },
]


class Command(BaseCommand):
    help = "Seed three polished, presentation-ready demo resort listings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--manager-username",
            default="",
            help="Optional existing user to attach as manager for the demo resorts.",
        )
        parser.add_argument(
            "--local-base-url",
            default="http://127.0.0.1:8000",
            help="Base URL printed for local preview links.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        manager = self._manager(options.get("manager_username", ""))
        local_base_url = (options.get("local_base_url") or "http://127.0.0.1:8000").rstrip("/")

        with self._without_external_side_effect_signals():
            self._delete_auto_events_for_demo_places()
            created = []
            for demo in DEMO_RESORTS:
                resort = self._upsert_resort(demo, manager=manager)
                created.append(resort)

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(created)} polished demo resort listings."))
        for resort in created:
            self.stdout.write(f"- {resort.RealName}")
            self.stdout.write(f"  Public: {local_base_url}/est/{resort.name}/")
            if resort.place:
                self.stdout.write(f"  Friendly: {local_base_url}/{resort.place.slug}/check/{resort.slug}/")

    @contextmanager
    def _without_external_side_effect_signals(self):
        from resorts import signals as resort_signals

        signal_specs = [
            (post_save, resort_signals.link_resort_to_place, resortItem),
            (post_save, resort_signals.create_events_on_promo_created, Packages),
            (m2m_changed, resort_signals.create_event_on_resort_tour_add, resortItem.resortTour.through),
        ]

        disconnected = []
        for signal, receiver, sender in signal_specs:
            if signal.disconnect(receiver=receiver, sender=sender):
                disconnected.append((signal, receiver, sender))

        try:
            yield
        finally:
            for signal, receiver, sender in disconnected:
                signal.connect(receiver=receiver, sender=sender)

    def _delete_auto_events_for_demo_places(self):
        demo_place_slugs = [demo["place"]["slug"] for demo in DEMO_RESORTS]
        SiargaoEventSchedule.objects.filter(place__slug__in=demo_place_slugs).delete()

    def _manager(self, username: str):
        User = get_user_model()
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                self.stdout.write(self.style.WARNING(f"No user found for --manager-username={username}"))
            return user
        return User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()

    def _upsert_resort(self, demo: dict, manager=None) -> resortItem:
        place = self._upsert_place(demo["place"])
        slug = slugify(demo["name"])
        website_url = f"https://www.paratara.com/{place.slug}/check/{slug}/"

        resort = (
            resortItem.objects.filter(slug=slug).first()
            or resortItem.objects.filter(name=slug).first()
            or resortItem()
        )
        resort.is_active = True
        resort.RealName = demo["name"]
        resort.slug = slug
        resort.name = slug
        resort.address = demo["address"]
        resort.place = place
        resort.contactNumber = demo["phone"]
        resort.contactEmail = demo["email"]
        resort.whatsappNumber = demo["whatsapp"]
        resort.open_hours = demo["hours"]
        resort.headerImage = demo["header"]
        resort.latitude = demo["lat"]
        resort.longitude = demo["lng"]
        resort.reviews = max(resort.reviews or 0, 24)
        resort.description = demo["description"]
        resort.province = demo["province"]
        resort.websiteURL = website_url
        resort.last_visited = timezone.now()

        for field, value in demo["amenities"].items():
            setattr(resort, field, value)

        resort.save()

        if resort.resort_ID != resort.id:
            resort.resort_ID = resort.id

        resort.resortQRLink = self._qr_url(website_url)
        resort.save()

        place.resortItem.add(resort)

        if manager:
            resort.adminManager.add(manager)
            if not resort.registeredBy_id:
                resort.registeredBy = manager
                resort.save()

        resort.resortGallery.set([self._image(url) for url in demo["gallery"]])
        self._sync_groups(resort, demo["groups"])
        return resort

    def _upsert_place(self, place_data: dict) -> Places_v2:
        place, _created = Places_v2.objects.get_or_create(
            slug=place_data["slug"],
            defaults={"placename": place_data["name"], "placeID": 0},
        )
        if place.placename != place_data["name"]:
            place.placename = place_data["name"]
            place.save()
        return place

    def _sync_groups(self, resort: resortItem, groups: dict) -> None:
        relation_map = {
            "accommodations": resort.resortAccomodations,
            "promotions": resort.resortTour,
            "activities": resort.resortActivities,
            "food": resort.resortFood,
        }

        for group_key, group_data in groups.items():
            group, _created = resortPackages.objects.get_or_create(
                ItemOfResort=resort,
                PackageTitle=group_data["title"],
            )
            titles = [item["title"] for item in group_data["items"]]
            Packages.objects.filter(packageName=group).exclude(title__in=titles).delete()

            package_items = []
            for item in group_data["items"]:
                package, _created = Packages.objects.update_or_create(
                    packageName=group,
                    title=item["title"],
                    defaults={
                        "description": item["description"],
                        "information": item["information"],
                        "price": item["price"],
                        "website": item.get("website") or "",
                        "is_available": item.get("is_available", True),
                    },
                )
                package.ImageURL.set([self._image(url) for url in item["images"]])
                package_items.append(package)

            group.subPackages.set(package_items)
            relation_map[group_key].set([group])

    def _image(self, url: str) -> sideImagesURLs:
        image, _created = sideImagesURLs.objects.get_or_create(urlField=url)
        return image

    def _qr_url(self, website_url: str) -> str:
        return f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={quote(website_url, safe='')}"

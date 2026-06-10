import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError, BaseCommand
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from home.models import Places_v2
from home.views import viaje_v2


DEFAULT_PLACE_NAMES = [
    "Batanes",
    "Baguio City",
    "Sagada",
    "Banaue Rice Terraces",
    "Vigan",
    "La Union",
    "Hundred Islands",
    "Subic Bay",
    "Tagaytay",
    "Taal Volcano",
    "Anawangin Cove",
    "Mount Pinatubo",
    "Intramuros",
    "Corregidor Island",
    "Puerto Galera",
    "Apo Reef",
    "Coron",
    "El Nido",
    "Puerto Princesa",
    "San Vicente Palawan",
    "Port Barton",
    "Balabac",
    "Boracay",
    "Iloilo City",
    "Guimaras",
    "Bacolod",
    "Sipalay",
    "Dumaguete",
    "Apo Island",
    "Siquijor",
    "Cebu City",
    "Moalboal",
    "Bantayan Island",
    "Malapascua Island",
    "Oslob",
    "Bohol",
    "Panglao Island",
    "Camiguin",
    "Cagayan de Oro",
    "Bukidnon",
    "Davao City",
    "Samal Island",
    "Mount Apo",
    "Siargao Island",
    "Surigao City",
    "Dinagat Islands",
    "Sohoton Cove",
    "Zamboanga City",
    "Lake Sebu",
    "General Santos",
    "Mati",
    "Dahican Beach",
    "Kalanggaman Island",
    "Leyte",
    "Samar",
    "Biri Island",
    "Caramoan",
    "Mayon Volcano",
    "Donsol",
    "Calaguas Islands",
    "Catanduanes",
    "Marinduque",
    "Romblon",
    "Masbate",
    "Camotes Islands",
    "Gigantes Islands",
    "Antique",
    "Capiz",
    "Zambales",
    "Batangas",
    "Laiya",
    "Nasugbu",
    "Tanay Rizal",
    "Masungi Georeserve",
    "Jomalig Island",
    "Polillo Island",
    "Quezon Province",
    "Pagudpud",
    "Laoag",
    "Paoay",
    "San Juan La Union",
    "Atok Benguet",
    "Kabayan Benguet",
    "Buscalan",
    "Kalinga",
    "Tuguegarao",
    "Palaui Island",
    "Isabela",
    "Quirino Province",
    "Nueva Vizcaya",
    "Aurora",
    "Baler",
    "Dingalan",
    "Sorsogon",
    "Legazpi City",
    "Naga City",
    "Tacloban",
    "Ormoc",
    "Iligan City",
    "Ozamis City",
]


class Command(BaseCommand):
    help = "Create random destination places by submitting default data through viaje_v2."

    def add_arguments(self, parser):
        parser.add_argument("count", type=int, help="Number of new places to create.")
        parser.add_argument(
            "--username",
            help="User account to use as the schedule poster. Defaults to the first superuser, staff user, or active user.",
        )
        parser.add_argument("--seed", type=int, help="Seed for repeatable random selection.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without creating anything.")
        parser.add_argument("--meet-place", default="Cebu City", help="Default meet place.")
        parser.add_argument("--contact", default="", help="Default contact. Defaults to the selected user's email.")
        parser.add_argument("--travel-type", default="RIDE", help="Default scheduleTravelType value.")
        parser.add_argument("--mode", default="Passenger", help="Default scheduleTypeAndMode value.")
        parser.add_argument("--maker-or-looker", default="Find", help="Default MakerOrLooker value.")

    def handle(self, *args, **options):
        count = options["count"]
        if count < 1:
            raise CommandError("count must be at least 1.")

        rng = random.Random(options["seed"])
        user = self._get_user(options.get("username"))
        candidates = DEFAULT_PLACE_NAMES[:]
        rng.shuffle(candidates)

        created = 0
        skipped = 0
        attempted = 0

        for place_name in candidates:
            if created >= count:
                break

            attempted += 1
            if Places_v2.objects.filter(placename__iexact=place_name).exists():
                skipped += 1
                self.stdout.write(f"Skipping existing place: {place_name}")
                continue

            if options["dry_run"]:
                created += 1
                self.stdout.write(f"Would create: {place_name}")
                continue

            response = self._submit_to_viaje(place_name, user, created, options)
            if 300 <= getattr(response, "status_code", 0) < 400:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created through viaje_v2: {place_name}"))
            else:
                status_code = getattr(response, "status_code", "unknown")
                self.stdout.write(self.style.WARNING(f"Unexpected response for {place_name}: {status_code}"))

        if created < count:
            remaining = count - created
            raise CommandError(
                f"Created {created}, but still need {remaining}. "
                f"Only {attempted} candidate names were available after skipping {skipped} existing places."
            )

        verb = "Would create" if options["dry_run"] else "Created"
        self.stdout.write(self.style.SUCCESS(f"{verb} {created} place(s). Skipped {skipped} existing place(s)."))

    def _get_user(self, username):
        UserModel = get_user_model()
        if username:
            user = UserModel.objects.filter(username=username).first()
            if user is None:
                raise CommandError(f'No user found with username "{username}".')
            return user

        user = UserModel.objects.filter(is_superuser=True).order_by("id").first()
        if user is None:
            user = UserModel.objects.filter(is_staff=True).order_by("id").first()
        if user is None:
            user = UserModel.objects.filter(is_active=True).order_by("id").first()
        if user is None:
            raise CommandError("No user exists. Create a user first or pass --username.")
        return user

    def _submit_to_viaje(self, place_name, user, index, options):
        meet_date = timezone.localtime(timezone.now() + timedelta(days=index + 1)).replace(
            hour=9,
            minute=0,
            second=0,
            microsecond=0,
        )
        contact = options["contact"] or getattr(user, "email", "") or "admin@example.com"
        post_data = {
            "placenameschedule": place_name,
            "meetDate": [meet_date.strftime("%Y-%m-%dT%H:%M")],
            "meetPlace": options["meet_place"],
            "scheduleCost": "",
            "theDetails": f"Auto-created default schedule for {place_name}.",
            "detailsContact": contact,
            "MakerOrLooker": options["maker_or_looker"],
            "additionalDetails": "Created by create_random_viaje_places management command.",
            "scheduleWebsite": "",
            "scheduleTravelType": options["travel_type"],
            "scheduleTypeAndMode": options["mode"],
        }

        factory = RequestFactory()
        request = factory.post(reverse("home:viaje"), data=post_data)
        request.user = user
        return viaje_v2(request)

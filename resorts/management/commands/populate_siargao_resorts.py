from django.core.management.base import BaseCommand
from django.db import transaction

from resorts.models import resortItem
from home.models import Places_v2


class Command(BaseCommand):
    help = "Create ten resortItem records for Siargao in the database"

    def handle(self, *args, **kwargs):
        try:
            siargao_place = Places_v2.objects.get(placename__iexact="Siargao")
        except Places_v2.DoesNotExist:
            self.stdout.write(self.style.ERROR('Place "Siargao" does not exist.'))
            return

        resort_templates = [
            {
                "RealName": "Cloud Nine Breeze",
                "address": "Cloud 9, General Luna",
                "contactEmail": "cloud9@siargaopalace.com",
            },
            {
                "RealName": "Sapphire Surf Retreat",
                "address": "Tourist Village, General Luna",
                "contactEmail": "sapphire@siargaopalace.com",
            },
            {
                "RealName": "Tidal Pools Hideaway",
                "address": "Pacifico, General Luna",
                "contactEmail": "tidal@siargaopalace.com",
            },
            {
                "RealName": "Luna Lagoon Villas",
                "address": "Madison Beach, General Luna",
                "contactEmail": "lagoon@siargaopalace.com",
            },
            {
                "RealName": "Fisherman’s Wharf Inn",
                "address": "General Luna Port",
                "contactEmail": "wharf@siargaopalace.com",
            },
            {
                "RealName": "Sunset Sand Dunes",
                "address": "Alegria Coastline",
                "contactEmail": "sunset@siargaopalace.com",
            },
            {
                "RealName": "Coral Bloom Residences",
                "address": "Dapa Bayview",
                "contactEmail": "coral@siargaopalace.com",
            },
            {
                "RealName": "Palm Canopy Escape",
                "address": "Malinao, San Isidro",
                "contactEmail": "canopy@siargaopalace.com",
            },
            {
                "RealName": "Island Echo Suites",
                "address": "Bubuan Road, General Luna",
                "contactEmail": "echo@siargaopalace.com",
            },
            {
                "RealName": "Laguna Pebble Resort",
                "address": "Carlos P. Garcia Avenue",
                "contactEmail": "laguna@siargaopalace.com",
            },
        ]

        created = []
        with transaction.atomic():
            for idx, template in enumerate(resort_templates, start=1):
                resort = resortItem.objects.create(
                    RealName=template["RealName"],
                    address=template["address"],
                    place=siargao_place,
                    contactNumber=f"09123{idx:05d}678",
                    contactEmail=template["contactEmail"],
                    whatsappNumber=f"09123{idx:05d}678",
                    promotionalVideo=f"https://youtube.com/channel/UCsiargao{idx}",
                    virtualpicture=f"https://cdn.example.com/virtual/{idx}.jpg",
                    headerImage=f"https://cdn.example.com/header/{idx}.jpg",
                    latitude=9.85 + (idx * 0.01),
                    longitude=126.05 + (idx * 0.01),
                    reviews=idx * 3,
                    description=f"Signature resort #{idx} on Siargao with premium amenities.",
                    province="Surigao del Norte",
                )
                created.append(resort)
                self.stdout.write(self.style.SUCCESS(f"Created {resort.RealName} (ID: {resort.id})"))

        self.stdout.write(self.style.SUCCESS(f"Successfully populated {len(created)} resorts for Siargao."))

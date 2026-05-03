from django.core.management.base import BaseCommand
from resorts.models import resortItem
from home.models import Places_v2
from userProfile.models import UserCredentials
import random

class Command(BaseCommand):
    help = 'Populate resortItem model with sample data'

    def handle(self, *args, **options):
        # Sample data for resorts
        resorts_data = [
            {
                'RealName': 'Paradise Beach Resort',
                'address': '123 Beachfront Avenue, Siargao Island',
                'contactNumber': '+63 917 123 4567',
                'contactEmail': 'info@paradisebeach.com',
                'whatsappNumber': '+63 917 123 4567',
                'promotionalVideo': 'https://example.com/video1.mp4',
                'virtualpicture': 'https://example.com/virtual1.jpg',
                'headerImage': 'https://example.com/header1.jpg',
                'latitude': 9.8558,
                'longitude': 126.0323,
                'reviews': random.randint(10, 100),
                'description': 'A luxurious beach resort offering stunning views of the Pacific Ocean with world-class amenities.',
                'province': 'Surigao del Norte',
            },
            {
                'RealName': 'Mountain View Eco Resort',
                'address': '456 Mountain Trail, Cloud 9, Siargao',
                'contactNumber': '+63 918 234 5678',
                'contactEmail': 'reservations@mountainview.com',
                'whatsappNumber': '+63 918 234 5678',
                'promotionalVideo': 'https://example.com/video2.mp4',
                'virtualpicture': 'https://example.com/virtual2.jpg',
                'headerImage': 'https://example.com/header2.jpg',
                'latitude': 9.8667,
                'longitude': 126.0333,
                'reviews': random.randint(10, 100),
                'description': 'An eco-friendly resort nestled in the mountains, perfect for nature lovers and adventure seekers.',
                'province': 'Surigao del Norte',
            },
            {
                'RealName': 'Island Paradise Resort',
                'address': '789 Island Road, General Luna, Siargao',
                'contactNumber': '+63 919 345 6789',
                'contactEmail': 'hello@islandparadise.com',
                'whatsappNumber': '+63 919 345 6789',
                'promotionalVideo': 'https://example.com/video3.mp4',
                'virtualpicture': 'https://example.com/virtual3.jpg',
                'headerImage': 'https://example.com/header3.jpg',
                'latitude': 9.7833,
                'longitude': 126.1667,
                'reviews': random.randint(10, 100),
                'description': 'A tropical paradise resort with private villas, infinity pools, and direct beach access.',
                'province': 'Surigao del Norte',
            },
        ]

        # Get or create a sample place
        place, created = Places_v2.objects.get_or_create(
            placename='Siargao Island',
            defaults={'placeID': 1}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created place: {place.placename}'))

        # Get or create a sample user
        user, created = UserCredentials.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {user.username}'))

        # Create resort items
        for i, resort_data in enumerate(resorts_data, 1):
            resort, created = resortItem.objects.get_or_create(
                RealName=resort_data['RealName'],
                defaults={
                    'resort_ID': i,
                    'address': resort_data['address'],
                    'place': place,
                    'contactNumber': resort_data['contactNumber'],
                    'contactEmail': resort_data['contactEmail'],
                    'whatsappNumber': resort_data['whatsappNumber'],
                    'promotionalVideo': resort_data['promotionalVideo'],
                    'virtualpicture': resort_data['virtualpicture'],
                    'headerImage': resort_data['headerImage'],
                    'latitude': resort_data['latitude'],
                    'longitude': resort_data['longitude'],
                    'reviews': resort_data['reviews'],
                    'description': resort_data['description'],
                    'province': resort_data['province'],
                    'registeredBy': user,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created resort: {resort.RealName}'))
            else:
                self.stdout.write(f'Resort already exists: {resort.RealName}')

        self.stdout.write(self.style.SUCCESS('Successfully populated resortItem model with sample data'))
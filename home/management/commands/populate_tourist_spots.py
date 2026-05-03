from django.core.management.base import BaseCommand
from home.models import TouristSpot, Places_v2

class Command(BaseCommand):
    help = 'Populate TouristSpot with sample data'

    def handle(self, *args, **options):
        # Sample data for tourist spots
        spots_data = [
            {
                'place_slug': 'siargao',
                'name': 'Cloud 9',
                'desc': 'Famous surfing spot in Siargao.',
                'img': 'https://example.com/cloud9.jpg',
                'url': 'https://en.wikipedia.org/wiki/Cloud_9_(wave)',
                'coords': {'lat': 9.8606, 'lng': 126.1700}
            },
            {
                'place_slug': 'siargao',
                'name': 'Magpupungko Rock Pools',
                'desc': 'Natural rock pools perfect for swimming.',
                'img': 'https://example.com/magpupungko.jpg',
                'url': 'https://www.tripadvisor.com/Attraction_Review-g780138-d10412374-Reviews-Magpupungko_Rock_Pools-Siargao_Surigao_del_Norte_Province_Mindanao.html',
                'coords': {'lat': 9.8667, 'lng': 126.1833}
            },
            {
                'place_slug': 'siargao',
                'name': 'Sugba Lagoon',
                'desc': 'Beautiful lagoon with crystal clear waters.',
                'img': 'https://example.com/sugba.jpg',
                'url': 'https://www.tripadvisor.com/Attraction_Review-g780138-d10412375-Reviews-Sugba_Lagoon-Siargao_Surigao_del_Norte_Province_Mindanao.html',
                'coords': {'lat': 9.8500, 'lng': 126.1667}
            },
            {
                'place_slug': 'boracay',
                'name': 'White Beach',
                'desc': 'Iconic white sand beach in Boracay.',
                'img': 'https://example.com/whitebeach.jpg',
                'url': 'https://en.wikipedia.org/wiki/Boracay',
                'coords': {'lat': 11.9674, 'lng': 121.9244}
            },
            {
                'place_slug': 'boracay',
                'name': 'Puka Beach',
                'desc': 'Secluded beach with clear waters.',
                'img': 'https://example.com/pukabeach.jpg',
                'url': 'https://www.tripadvisor.com/Attraction_Review-g298460-d10412376-Reviews-Puka_Beach-Boracay_Aklan_Province_Panay_Island_Visayas.html',
                'coords': {'lat': 11.9667, 'lng': 121.9250}
            },
            {
                'place_slug': 'boracay',
                'name': 'Diniwid Beach',
                'desc': 'Less crowded beach perfect for relaxation.',
                'img': 'https://example.com/diniwid.jpg',
                'url': 'https://www.tripadvisor.com/Attraction_Review-g298460-d10412377-Reviews-Diniwid_Beach-Boracay_Aklan_Province_Panay_Island_Visayas.html',
                'coords': {'lat': 11.9672, 'lng': 121.9267}
            },
            {
                'place_slug': 'boracay',
                'name': 'Mount Luho',
                'desc': 'Viewpoint offering panoramic views of Boracay.',
                'img': 'https://example.com/mountluho.jpg',
                'url': 'https://www.tripadvisor.com/Attraction_Review-g298460-d10412378-Reviews-Mount_Luho-Boracay_Aklan_Province_Panay_Island_Visayas.html',
                'coords': {'lat': 11.9678, 'lng': 121.9222}
            },
            # Add more spots as needed
        ]

        for spot_data in spots_data:
            try:
                place = Places_v2.objects.get(slug=spot_data['place_slug'])
                spot, created = TouristSpot.objects.get_or_create(
                    place=place,
                    name=spot_data['name'],
                    defaults={
                        'desc': spot_data['desc'],
                        'img': spot_data['img'],
                        'url': spot_data['url'],
                        'coords': spot_data['coords']
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created tourist spot: {spot.name}'))
                else:
                    self.stdout.write(f'Tourist spot already exists: {spot.name}')
            except Places_v2.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Place not found: {spot_data["place_slug"]}'))

        self.stdout.write(self.style.SUCCESS('TouristSpot population completed.'))
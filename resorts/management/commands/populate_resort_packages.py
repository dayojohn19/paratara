from django.core.management.base import BaseCommand
from resorts.models import resortItem, resortPackages, Packages, sideImagesURLs
from home.models import allSchedules
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate resort packages, sub-packages, and images for existing resorts'

    def handle(self, *args, **options):
        # Get the three resorts we created
        resorts = resortItem.objects.filter(
            RealName__in=['Paradise Beach Resort', 'Mountain View Eco Resort', 'Island Paradise Resort']
        )

        if not resorts.exists():
            self.stdout.write(self.style.ERROR('No resorts found. Please run populate_resort_items first.'))
            return

        # Sample image URLs (working placeholder images)
        sample_images = [
            'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=400',  # Beach resort
            'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=400',  # Mountain view
            'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=400',  # Island paradise
            'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400',  # Room interior
            'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400',  # Restaurant
            'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',  # Activity
            'https://images.unsplash.com/photo-1539635278303-d4002c07eae3?w=400',  # Tour
            'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400',  # Food
        ]

        # Create image URLs
        image_objects = []
        for url in sample_images:
            img, created = sideImagesURLs.objects.get_or_create(urlField=url)
            image_objects.append(img)
            if created:
                self.stdout.write(f'Created image: {url}')

        # Sample data for different categories
        accommodations_data = [
            {
                'title': 'Deluxe Ocean View Room',
                'description': 'Spacious room with breathtaking ocean views, king bed, and private balcony.',
                'information': 'Includes complimentary breakfast, WiFi, and 24/7 room service.',
                'price': 4500,
            },
            {
                'title': 'Garden Villa Suite',
                'description': 'Private villa surrounded by tropical gardens with plunge pool.',
                'information': 'Perfect for families, includes kitchenette and outdoor dining area.',
                'price': 6500,
            },
        ]

        activities_data = [
            {
                'title': 'Island Hopping Adventure',
                'description': 'Full day tour visiting nearby islands with snorkeling and beach activities.',
                'information': 'Includes equipment, lunch, and professional guide.',
                'price': 2800,
            },
            {
                'title': 'Surfing Lessons',
                'description': 'Professional surfing instruction for all skill levels.',
                'information': '2-hour session with board rental and safety equipment.',
                'price': 1500,
            },
        ]

        food_data = [
            {
                'title': 'Seafood Platter',
                'description': 'Fresh grilled fish, prawns, and calamari with tropical salsa.',
                'information': 'Served with jasmine rice and seasonal vegetables.',
                'price': 850,
            },
            {
                'title': 'Tropical Fruit Salad',
                'description': 'Fresh seasonal fruits with coconut yogurt and honey drizzle.',
                'information': 'Healthy and refreshing, perfect for any meal.',
                'price': 350,
            },
        ]

        tour_data = [
            {
                'title': 'Sunset Beach Tour',
                'description': 'Romantic sunset walk along pristine beaches with champagne toast.',
                'information': 'Includes transportation and photo session.',
                'price': 1200,
            },
            {
                'title': 'Cultural Village Experience',
                'description': 'Visit local villages, learn traditional crafts, and enjoy cultural performances.',
                'information': 'Full day experience with lunch and souvenirs.',
                'price': 2200,
            },
        ]

        # Get some sample schedules
        schedules = list(allSchedules.objects.all()[:3])  # Get first 3 schedules

        for resort in resorts:
            self.stdout.write(f'\nProcessing resort: {resort.RealName}')

            # Create accommodations
            accom_package, created = resortPackages.objects.get_or_create(
                PackageTitle=f'Accommodations at {resort.RealName}',
                ItemOfResort=resort
            )
            if created:
                self.stdout.write(f'  Created accommodations package')

            for i, accom_data in enumerate(accommodations_data):
                package, created = Packages.objects.get_or_create(
                    packageName=accom_package,
                    title=accom_data['title'],
                    defaults={
                        'description': accom_data['description'],
                        'information': accom_data['information'],
                        'price': accom_data['price'],
                    }
                )
                if created:
                    # Add random images
                    package.ImageURL.add(*random.sample(image_objects, 2))
                    self.stdout.write(f'    Created accommodation: {package.title}')
                
                # Ensure the package is in the subPackages ManyToManyField
                if package not in accom_package.subPackages.all():
                    accom_package.subPackages.add(package)

            resort.resortAccomodations.add(accom_package)

            # Create activities
            activity_package, created = resortPackages.objects.get_or_create(
                PackageTitle=f'Activities at {resort.RealName}',
                ItemOfResort=resort
            )
            if created:
                self.stdout.write(f'  Created activities package')

            for i, activity_data in enumerate(activities_data):
                package, created = Packages.objects.get_or_create(
                    packageName=activity_package,
                    title=activity_data['title'],
                    defaults={
                        'description': activity_data['description'],
                        'information': activity_data['information'],
                        'price': activity_data['price'],
                    }
                )
                if created:
                    package.ImageURL.add(*random.sample(image_objects, 2))
                    self.stdout.write(f'    Created activity: {package.title}')
                
                # Ensure the package is in the subPackages ManyToManyField
                if package not in activity_package.subPackages.all():
                    activity_package.subPackages.add(package)

            resort.resortActivities.add(activity_package)

            # Create food
            food_package, created = resortPackages.objects.get_or_create(
                PackageTitle=f'Dining at {resort.RealName}',
                ItemOfResort=resort
            )
            if created:
                self.stdout.write(f'  Created food package')

            for i, food_item in enumerate(food_data):
                package, created = Packages.objects.get_or_create(
                    packageName=food_package,
                    title=food_item['title'],
                    defaults={
                        'description': food_item['description'],
                        'information': food_item['information'],
                        'price': food_item['price'],
                    }
                )
                if created:
                    package.ImageURL.add(*random.sample(image_objects, 1))
                    self.stdout.write(f'    Created food item: {package.title}')
                
                # Ensure the package is in the subPackages ManyToManyField
                if package not in food_package.subPackages.all():
                    food_package.subPackages.add(package)

            resort.resortFood.add(food_package)

            # Create tours
            tour_package, created = resortPackages.objects.get_or_create(
                PackageTitle=f'Tours at {resort.RealName}',
                ItemOfResort=resort
            )
            if created:
                self.stdout.write(f'  Created tours package')

            for i, tour_item in enumerate(tour_data):
                package, created = Packages.objects.get_or_create(
                    packageName=tour_package,
                    title=tour_item['title'],
                    defaults={
                        'description': tour_item['description'],
                        'information': tour_item['information'],
                        'price': tour_item['price'],
                    }
                )
                if created:
                    package.ImageURL.add(*random.sample(image_objects, 2))
                    self.stdout.write(f'    Created tour: {package.title}')
                
                # Ensure the package is in the subPackages ManyToManyField
                if package not in tour_package.subPackages.all():
                    tour_package.subPackages.add(package)

            resort.resortTour.add(tour_package)

            # Add schedules if available
            if schedules:
                resort.resortSchedules.add(*random.sample(schedules, min(2, len(schedules))))
                self.stdout.write(f'  Added {min(2, len(schedules))} schedules')

        self.stdout.write(self.style.SUCCESS('\nSuccessfully populated all resort packages with sample data!'))
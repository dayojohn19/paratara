from django.core.management.base import BaseCommand
from resorts.models import resortItem, Packages, sideImagesURLs
from django.db import transaction

class Command(BaseCommand):
    help = 'Update resort packages with more items and proper images'

    def handle(self, *args, **options):
        # Get the three resorts
        resorts = resortItem.objects.filter(
            RealName__in=['Paradise Beach Resort', 'Mountain View Eco Resort', 'Island Paradise Resort']
        )

        if not resorts.exists():
            self.stdout.write(self.style.ERROR('No resorts found.'))
            return

        # Additional accommodation items
        accom_additions = {
            'Paradise Beach Resort': [
                ('Beachfront Villa', 'https://images.unsplash.com/photo-1520637836862-4d197d17c1a8?w=400', 7500),
                ('Ocean Suite', 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=400', 5500),
                ('Family Bungalow', 'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=400', 8500),
            ],
            'Mountain View Eco Resort': [
                ('Treehouse Cabin', 'https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=400', 4800),
                ('Eco Lodge Room', 'https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=400', 3800),
                ('Mountain Chalet', 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=400', 6200),
            ],
            'Island Paradise Resort': [
                ('Overwater Bungalow', 'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=400', 9200),
                ('Garden Pavilion', 'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=400', 5800),
                ('Private Beach House', 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=400', 7800),
            ]
        }

        # Additional activity items
        activity_additions = {
            'Paradise Beach Resort': [
                ('Sunset Catamaran Cruise', 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400', 3200),
                ('Beach Volleyball Tournament', 'https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=400', 800),
                ('Dolphin Watching Tour', 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400', 2500),
            ],
            'Mountain View Eco Resort': [
                ('Hiking Expedition', 'https://images.unsplash.com/photo-1551632811-561732d1e306?w=400', 1800),
                ('Bird Watching Tour', 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400', 1200),
                ('Photography Workshop', 'https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400', 2200),
            ],
            'Island Paradise Resort': [
                ('Snorkeling Adventure', 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400', 2800),
                ('Cultural Dance Class', 'https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400', 1500),
                ('Spa Treatment Session', 'https://images.unsplash.com/photo-1596178060810-fb4bd482ee2c?w=400', 3500),
            ]
        }

        # Additional tour items
        tour_additions = {
            'Paradise Beach Resort': [
                ('Coral Reef Exploration', 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400', 2400),
                ('Local Market Visit', 'https://images.unsplash.com/photo-1533900298318-6b8da08a36f3?w=400', 600),
                ('Sunrise Yoga Session', 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400', 1000),
            ],
            'Mountain View Eco Resort': [
                ('Waterfall Trek', 'https://images.unsplash.com/photo-1464822759844-d150f39be80d?w=400', 1600),
                ('Coffee Farm Tour', 'https://images.unsplash.com/photo-1459755486867-b55449bb39ff?w=400', 900),
                ('Stargazing Experience', 'https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=400', 1300),
            ],
            'Island Paradise Resort': [
                ('Mangrove Kayaking', 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400', 2000),
                ('Traditional Cooking Class', 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400', 1800),
                ('Fire Dance Show', 'https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400', 1200),
            ]
        }

        # Food items with actual food images (6 each)
        food_data = {
            'Paradise Beach Resort': [
                ('Grilled Seafood Platter', 'https://images.unsplash.com/photo-1559847844-5315695dadae?w=400'),
                ('Fresh Tropical Fruit Bowl', 'https://images.unsplash.com/photo-1490474418585-ba9b6e6e7468?w=400'),
                ('Beachside BBQ Ribs', 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400'),
                ('Coconut Shrimp', 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400'),
                ('Island Poke Bowl', 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400'),
                ('Fresh Mango Salad', 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400')
            ],
            'Mountain View Eco Resort': [
                ('Organic Garden Salad', 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400'),
                ('Mountain Herb Pasta', 'https://images.unsplash.com/photo-1551892376-c73ba8b2b6ad?w=400'),
                ('Fresh Mountain Trout', 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400'),
                ('Wild Mushroom Risotto', 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=400'),
                ('Herb-Crusted Lamb', 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400'),
                ('Forest Berry Tart', 'https://images.unsplash.com/photo-1571771019784-3ff35f4f4277?w=400')
            ],
            'Island Paradise Resort': [
                ('Island Coconut Curry', 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400'),
                ('Fresh Seafood Ceviche', 'https://images.unsplash.com/photo-1574484284002-952d92456975?w=400'),
                ('Tropical Smoothie Bowl', 'https://images.unsplash.com/photo-1571771019784-3ff35f4f4277?w=400'),
                ('Pineapple Fried Rice', 'https://images.unsplash.com/photo-1563379091339-03246963d96c?w=400'),
                ('Grilled Mahi Mahi', 'https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=400'),
                ('Coconut Panna Cotta', 'https://images.unsplash.com/photo-1551024506-0bccd828d307?w=400')
            ]
        }

        # Resort header images
        resort_images = {
            'Paradise Beach Resort': 'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800',
            'Mountain View Eco Resort': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800',
            'Island Paradise Resort': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800'
        }

        # Disable signals temporarily to avoid issues
        from django.db.models.signals import post_save
        from resorts.signals import create_events_on_promo_created
        
        post_save.disconnect(create_events_on_promo_created, sender=Packages)
        
        try:
            with transaction.atomic():
                for resort in resorts:
                    self.stdout.write(f'\nUpdating {resort.RealName}...')

                    # Update resort header image
                    resort.headerImage = resort_images[resort.RealName]
                    resort.save()

                    # Update food items (6 each)
                    food_package = resort.resortFood.first()
                    if food_package:
                        # Delete existing packages entirely
                        food_package.subPackages.all().delete()
                        for title, image_url in food_data[resort.RealName]:
                            package = Packages.objects.create(
                                packageName=food_package,
                                title=title,
                                description=f'Delicious {title.lower()} prepared with fresh local ingredients.',
                                information='Served daily with seasonal accompaniments.',
                                price=250 + food_package.subPackages.count() * 50,
                            )
                            img, _ = sideImagesURLs.objects.get_or_create(urlField=image_url)
                            package.ImageURL.add(img)
                            # Ensure the package is in the subPackages ManyToManyField
                            if package not in food_package.subPackages.all():
                                food_package.subPackages.add(package)

                    # Add additional accommodation items
                    accom_package = resort.resortAccomodations.first()
                    if accom_package:
                        for title, image_url, price in accom_additions[resort.RealName]:
                            package, created = Packages.objects.get_or_create(
                                packageName=accom_package,
                                title=title,
                                defaults={
                                    'description': f'Luxurious {title.lower()} with stunning views and modern amenities.',
                                    'information': 'Includes complimentary breakfast and resort amenities.',
                                    'price': price,
                                }
                            )
                            if created:
                                img, _ = sideImagesURLs.objects.get_or_create(urlField=image_url)
                                package.ImageURL.add(img)
                            # Ensure the package is in the subPackages ManyToManyField
                            if package not in accom_package.subPackages.all():
                                accom_package.subPackages.add(package)
                    activity_package = resort.resortActivities.first()
                    if activity_package:
                        for title, image_url, price in activity_additions[resort.RealName]:
                            package, created = Packages.objects.get_or_create(
                                packageName=activity_package,
                                title=title,
                                defaults={
                                    'description': f'Exciting {title.lower()} for adventure seekers.',
                                    'information': 'Professional guides and all necessary equipment included.',
                                    'price': price,
                                }
                            )
                            if created:
                                img, _ = sideImagesURLs.objects.get_or_create(urlField=image_url)
                                package.ImageURL.add(img)
                            # Ensure the package is in the subPackages ManyToManyField
                            if package not in activity_package.subPackages.all():
                                activity_package.subPackages.add(package)
                    tour_package = resort.resortTour.first()
                    if tour_package:
                        for title, image_url, price in tour_additions[resort.RealName]:
                            package, created = Packages.objects.get_or_create(
                                packageName=tour_package,
                                title=title,
                                defaults={
                                    'description': f'Captivating {title.lower()} showcasing local culture and nature.',
                                    'information': 'Small groups, expert local guides, and memorable experiences.',
                                    'price': price,
                                }
                            )
                            if created:
                                img, _ = sideImagesURLs.objects.get_or_create(urlField=image_url)
                                package.ImageURL.add(img)
                            # Ensure the package is in the subPackages ManyToManyField
                            if package not in tour_package.subPackages.all():
                                tour_package.subPackages.add(package)

        finally:
            # Reconnect the signal
            post_save.connect(create_events_on_promo_created, sender=Packages)

        self.stdout.write(self.style.SUCCESS('\nSuccessfully updated all resorts with additional items and images!'))
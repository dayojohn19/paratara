from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


class Command(BaseCommand):
    help = "Attach ten food packages with images to each Siargao resort"

    def handle(self, *args, **kwargs):
        siargao_resorts = resortItem.objects.filter(place__placename__iexact="Siargao")
        if not siargao_resorts:
            self.stdout.write(self.style.WARNING("No resorts found for Siargao. Please run the population command first."))
            return

        created = 0
        with transaction.atomic():
            for resort in siargao_resorts:
                base_name = resort.RealName or resort.name or f"Resort {resort.id}"
                place_slug = resort.slug or slugify(base_name)

                for idx in range(1, 11):
                    title = f"{base_name} Food Experience {idx}"
                    if resort.resortFood.filter(PackageTitle=title).exists():
                        continue

                    food_package = resortPackages.objects.create(
                        PackageTitle=title,
                        ItemOfResort=resort,
                    )
                    resort.resortFood.add(food_package)

                    menu_item = Packages.objects.create(
                        packageName=food_package,
                        title=f"{title} Menu",
                        description=f"Chef-picked specialty dish #{idx} at {base_name}.",
                        information="Includes seasonal ingredients and island spices.",
                        price=1200 + idx * 150,
                        website=f"https://paratara.com/{place_slug}/food/{idx}",
                    )

                    for image_index in range(1, 3):
                        image_url = f"https://cdn.paratara.com/food/{place_slug}/item-{idx}-{image_index}.jpg"
                        img, _ = sideImagesURLs.objects.get_or_create(urlField=image_url)
                        menu_item.ImageURL.add(img)

                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"Added food package '{title}' to {resort.RealName or resort.name}."))

        self.stdout.write(self.style.SUCCESS(f"Created {created} food packages across {siargao_resorts.count()} resorts."))

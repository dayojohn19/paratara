from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import Packages, resortItem, sideImagesURLs


class Command(BaseCommand):
    help = "Replace image links for resortGallery and foodlist items (Packages.ImageURL)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default=None,
            help='Only update resorts in a specific place (e.g. "Siargao")',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database",
        )

    def handle(self, *args, **kwargs):
        place = kwargs.get("place")
        dry_run = bool(kwargs.get("dry_run"))

        resorts = resortItem.objects.all()
        if place:
            resorts = resorts.filter(place__placename__iexact=place)

        if not resorts.exists():
            self.stdout.write(self.style.WARNING("No resortItem records found for the given filter."))
            return

        gallery_sets = 0
        food_images_sets = 0
        food_items_seen = 0

        def resort_seed(resort: resortItem) -> str:
            base = resort.slug or slugify(resort.RealName or resort.name or f"resort-{resort.id}")
            return base or f"resort-{resort.id}"

        with transaction.atomic():
            for resort in resorts:
                seed = resort_seed(resort)

                # 1) Replace resortGallery with 3 working image URLs
                gallery_imgs = []
                for idx in range(1, 4):
                    url = f"https://picsum.photos/seed/{seed}-gallery-{idx}/1400/900"
                    img, _ = sideImagesURLs.objects.get_or_create(urlField=url)
                    gallery_imgs.append(img)

                if dry_run:
                    self.stdout.write(f"[DRY RUN] Would set resortGallery to 3 images for resort {resort.id} ({resort.RealName or resort.name}).")
                else:
                    resort.resortGallery.set(gallery_imgs)
                gallery_sets += 1

                # 2) Replace images for food list items
                food_packages = resort.resortFood.all()
                if not food_packages.exists():
                    continue

                menu_items = Packages.objects.filter(packageName__in=food_packages).distinct()
                for item in menu_items:
                    food_items_seen += 1
                    item_seed = slugify(item.title) or f"food-{item.id}"

                    new_imgs = []
                    for idx in range(1, 3):
                        url = f"https://picsum.photos/seed/{seed}-{item_seed}-{idx}/1200/800"
                        img, _ = sideImagesURLs.objects.get_or_create(urlField=url)
                        new_imgs.append(img)

                    if dry_run:
                        self.stdout.write(f"[DRY RUN] Would set {len(new_imgs)} images for food item {item.id} ({item.title}).")
                    else:
                        item.ImageURL.set(new_imgs)
                    food_images_sets += 1

            if dry_run:
                # Ensure no writes in dry-run mode
                transaction.set_rollback(True)

        scope = f"place={place}" if place else "all places"
        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: updated galleries for {gallery_sets} resorts ({scope}); updated food images for {food_images_sets} food items (seen={food_items_seen})."
            )
        )

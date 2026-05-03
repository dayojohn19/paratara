from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


class Command(BaseCommand):
    help = (
        "Ensure each resort has activity resortPackages and each activity resortPackage has at least N Packages items. "
        "Optionally adds a minimum number of images per item."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default="Siargao",
            help='Only update resorts in a specific place (default: "Siargao")',
        )
        parser.add_argument(
            "--min-activity-packages",
            type=int,
            default=3,
            help="Minimum resortPackages attached to resortActivities per resort (default: 3)",
        )
        parser.add_argument(
            "--min-items",
            type=int,
            default=3,
            help="Minimum Packages items per activity resortPackage (default: 3)",
        )
        parser.add_argument(
            "--min-images",
            type=int,
            default=1,
            help="Minimum images per Packages item (default: 1)",
        )

    def handle(self, *args, **kwargs):
        place: str = kwargs["place"]
        min_activity_packages: int = kwargs["min_activity_packages"]
        min_items: int = kwargs["min_items"]
        min_images: int = kwargs["min_images"]

        resorts = resortItem.objects.filter(place__placename__iexact=place)
        if not resorts.exists():
            self.stdout.write(self.style.WARNING(f"No resorts found for place '{place}'."))
            return

        created_packages = 0
        created_items = 0
        created_images = 0

        seed_titles = [
            "Island Hopping",
            "Surf Lessons",
            "Snorkeling",
            "Kayak Rental",
            "Motorbike Rental",
            "Yoga Session",
            "Board Games",
        ]

        with transaction.atomic():
            for resort in resorts:
                resort_label = resort.RealName or resort.name or f"Resort {resort.id}"
                resort_slug = resort.slug or slugify(resort_label)

                existing_activity_packages = list(resort.resortActivities.all().order_by("id"))
                needed = max(0, min_activity_packages - len(existing_activity_packages))

                # Create missing top-level activity packages if needed
                for idx in range(len(existing_activity_packages) + 1, len(existing_activity_packages) + needed + 1):
                    base_title = seed_titles[(idx - 1) % len(seed_titles)]
                    title = f"{base_title}"

                    # Avoid per-resort duplicates by title
                    existing = resort.resortActivities.filter(PackageTitle__iexact=title).first()
                    pkg = existing or resortPackages.objects.create(
                        PackageTitle=title,
                        ItemOfResort=resort,
                    )
                    resort.resortActivities.add(pkg)
                    existing_activity_packages.append(pkg)
                    if existing is None:
                        created_packages += 1

                # Ensure each activity package has minimum items + images
                for pkg_index, pkg in enumerate(existing_activity_packages[:min_activity_packages], start=1):
                    items_qs = Packages.objects.filter(packageName=pkg).order_by("id")
                    existing_items = list(items_qs)
                    needed_items = max(0, min_items - len(existing_items))

                    for item_index in range(len(existing_items) + 1, len(existing_items) + needed_items + 1):
                        item_title = f"{pkg.PackageTitle} Option {item_index}"
                        item = Packages.objects.create(
                            packageName=pkg,
                            title=item_title,
                            description=f"{pkg.PackageTitle} experience at {resort_label}.",
                            information="Includes basic inclusions and local guidance.",
                            price=500 + (pkg_index * 200) + (item_index * 150),
                            website=f"https://paratara.com/{resort_slug}/activity/{pkg_index}/{item_index}",
                        )
                        pkg.subPackages.add(item)
                        existing_items.append(item)
                        created_items += 1

                    for item in existing_items[:min_items]:
                        current_count = item.ImageURL.count()
                        if current_count < min_images:
                            for img_index in range(current_count + 1, min_images + 1):
                                seed = f"{resort_slug}-act-{pkg.id}-item-{item.id}-img-{img_index}"
                                url = f"https://picsum.photos/seed/{seed}/900/600"
                                img, _ = sideImagesURLs.objects.get_or_create(urlField=url)
                                item.ImageURL.add(img)
                                created_images += 1

                        # Keep item linked via M2M too (template uses subPackagesList)
                        pkg.subPackages.add(item)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated activities for {resort_label}: activity_packages={resort.resortActivities.count()}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Created activity_packages={created_packages}, items={created_items}, images={created_images}."
            )
        )

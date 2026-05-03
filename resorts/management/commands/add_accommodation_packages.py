from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


class Command(BaseCommand):
    help = (
        "Ensure each resort has at least 3 accommodation resortPackages; "
        "each accommodation has at least 2 Packages; each Package has at least 2 images."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default="Siargao",
            help='Only update resorts in a specific place (default: "Siargao")',
        )
        parser.add_argument(
            "--min-accommodations",
            type=int,
            default=3,
            help="Minimum resortPackages to attach to resortAccomodations (default: 3)",
        )
        parser.add_argument(
            "--min-items",
            type=int,
            default=2,
            help="Minimum Packages items per resortPackage (default: 2)",
        )
        parser.add_argument(
            "--min-images",
            type=int,
            default=2,
            help="Minimum images per Packages item (default: 2)",
        )

    def handle(self, *args, **kwargs):
        place: str = kwargs["place"]
        min_accommodations: int = kwargs["min_accommodations"]
        min_items: int = kwargs["min_items"]
        min_images: int = kwargs["min_images"]

        resorts = resortItem.objects.filter(place__placename__iexact=place)
        if not resorts.exists():
            self.stdout.write(self.style.WARNING(f"No resorts found for place '{place}'."))
            return

        created_accommodations = 0
        created_items = 0
        created_images = 0

        with transaction.atomic():
            for resort in resorts:
                resort_label = resort.RealName or resort.name or f"Resort {resort.id}"
                resort_slug = resort.slug or slugify(resort_label)

                existing_acc = list(resort.resortAccomodations.all().order_by("id"))
                needed_acc = max(0, min_accommodations - len(existing_acc))

                # Create missing accommodation packages
                for acc_index in range(len(existing_acc) + 1, len(existing_acc) + needed_acc + 1):
                    acc_title = f"{resort_label} Accommodation {acc_index}"
                    acc = resortPackages.objects.create(
                        PackageTitle=acc_title,
                        ItemOfResort=resort,
                    )
                    resort.resortAccomodations.add(acc)
                    existing_acc.append(acc)
                    created_accommodations += 1

                # Ensure each accommodation has the minimum items + images
                for acc_index, acc in enumerate(existing_acc[:min_accommodations], start=1):
                    # Items can be discovered either via FK or via M2M; keep both in sync.
                    items_qs = Packages.objects.filter(packageName=acc).order_by("id")
                    existing_items = list(items_qs)
                    needed_items = max(0, min_items - len(existing_items))

                    for item_index in range(len(existing_items) + 1, len(existing_items) + needed_items + 1):
                        item_title = f"{acc.PackageTitle} Room Option {item_index}"
                        item = Packages.objects.create(
                            packageName=acc,
                            title=item_title,
                            description=f"Room option {item_index} for {resort_label}.",
                            information="Includes breakfast and Wi‑Fi.",
                            price=2500 + (acc_index * 400) + (item_index * 250),
                            website=f"https://paratara.com/{resort_slug}/stay/{acc_index}/{item_index}",
                        )
                        acc.subPackages.add(item)
                        existing_items.append(item)
                        created_items += 1

                    # Ensure images for each item
                    for item in existing_items[:min_items]:
                        current_count = item.ImageURL.count()
                        if current_count >= min_images:
                            # Still ensure it's linked via acc.subPackages
                            acc.subPackages.add(item)
                            continue

                        for img_index in range(current_count + 1, min_images + 1):
                            seed = f"{resort_slug}-acc-{acc_index}-item-{item.id}-img-{img_index}"
                            url = f"https://picsum.photos/seed/{seed}/900/600"
                            img, _ = sideImagesURLs.objects.get_or_create(urlField=url)
                            item.ImageURL.add(img)
                            created_images += 1

                        # Keep item linked to the parent package
                        acc.subPackages.add(item)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated accommodations for {resort_label}: "
                        f"now {resort.resortAccomodations.count()} accommodation packages."
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Created accommodations={created_accommodations}, items={created_items}, images={created_images}."
            )
        )

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


@dataclass(frozen=True)
class MenuSubItemSpec:
    title: str
    description: str
    information: str
    price: int
    # Used only for building the image URL query
    image_terms: tuple[str, ...]


@dataclass(frozen=True)
class MenuCategorySpec:
    package_title: str
    subitems: tuple[MenuSubItemSpec, ...]


def _unsplash_closeup_url(*terms: str, w: int = 1200, h: int = 800) -> str:
    # Unsplash “Source” endpoint returns a random image for the query.
    # Using closeup/macro terms biases toward close-up food shots.
    query = ",".join([t for t in terms if t])
    return f"https://source.unsplash.com/{w}x{h}/?{query}"


SEED_MENU: tuple[MenuCategorySpec, ...] = (
    MenuCategorySpec(
        package_title="Cake",
        subitems=(
            MenuSubItemSpec(
                title="Chocolate Lava Cake",
                description="Warm chocolate cake with a molten center.",
                information="Served fresh; best enjoyed warm.",
                price=250,
                image_terms=("cake", "chocolate", "dessert", "closeup"),
            ),
            MenuSubItemSpec(
                title="Classic Cheesecake Slice",
                description="Creamy cheesecake with a buttery crust.",
                information="Chilled slice; smooth and rich.",
                price=220,
                image_terms=("cheesecake", "dessert", "closeup"),
            ),
            MenuSubItemSpec(
                title="Red Velvet Cupcake",
                description="Soft red velvet cupcake with cream cheese frosting.",
                information="Single serving; light cocoa notes.",
                price=180,
                image_terms=("cupcake", "red%20velvet", "dessert", "closeup"),
            ),
        ),
    ),
    MenuCategorySpec(
        package_title="Seafood",
        subitems=(
            MenuSubItemSpec(
                title="Garlic Butter Prawns",
                description="Juicy prawns sautéed in garlic butter.",
                information="Great with rice; squeeze of calamansi recommended.",
                price=420,
                image_terms=("prawns", "seafood", "garlic", "closeup"),
            ),
            MenuSubItemSpec(
                title="Crispy Calamari",
                description="Crispy fried squid with dipping sauce.",
                information="Served hot and crunchy.",
                price=380,
                image_terms=("calamari", "seafood", "fried", "closeup"),
            ),
            MenuSubItemSpec(
                title="Grilled Fish Fillet",
                description="Grilled fish fillet with light seasoning.",
                information="Fresh catch style; simple and flavorful.",
                price=450,
                image_terms=("grilled%20fish", "seafood", "closeup"),
            ),
        ),
    ),
    MenuCategorySpec(
        package_title="Pasta",
        subitems=(
            MenuSubItemSpec(
                title="Creamy Carbonara",
                description="Creamy pasta with bacon and parmesan.",
                information="Rich sauce; served hot.",
                price=320,
                image_terms=("carbonara", "pasta", "closeup"),
            ),
            MenuSubItemSpec(
                title="Seafood Marinara",
                description="Tomato-based pasta with mixed seafood.",
                information="Tangy marinara with seafood topping.",
                price=380,
                image_terms=("seafood%20pasta", "marinara", "closeup"),
            ),
            MenuSubItemSpec(
                title="Pesto Penne",
                description="Basil pesto pasta with parmesan.",
                information="Herby, aromatic, and comforting.",
                price=300,
                image_terms=("pesto", "penne", "pasta", "closeup"),
            ),
        ),
    ),
)


class Command(BaseCommand):
    help = (
        "Seed each resortItem's resortFood with 3 resortPackages (Cake/Seafood/Pasta), "
        "each with 3 corresponding subPackages and close-up food images."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--place",
            type=str,
            default=None,
            help='Only seed resorts in a specific place (e.g. "Siargao").',
        )
        parser.add_argument(
            "--resort-id",
            type=int,
            default=None,
            help="Only seed a specific resortItem id.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit how many resorts are processed (useful for testing).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Clear the resort's existing resortFood links before seeding.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **kwargs):
        place = kwargs.get("place")
        resort_id = kwargs.get("resort_id")
        limit = kwargs.get("limit")
        replace = bool(kwargs.get("replace"))
        dry_run = bool(kwargs.get("dry_run"))

        resorts = resortItem.objects.all().order_by("id")
        if place:
            resorts = resorts.filter(place__placename__iexact=place)
        if resort_id:
            resorts = resorts.filter(id=resort_id)
        if limit:
            resorts = resorts[:limit]

        if not resorts.exists():
            self.stdout.write(self.style.WARNING("No resortItem records found for the given filter."))
            return

        created_categories = 0
        created_subitems = 0
        linked_categories = 0
        processed_resorts = 0

        with transaction.atomic():
            for resort in resorts:
                processed_resorts += 1

                if replace:
                    if dry_run:
                        self.stdout.write(
                            f"[DRY RUN] Would clear resortFood for resort {resort.id} ({resort.RealName or resort.name})."
                        )
                    else:
                        resort.resortFood.clear()

                for category in SEED_MENU:
                    rp, rp_created = resortPackages.objects.get_or_create(
                        ItemOfResort=resort,
                        PackageTitle=category.package_title,
                    )
                    if rp_created:
                        created_categories += 1

                    # Ensure the resort links this category under its Food list
                    if dry_run:
                        self.stdout.write(
                            f"[DRY RUN] Would link resort {resort.id} -> resortFood add category '{category.package_title}'."
                        )
                    else:
                        resort.resortFood.add(rp)
                    linked_categories += 1

                    # Seed 3 sub-items and ensure they are linked to rp.subPackages
                    for sub in category.subitems:
                        pkg, pkg_created = Packages.objects.get_or_create(
                            packageName=rp,
                            title=sub.title,
                            defaults={
                                "description": sub.description,
                                "information": sub.information,
                                "price": sub.price,
                                "website": resort.websiteURL,
                            },
                        )

                        if not pkg_created and not dry_run:
                            # Keep details fresh if records already exist
                            dirty = False
                            if pkg.description != sub.description:
                                pkg.description = sub.description
                                dirty = True
                            if pkg.information != sub.information:
                                pkg.information = sub.information
                                dirty = True
                            if pkg.price != sub.price:
                                pkg.price = sub.price
                                dirty = True
                            if resort.websiteURL and pkg.website != resort.websiteURL:
                                pkg.website = resort.websiteURL
                                dirty = True
                            if dirty:
                                pkg.save(update_fields=["description", "information", "price", "website"])

                        if pkg_created:
                            created_subitems += 1

                        # Attach at least 1 close-up image per sub-item
                        img_url = _unsplash_closeup_url(*sub.image_terms)
                        img_obj, _ = sideImagesURLs.objects.get_or_create(urlField=img_url)

                        if dry_run:
                            self.stdout.write(
                                f"[DRY RUN] Would set image for '{sub.title}' -> {img_url}"
                            )
                        else:
                            pkg.ImageURL.set([img_obj])

                        if dry_run:
                            self.stdout.write(
                                f"[DRY RUN] Would ensure '{sub.title}' is linked in '{category.package_title}' subPackages."
                            )
                        else:
                            rp.subPackages.add(pkg)

            if dry_run:
                transaction.set_rollback(True)

        scope_bits = []
        if place:
            scope_bits.append(f"place={place}")
        if resort_id:
            scope_bits.append(f"resort_id={resort_id}")
        if limit:
            scope_bits.append(f"limit={limit}")
        scope = ", ".join(scope_bits) if scope_bits else "all resorts"

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode}: processed={processed_resorts} ({scope}); "
                f"created_categories={created_categories}; created_subitems={created_subitems}; "
                f"linked_categories={linked_categories}."
            )
        )

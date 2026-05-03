from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from django.core.management.base import BaseCommand
from django.db import transaction

from resorts.models import Packages, resortItem, resortPackages, sideImagesURLs


@dataclass(frozen=True)
class ActivitySubItemSpec:
    title: str
    description: str
    information: str
    price: int
    image_terms: tuple[str, ...]


@dataclass(frozen=True)
class ActivityCategorySpec:
    package_title: str
    subitems: tuple[ActivitySubItemSpec, ...]


def _unsplash_activity_url(*terms: str, w: int = 1200, h: int = 800) -> str:
    # Unsplash “Source” endpoint returns a random image for the query.
    # Keep queries broad to avoid broken results; URL-encode safely.
    query = ",".join([t for t in terms if t]).strip()
    return f"https://source.unsplash.com/{w}x{h}/?{quote_plus(query)}"


SEED_ACTIVITIES: tuple[ActivityCategorySpec, ...] = (
    ActivityCategorySpec(
        package_title="Transportation",
        subitems=(
            ActivitySubItemSpec(
                title="Motorbike Rental",
                description="Daily motorbike rental for exploring nearby spots.",
                information="Valid driver’s license required. Fuel not included.",
                price=450,
                image_terms=("motorbike", "rental", "scooter", "travel"),
            ),
            ActivitySubItemSpec(
                title="Car Rental",
                description="Comfortable car rental for group travel.",
                information="Driver option available upon request.",
                price=1800,
                image_terms=("car", "rental", "road", "travel"),
            ),
            ActivitySubItemSpec(
                title="Bicycle Rental",
                description="Bike rental for relaxed rides and short trips.",
                information="Includes basic lock; helmet subject to availability.",
                price=200,
                image_terms=("bicycle", "rental", "outdoors"),
            ),
        ),
    ),
    ActivityCategorySpec(
        package_title="Board Games",
        subitems=(
            ActivitySubItemSpec(
                title="Chess",
                description="Classic chess set for casual or competitive play.",
                information="Borrow from the front desk; return before closing.",
                price=0,
                image_terms=("chess", "board%20game", "tabletop"),
            ),
            ActivitySubItemSpec(
                title="Scrabble",
                description="Word game perfect for family or friends.",
                information="Complete tile set; English letters.",
                price=0,
                image_terms=("scrabble", "board%20game", "letters"),
            ),
            ActivitySubItemSpec(
                title="Uno",
                description="Fast-paced card game for everyone.",
                information="Standard deck; best for 2–8 players.",
                price=0,
                image_terms=("uno", "card%20game", "table"),
            ),
        ),
    ),
    ActivityCategorySpec(
        package_title="Tours",
        subitems=(
            ActivitySubItemSpec(
                title="Land Tour",
                description="Guided land tour to top attractions and viewpoints.",
                information="Pickup time varies by route; ask for the itinerary.",
                price=1200,
                image_terms=("tour", "van", "scenic", "travel"),
            ),
            ActivitySubItemSpec(
                title="Island Hopping",
                description="Boat tour to nearby islands with swim stops.",
                information="Weather dependent; bring sun protection.",
                price=1500,
                image_terms=("island", "hopping", "boat", "ocean"),
            ),
            ActivitySubItemSpec(
                title="Sunset Tour",
                description="Golden-hour tour for photos and relaxing views.",
                information="Best on clear days; light snacks optional.",
                price=900,
                image_terms=("sunset", "tour", "beach", "travel"),
            ),
        ),
    ),
)


class Command(BaseCommand):
    help = (
        "Seed each resortItem's resortActivities with 3 categories (Transportation/Board Games/Tours), "
        "each with 3 corresponding subPackages and images."
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
            help="Clear the resort's existing resortActivities links before seeding.",
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
                            f"[DRY RUN] Would clear resortActivities for resort {resort.id} ({resort.RealName or resort.name})."
                        )
                    else:
                        resort.resortActivities.clear()

                for category in SEED_ACTIVITIES:
                    rp, rp_created = resortPackages.objects.get_or_create(
                        ItemOfResort=resort,
                        PackageTitle=category.package_title,
                    )
                    if rp_created:
                        created_categories += 1

                    if dry_run:
                        self.stdout.write(
                            f"[DRY RUN] Would link resort {resort.id} -> resortActivities add category '{category.package_title}'."
                        )
                    else:
                        resort.resortActivities.add(rp)
                    linked_categories += 1

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

                        img_url = _unsplash_activity_url(*sub.image_terms)
                        img_obj, _ = sideImagesURLs.objects.get_or_create(urlField=img_url)

                        if dry_run:
                            self.stdout.write(f"[DRY RUN] Would set image for '{sub.title}' -> {img_url}")
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

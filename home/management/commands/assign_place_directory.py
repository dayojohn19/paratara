import csv

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from home.models import Continent, Country, Places_v2, Region, normalize_place_type
from home.place_directory import sync_place_directory


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


class Command(BaseCommand):
    help = "Assign geography and type to existing Places_v2 directory rows."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--place-id", type=int, help="Places_v2 id to update.")
        target.add_argument("--slug", help="Places_v2 slug to update.")
        target.add_argument("--name", help="Places_v2 placename to update, case-insensitive.")
        target.add_argument(
            "--csv",
            dest="csv_path",
            help=(
                "CSV with place_id/id, slug, or placename/name plus optional "
                "continent, continent_name, region, region_name, country, "
                "country_name, place_type, is_published, popularity_score."
            ),
        )

        parser.add_argument("--continent", help="Continent code, e.g. asia.")
        parser.add_argument("--continent-name", help="Continent display name.")
        parser.add_argument("--region", help="Region code, e.g. southeast-asia.")
        parser.add_argument("--region-name", help="Region display name.")
        parser.add_argument("--country", help="Country code, e.g. PH.")
        parser.add_argument("--country-name", help="Country display name.")
        parser.add_argument("--place-type", help="Place type, e.g. island, beach, city.")
        parser.add_argument("--is-published", help="true/false value for directory publication.")
        parser.add_argument("--popularity-score", type=int, help="Override popularity score.")
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving.")

    def handle(self, *args, **options):
        if options.get("csv_path"):
            totals = self._handle_csv(options)
        else:
            totals = self._assign_one(options)

        suffix = " (dry-run)" if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                "Assigned place directories%s. processed=%s updated=%s skipped=%s"
                % (suffix, totals["processed"], totals["updated"], totals["skipped"])
            )
        )

    def _handle_csv(self, options):
        totals = {"processed": 0, "updated": 0, "skipped": 0}
        with open(options["csv_path"], newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise CommandError("CSV file has no header row.")

            for line_number, row in enumerate(reader, start=2):
                if not any(str(value or "").strip() for value in row.values()):
                    totals["skipped"] += 1
                    continue

                row_options = self._options_from_row(row, options)
                try:
                    row_totals = self._assign_one(row_options, label=f"line {line_number}")
                except CommandError as exc:
                    raise CommandError(f"CSV line {line_number}: {exc}") from exc

                for key in totals:
                    totals[key] += row_totals[key]

        return totals

    def _assign_one(self, options, label=None):
        place = self._get_place(options)
        sync_kwargs = self._sync_kwargs(options)

        if options["dry_run"]:
            directory = self._existing_directory(place)
        else:
            directory = sync_place_directory(place, **sync_kwargs)

        self.stdout.write(
            "%splace_id=%s placename=%r country=%s region=%s continent=%s place_type=%s"
            % (
                f"{label}: " if label else "",
                place.id,
                place.placename,
                self._code(getattr(directory, "country", None)) or self._code(sync_kwargs.get("country")),
                self._code(getattr(directory, "region", None)) or self._code(sync_kwargs.get("region")),
                self._code(getattr(directory, "continent", None)) or self._code(sync_kwargs.get("continent")),
                sync_kwargs.get("place_type", getattr(directory, "place_type", "")),
            )
        )

        return {"processed": 1, "updated": 0 if options["dry_run"] else 1, "skipped": 0}

    def _options_from_row(self, row, base_options):
        options = {
            "place_id": self._row_value(row, "place_id", "id"),
            "slug": self._row_value(row, "slug"),
            "name": self._row_value(row, "placename", "name"),
            "continent": self._row_value(row, "continent", "continent_code"),
            "continent_name": self._row_value(row, "continent_name"),
            "region": self._row_value(row, "region", "region_code"),
            "region_name": self._row_value(row, "region_name"),
            "country": self._row_value(row, "country", "country_code"),
            "country_name": self._row_value(row, "country_name"),
            "place_type": self._row_value(row, "place_type", "type"),
            "is_published": self._row_value(row, "is_published", "published"),
            "popularity_score": self._row_value(row, "popularity_score", "score"),
            "dry_run": base_options["dry_run"],
        }

        if options["place_id"]:
            try:
                options["place_id"] = int(options["place_id"])
            except (TypeError, ValueError) as exc:
                raise CommandError(f"Invalid place_id {options['place_id']!r}.") from exc
        if options["popularity_score"]:
            try:
                options["popularity_score"] = int(options["popularity_score"])
            except (TypeError, ValueError) as exc:
                raise CommandError(f"Invalid popularity_score {options['popularity_score']!r}.") from exc

        return options

    def _sync_kwargs(self, options):
        sync_kwargs = {}

        continent = self._ensure_continent(options)
        region = self._ensure_region(options, continent)
        country = self._ensure_country(options, region)

        if continent is not None:
            sync_kwargs["continent"] = continent
        if region is not None:
            sync_kwargs["region"] = region
        if country is not None:
            sync_kwargs["country"] = country
        if options.get("place_type"):
            place_type = normalize_place_type(options["place_type"])
            if place_type is None:
                raise CommandError(f"Unknown place_type {options['place_type']!r}.")
            sync_kwargs["place_type"] = place_type
        if options.get("is_published") not in (None, ""):
            sync_kwargs["is_published"] = self._parse_bool(options["is_published"])
        if options.get("popularity_score") is not None:
            sync_kwargs["popularity_score"] = options["popularity_score"]

        return sync_kwargs

    def _ensure_continent(self, options):
        code = self._clean_code(options.get("continent"), lower=True)
        name = self._clean(options.get("continent_name")) or code
        if not code and not name:
            return None
        if not code:
            code = slugify(name)
        continent, _created = Continent.objects.get_or_create(
            code=code,
            defaults={"name": name},
        )
        if name and continent.name != name:
            continent.name = name
            continent.save(update_fields=["name"])
        return continent

    def _ensure_region(self, options, continent):
        code = self._clean_code(options.get("region"), lower=True)
        name = self._clean(options.get("region_name")) or code
        if not code and not name:
            return None
        if not code:
            code = slugify(name)
        region, _created = Region.objects.get_or_create(
            code=code,
            defaults={"name": name, "continent": continent},
        )
        update_fields = []
        if name and region.name != name:
            region.name = name
            update_fields.append("name")
        if continent is not None and region.continent_id != continent.id:
            region.continent = continent
            update_fields.append("continent")
        if update_fields:
            region.save(update_fields=update_fields)
        return region

    def _ensure_country(self, options, region):
        code = self._clean_code(options.get("country"), upper=True)
        name = self._clean(options.get("country_name")) or code
        if not code and not name:
            return None
        if not code:
            raise CommandError("Country code is required when creating a new country.")

        country, _created = Country.objects.get_or_create(
            code=code,
            defaults={"name": name, "region": region},
        )
        update_fields = []
        if name and country.name != name:
            country.name = name
            update_fields.append("name")
        if region is not None and country.region_id != region.id:
            country.region = region
            update_fields.append("region")
        if update_fields:
            country.save(update_fields=update_fields)
        return country

    def _get_place(self, options):
        if options.get("place_id"):
            place = Places_v2.objects.filter(pk=options["place_id"]).first()
            if not place:
                raise CommandError(f"Place id {options['place_id']} was not found.")
            return place

        if options.get("slug"):
            place = Places_v2.objects.filter(slug=options["slug"]).first()
            if not place:
                raise CommandError(f"Place slug {options['slug']!r} was not found.")
            return place

        if options.get("name"):
            queryset = Places_v2.objects.filter(placename__iexact=options["name"])
            count = queryset.count()
            if count == 0:
                raise CommandError(f"Place name {options['name']!r} was not found.")
            if count > 1:
                raise CommandError(f"Place name {options['name']!r} matched {count} places. Use --place-id.")
            return queryset.first()

        raise CommandError("A place id, slug, name, or CSV row identifier is required.")

    def _parse_bool(self, value):
        text = str(value).strip().lower()
        if text in TRUE_VALUES:
            return True
        if text in FALSE_VALUES:
            return False
        raise CommandError(f"Invalid boolean value {value!r}.")

    def _existing_directory(self, place):
        try:
            return place.directory
        except Exception:
            return None

    def _row_value(self, row, *keys):
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _clean(self, value):
        return str(value or "").strip()

    def _clean_code(self, value, *, lower=False, upper=False):
        cleaned = self._clean(value)
        if lower:
            return cleaned.lower()
        if upper:
            return cleaned.upper()
        return cleaned

    def _code(self, obj):
        return getattr(obj, "code", "") if obj else ""

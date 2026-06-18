from django.db import transaction

from .models import (
    Continent,
    Country,
    PLACE_TYPE_UNSPECIFIED,
    PlaceDirectory,
    Places_v2,
    Region,
    normalize_place_type,
)


_UNSET = object()


def _place_is_published(place):
    return bool(getattr(place, "is_published", True))


def _place_popularity_score(place):
    try:
        return max(0, int(getattr(place, "reviewCount", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _resolve_reference(model_class, value):
    if value is _UNSET:
        return _UNSET
    if value is None or value == "":
        return None
    if isinstance(value, model_class):
        return value
    text = str(value).strip()
    if text.isdigit():
        return model_class.objects.filter(pk=int(text)).first()
    return model_class.objects.filter(code__iexact=text).first() or model_class.objects.filter(
        name__iexact=text
    ).first()


def _existing_reference(existing, field_name):
    if existing is None:
        return None
    return getattr(existing, field_name, None)


def _directory_geo(existing, *, continent=_UNSET, region=_UNSET, country=_UNSET):
    country_obj = _existing_reference(existing, "country")
    region_obj = _existing_reference(existing, "region")
    continent_obj = _existing_reference(existing, "continent")

    country_value = _resolve_reference(Country, country)
    region_value = _resolve_reference(Region, region)
    continent_value = _resolve_reference(Continent, continent)

    if country_value is not _UNSET:
        country_obj = country_value
        if country_obj is not None:
            region_obj = country_obj.region
            continent_obj = region_obj.continent if region_obj and region_obj.continent_id else None

    if region_value is not _UNSET:
        region_obj = region_value
        if region_obj is None:
            country_obj = None
        else:
            continent_obj = region_obj.continent
            if country_obj is not None and country_obj.region_id != region_obj.id:
                country_obj = None

    if continent_value is not _UNSET:
        continent_obj = continent_value
        if continent_obj is None:
            region_obj = None
            country_obj = None
        elif region_obj is not None and region_obj.continent_id != continent_obj.id:
            region_obj = None
            country_obj = None

    return continent_obj, region_obj, country_obj


def sync_place_directory(
    place,
    *,
    continent=_UNSET,
    region=_UNSET,
    country=_UNSET,
    place_type=_UNSET,
    is_published=None,
    popularity_score=None,
):
    existing = PlaceDirectory.objects.filter(place=place).select_related(
        "continent",
        "region__continent",
        "country__region__continent",
    ).first()
    continent_obj, region_obj, country_obj = _directory_geo(
        existing,
        continent=continent,
        region=region,
        country=country,
    )

    if place_type is _UNSET:
        place_type_value = existing.place_type if existing else PLACE_TYPE_UNSPECIFIED
    else:
        place_type_value = normalize_place_type(place_type)
        if place_type_value is None:
            raise ValueError(f"Unknown place_type: {place_type!r}")

    defaults = {
        "continent": continent_obj,
        "region": region_obj,
        "country": country_obj,
        "place_type": place_type_value,
        "is_published": _place_is_published(place) if is_published is None else bool(is_published),
        "popularity_score": (
            _place_popularity_score(place)
            if popularity_score is None
            else max(0, int(popularity_score or 0))
        ),
    }

    directory, _created = PlaceDirectory.objects.update_or_create(
        place=place,
        defaults=defaults,
    )
    return directory


def build_place_directory_queryset(params):
    queryset = PlaceDirectory.objects.published()

    continent = params.get("continent")
    region = params.get("region")
    country = params.get("country")
    place_type = params.get("place_type") or params.get("type")
    query = (params.get("q") or "").strip()

    if continent:
        queryset = queryset.in_continent(continent)
    if region:
        queryset = queryset.in_region(region)
    if country:
        queryset = queryset.in_country(country)
    if place_type:
        queryset = queryset.of_type(place_type)
    if query:
        queryset = queryset.filter(place__placename__icontains=query)

    return queryset.popular_first()


def fetch_places_for_directory_rows(directory_rows, *, include_photo=True):
    place_ids = [row.place_id for row in directory_rows]
    if not place_ids:
        return []

    fields = ["id", "placeID", "placename", "reviewCount", "slug"]
    if include_photo:
        fields.append("placePhoto")

    places_by_id = {
        row["id"]: row
        for row in Places_v2.objects.filter(pk__in=place_ids).values(*fields)
    }
    return [places_by_id[place_id] for place_id in place_ids if place_id in places_by_id]


def bulk_sync_place_directory(
    places_queryset,
    *,
    batch_size=500,
    dry_run=False,
    missing_only=False,
    progress=None,
):
    totals = {
        "processed": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
    }
    batch = []

    def flush():
        if not batch:
            return
        stats = _bulk_sync_batch(batch, dry_run=dry_run, missing_only=missing_only)
        for key, value in stats.items():
            totals[key] += value
        if progress:
            progress(totals.copy())
        batch.clear()

    for place in places_queryset.iterator(chunk_size=batch_size):
        batch.append(place)
        if len(batch) >= batch_size:
            flush()
    flush()
    return totals


def _bulk_sync_batch(places, *, dry_run=False, missing_only=False):
    place_ids = [place.id for place in places]
    existing_by_place_id = {
        directory.place_id: directory
        for directory in PlaceDirectory.objects.filter(place_id__in=place_ids).only(
            "place_id",
            "is_published",
            "popularity_score",
        )
    }

    creates = []
    updates = []
    unchanged = 0

    for place in places:
        is_published = _place_is_published(place)
        popularity_score = _place_popularity_score(place)
        existing = existing_by_place_id.get(place.id)

        if existing is None:
            creates.append(
                PlaceDirectory(
                    place_id=place.id,
                    place_type=PLACE_TYPE_UNSPECIFIED,
                    is_published=is_published,
                    popularity_score=popularity_score,
                )
            )
            continue

        if missing_only:
            unchanged += 1
            continue

        if (
            existing.is_published == is_published
            and existing.popularity_score == popularity_score
        ):
            unchanged += 1
            continue

        existing.is_published = is_published
        existing.popularity_score = popularity_score
        updates.append(existing)

    if not dry_run:
        with transaction.atomic():
            if creates:
                PlaceDirectory.objects.bulk_create(
                    creates,
                    batch_size=len(creates),
                    ignore_conflicts=True,
                )
            if updates:
                PlaceDirectory.objects.bulk_update(
                    updates,
                    ["is_published", "popularity_score"],
                    batch_size=len(updates),
                )

    return {
        "processed": len(places),
        "created": len(creates),
        "updated": len(updates),
        "unchanged": unchanged,
    }

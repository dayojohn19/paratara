import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from home.models import (
    Continent,
    Country,
    PLACE_TYPE_BEACH,
    PLACE_TYPE_CITY,
    PLACE_TYPE_ISLAND,
    PlaceDirectory,
    Places_v2,
    Region,
)
from home.place_directory import (
    build_place_directory_queryset,
    fetch_places_for_directory_rows,
    sync_place_directory,
)
from home.views import carpoolJOSN


def response_json(response):
    return json.loads(response.content.decode("utf-8"))


class PlaceDirectoryTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.asia = Continent.objects.create(code="asia", name="Asia")
        self.europe = Continent.objects.create(code="europe", name="Europe")
        self.se_asia = Region.objects.create(
            code="southeast-asia",
            name="Southeast Asia",
            continent=self.asia,
        )
        self.western_europe = Region.objects.create(
            code="western-europe",
            name="Western Europe",
            continent=self.europe,
        )
        self.ph = Country.objects.create(code="PH", name="Philippines", region=self.se_asia)
        self.fr = Country.objects.create(code="FR", name="France", region=self.western_europe)

    def create_place(self, name, score=0, country=None, place_type="destination", is_published=True):
        place = Places_v2.objects.create(placename=name, reviewCount=score)
        sync_place_directory(
            place,
            country=country,
            place_type=place_type,
            is_published=is_published,
        )
        return place

    def test_sync_creates_directory_row_from_place(self):
        place = self.create_place("Boracay", score=42, country=self.ph, place_type="beach")

        directory = PlaceDirectory.objects.get(place=place)

        self.assertEqual(directory.pk, place.pk)
        self.assertEqual(directory.country, self.ph)
        self.assertEqual(directory.region, self.se_asia)
        self.assertEqual(directory.continent, self.asia)
        self.assertEqual(directory.place_type, PLACE_TYPE_BEACH)
        self.assertTrue(directory.is_published)
        self.assertEqual(directory.popularity_score, 42)

    def test_sync_updates_ranking_publication_type_and_geography(self):
        place = self.create_place("Paris", score=4, country=self.ph, place_type="island")

        place.reviewCount = 99
        place.save(update_fields=["reviewCount"])
        sync_place_directory(
            place,
            country=self.fr,
            place_type="city",
            is_published=False,
        )

        directory = PlaceDirectory.objects.get(place=place)
        self.assertEqual(directory.country, self.fr)
        self.assertEqual(directory.region, self.western_europe)
        self.assertEqual(directory.continent, self.europe)
        self.assertEqual(directory.place_type, PLACE_TYPE_CITY)
        self.assertFalse(directory.is_published)
        self.assertEqual(directory.popularity_score, 99)

    def test_filters_by_continent_region_country_and_place_type(self):
        boracay = self.create_place("Boracay", score=20, country=self.ph, place_type="beach")
        paris = self.create_place("Paris", score=30, country=self.fr, place_type="city")

        self.assertEqual(
            list(PlaceDirectory.objects.published().in_continent("asia")),
            [boracay.directory],
        )
        self.assertEqual(
            list(PlaceDirectory.objects.published().in_region("western-europe")),
            [paris.directory],
        )
        self.assertEqual(
            list(PlaceDirectory.objects.published().in_country("PH")),
            [boracay.directory],
        )
        self.assertEqual(
            list(PlaceDirectory.objects.published().of_type("city")),
            [paris.directory],
        )

    def test_combined_filters(self):
        boracay = self.create_place("Boracay", score=20, country=self.ph, place_type="beach")
        self.create_place("Cebu City", score=30, country=self.ph, place_type="city")
        self.create_place("Nice", score=10, country=self.fr, place_type="beach")

        queryset = build_place_directory_queryset({
            "continent": "asia",
            "country": "PH",
            "place_type": "beach",
        })

        self.assertEqual(list(queryset), [boracay.directory])

    def test_directory_ordering_and_pagination_are_deterministic(self):
        first = self.create_place("First", score=10, country=self.ph, place_type="island")
        second = self.create_place("Second", score=30, country=self.ph, place_type="island")
        third = self.create_place("Third", score=30, country=self.ph, place_type="island")

        request = self.factory.get("/home/getcarpooljson/", {"limit": 2})
        response = carpoolJOSN(request)
        data = response_json(response)

        self.assertEqual([place["id"] for place in data["PlacesList"]], [second.id, third.id])
        self.assertTrue(data["has_next"])
        self.assertEqual(data["next_offset"], 2)

        request = self.factory.get("/home/getcarpooljson/", {"limit": 2, "offset": 2})
        response = carpoolJOSN(request)
        data = response_json(response)

        self.assertEqual([place["id"] for place in data["PlacesList"]], [first.id])

    def test_fetch_places_preserves_directory_order(self):
        first = self.create_place("First", score=10, country=self.ph, place_type="island")
        second = self.create_place("Second", score=30, country=self.ph, place_type="island")
        third = self.create_place("Third", score=20, country=self.ph, place_type="island")

        directory_rows = [
            PlaceDirectory.objects.get(place=second),
            PlaceDirectory.objects.get(place=third),
            PlaceDirectory.objects.get(place=first),
        ]

        places = fetch_places_for_directory_rows(directory_rows)

        self.assertEqual([place["id"] for place in places], [second.id, third.id, first.id])

    def test_missing_geography_does_not_crash_or_match_geo_filter(self):
        place = Places_v2.objects.create(placename="Unknown Place", reviewCount=1)
        sync_place_directory(place)

        self.assertEqual(PlaceDirectory.objects.in_country("PH").count(), 0)

        request = self.factory.get("/home/getcarpooljson/", {"limit": 5})
        response = carpoolJOSN(request)
        data = response_json(response)

        self.assertEqual([row["id"] for row in data["PlacesList"]], [place.id])

    def test_deleting_place_removes_directory_row(self):
        place = self.create_place("Temporary", score=1, country=self.ph, place_type="island")
        place_id = place.id

        place.delete()

        self.assertFalse(PlaceDirectory.objects.filter(place_id=place_id).exists())

    def test_rebuild_command_is_idempotent(self):
        self.create_place("One", score=1, country=self.ph, place_type="island")
        self.create_place("Two", score=2, country=self.ph, place_type="island")
        PlaceDirectory.objects.all().delete()

        out = StringIO()
        call_command("rebuild_place_directory", batch_size=1, stdout=out)
        self.assertEqual(PlaceDirectory.objects.count(), 2)

        call_command("rebuild_place_directory", batch_size=1, stdout=out)
        self.assertEqual(PlaceDirectory.objects.count(), 2)

    def test_list_page_query_count_is_constant_for_page_size(self):
        for index in range(60):
            self.create_place(
                f"Place {index}",
                score=index,
                country=self.ph,
                place_type="island",
            )

        query_counts = []
        for limit in (5, 20, 50):
            request = self.factory.get("/home/getcarpooljson/", {"limit": limit})
            with CaptureQueriesContext(connection) as captured:
                response = carpoolJOSN(request)
                response_json(response)
            query_counts.append(len(captured))

        self.assertEqual(query_counts, [2, 2, 2])

    def test_assign_command_updates_existing_place_directory(self):
        place = Places_v2.objects.create(placename="Siargao Island", reviewCount=7)

        out = StringIO()
        call_command(
            "assign_place_directory",
            slug=place.slug,
            country="PH",
            country_name="Philippines",
            region="southeast-asia",
            region_name="Southeast Asia",
            continent="asia",
            continent_name="Asia",
            place_type="island",
            stdout=out,
        )

        directory = PlaceDirectory.objects.get(place=place)
        self.assertEqual(directory.country.code, "PH")
        self.assertEqual(directory.region.code, "southeast-asia")
        self.assertEqual(directory.continent.code, "asia")
        self.assertEqual(directory.place_type, PLACE_TYPE_ISLAND)

    def test_assign_command_updates_existing_places_from_csv(self):
        siargao = Places_v2.objects.create(placename="Siargao Island", reviewCount=7)
        boracay = Places_v2.objects.create(placename="Boracay", reviewCount=10)

        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "place_directory.csv"
            csv_path.write_text(
                "slug,country,country_name,region,region_name,continent,continent_name,place_type\n"
                f"{siargao.slug},PH,Philippines,southeast-asia,Southeast Asia,asia,Asia,island\n"
                f"{boracay.slug},PH,Philippines,southeast-asia,Southeast Asia,asia,Asia,beach\n",
                encoding="utf-8",
            )

            out = StringIO()
            call_command("assign_place_directory", csv_path=str(csv_path), stdout=out)

        siargao_directory = PlaceDirectory.objects.get(place=siargao)
        boracay_directory = PlaceDirectory.objects.get(place=boracay)

        self.assertEqual(siargao_directory.country.code, "PH")
        self.assertEqual(siargao_directory.place_type, PLACE_TYPE_ISLAND)
        self.assertEqual(boracay_directory.country.code, "PH")
        self.assertEqual(boracay_directory.place_type, PLACE_TYPE_BEACH)

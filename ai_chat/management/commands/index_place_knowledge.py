
from django.core.management.base import BaseCommand, CommandError

from ai_chat.services.discussion_retrieval_service import index_place_knowledge
from home.models import Places_v2




class Command(BaseCommand):
    help = "Build or refresh local embeddings for place discussion knowledge."

    def add_arguments(self, parser):
        parser.add_argument(
            "--placeID",
            type=int,
            help="Index one Places_v2.placeID. If omitted, all places are indexed.",
        )
        parser.add_argument(
            "--keep-stale",
            action="store_true",
            help="Do not delete old index rows whose source records no longer exist.",
        )

    def handle(self, *args, **options):
        place_id = options.get("placeID")
        delete_stale = not options.get("keep_stale")

        if place_id is not None:
            try:
                places = [Places_v2.objects.get(placeID=place_id)]
            except Places_v2.DoesNotExist as exc:
                raise CommandError(f"Place with placeID={place_id} was not found") from exc
        else:
            places = list(Places_v2.objects.all().order_by("id"))

        if not places:
            self.stdout.write(self.style.WARNING("No places found to index."))
            return

        totals = {"documents": 0, "created": 0, "updated": 0, "skipped": 0, "deleted": 0}
        for place in places:
            self.stdout.write(f"Indexing placeID={place.placeID} name={place.placename}")
            result = index_place_knowledge(place, delete_stale=delete_stale)
            for key in totals:
                totals[key] += result.get(key, 0)
            self.stdout.write(
                "  documents={documents} created={created} updated={updated} "
                "skipped={skipped} deleted={deleted}".format(**result)
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Done. documents={documents} created={created} updated={updated} "
                "skipped={skipped} deleted={deleted}".format(**totals)
            )
        )


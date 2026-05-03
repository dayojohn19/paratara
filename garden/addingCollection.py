from django.http import HttpResponse
from garden.models import Collection
from home.models import Places_v2
from django.db.models import Q


def update_all_collection_place_direct(request):
    collections = Collection.objects.all()

    updated_count = 0

    for collection in collections:
        if not collection.collectionPlace:
            continue

        place_source_name = collection.collectionPlace.placeName.strip()

        # Primary match
        match = Places_v2.objects.filter(
            placename__icontains=place_source_name
        ).first()

        # Fallback: first word
        if not match:
            first_word = place_source_name.split()[0]
            match = Places_v2.objects.filter(
                Q(placename__icontains=first_word)
            ).first()

        collection.collectionPlaceDirect = match
        collection.save()

        updated_count += 1

    return HttpResponse(f"Updated {updated_count} collections successfully!")

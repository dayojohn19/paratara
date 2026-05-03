from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from resorts.models import resortItem, sideImagesURLs


class Command(BaseCommand):
    help = "Ensure each Siargao resort has at least three gallery images"

    def handle(self, *args, **kwargs):
        siargao_resorts = resortItem.objects.filter(place__placename__iexact="Siargao")
        if not siargao_resorts:
            self.stdout.write(self.style.WARNING("No Siargao resorts to update."))
            return

        added = 0
        with transaction.atomic():
            for resort in siargao_resorts:
                base_slug = resort.slug or slugify(resort.RealName or resort.name or f"resort-{resort.id}")
                existing = resort.resortGallery.count()
                for idx in range(existing + 1, 4):
                    url = f"https://cdn.paratara.com/gallery/{base_slug}/photo-{idx}.jpg"
                    image, _ = sideImagesURLs.objects.get_or_create(urlField=url)
                    resort.resortGallery.add(image)
                    added += 1
                    self.stdout.write(self.style.SUCCESS(f"Added gallery image {url} to {resort.RealName or resort.name}."))

        self.stdout.write(self.style.SUCCESS(f"Added {added} gallery images across {siargao_resorts.count()} resorts."))

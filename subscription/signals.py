from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SubscriptionProduct


@receiver(post_save, sender="resorts.Packages")
def create_subscription_product_for_package(sender, instance, created, **kwargs):
    if not created:
        return

    SubscriptionProduct.objects.get_or_create(
        resort_package=instance,
        defaults={
            "name": instance.title,
            "description": instance.description or "",
            "product_type": "SERVICE",
            "category": "SOFTWARE",
        },
    )
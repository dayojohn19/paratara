# subscriptions/models.py
from django.db import models
from resorts.models import resortItem

class PayPalSubscription(models.Model):
    STATUS_CHOICES = [
        ("CREATED", "Created"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    resort = models.ForeignKey(
        resortItem,
        on_delete=models.CASCADE,
        related_name="paypal_subscriptions"
    )
    paypal_subscription_id = models.CharField(max_length=100, unique=True)
    plan_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(null=True, blank=True)
    next_billing_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resort.name} - {self.status}"

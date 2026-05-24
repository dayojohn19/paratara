# subscriptions/models.py
from django.db import models
from resorts.models import resortItem

class PayPalCustomerSubscription(models.Model):
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
        related_name="paypal_subscriptions",
        blank=True,
        null=True
    )
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    mobile_number = models.CharField(max_length=30, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=100, unique=True)
    paypal_payer_id = models.CharField(max_length=150, blank=True, null=True)
    subscription_status = models.CharField(max_length=50, default="ACTIVE")
    plan_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(null=True, blank=True)
    paypal_create_time = models.DateTimeField(null=True, blank=True)
    paypal_status_update_time = models.DateTimeField(null=True, blank=True)
    next_billing_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    quantity = models.CharField(max_length=30, blank=True, null=True)
    shipping_amount_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    shipping_amount_currency = models.CharField(max_length=10, blank=True, null=True)
    failed_payments_count = models.IntegerField(null=True, blank=True)
    cycle_executions = models.JSONField(default=list, blank=True)
    billing_info = models.JSONField(default=dict, blank=True)
    subscriber = models.JSONField(default=dict, blank=True)
    last_payment = models.JSONField(default=dict, blank=True)
    last_payment_amount_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_payment_amount_currency = models.CharField(max_length=10, blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.paypal_subscription_id} - {self.subscription_status}"


class SubscriptionPlan(models.Model):
    BILLING_INTERVAL_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    TYPE_CHOICES = [
        ("subscription", "Subscription"),
        ("one_time", "One Time"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    billingInterval = models.CharField(max_length=20, choices=BILLING_INTERVAL_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="subscription")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    features = models.JSONField(default=list, blank=True)
    imageUrl = models.URLField(blank=True, null=True)
    paypalProduct = models.ForeignKey(
        "PayPalProduct",
        on_delete=models.SET_NULL,
        related_name="plans_fk",
        blank=True,
        null=True,
    )
    paypalPlanId = models.CharField(max_length=100, blank=True, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PayPalProduct(models.Model):
    paypal_product_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=50, default="SERVICE")
    category = models.CharField(max_length=80, default="SOFTWARE")
    status = models.CharField(max_length=30, blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True)
    subscription_plans = models.ManyToManyField(
        "SubscriptionPlan",
        related_name="paypal_products",
        blank=True,
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.paypal_product_id})"

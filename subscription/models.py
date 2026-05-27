import uuid
from datetime import timedelta

# subscriptions/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from resorts.models import resortItem


def _public_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def source_website_public_id():
    return _public_id("src")


def payment_button_public_id():
    return _public_id("btn")


def transaction_reference_id():
    return _public_id("txn")

class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("CREATED", "Created"),
        ("ACTIVE", "Active"),
        ("PAST_DUE", "Past Due"),
        ("UNPAID", "Unpaid"),
        ("SUSPENDED", "Suspended"),
        ("FAILED", "Failed"),
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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="user_subscriptions",
        blank=True,
        null=True,
    )
    plan = models.ForeignKey(
        "SubscriptionPlan",
        on_delete=models.PROTECT,
        related_name="user_subscriptions",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    mobile_number = models.CharField(max_length=30, blank=True, null=True)
    paypal_subscription_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    paypal_payer_id = models.CharField(max_length=150, blank=True, null=True)
    paymongo_customer_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    paymongo_subscription_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    subscription_status = models.CharField(max_length=50, default="ACTIVE")
    paypal_plan_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
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
    receipt_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        status_label = self.get_status_display() if self.status else (self.subscription_status or "Unknown")
        last_payment = self.last_payment_date.strftime("%Y-%m-%d") if self.last_payment_date else "N/A"
        next_billing = self.next_billing_time.strftime("%Y-%m-%d") if self.next_billing_time else "N/A"
        return f"{status_label} | Last payment: {last_payment} | Next billing: {next_billing}"


class SubscriptionPlan(models.Model):
    BILLING_INTERVAL_CHOICES = [
        ("weekly", "Weekly"),
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
    subscriptionProduct = models.ForeignKey(
        "SubscriptionProduct",
        on_delete=models.SET_NULL,
        related_name="plans_fk",
        blank=True,
        null=True,
    )
    paypalPlanId = models.CharField(max_length=100, blank=True, null=True)
    paymongo_plan_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SubscriptionProduct(models.Model):
    paypal_product_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    paymongo_product_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=50, default="SERVICE")
    category = models.CharField(max_length=80, default="SOFTWARE")
    status = models.CharField(max_length=30, blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True)
    subscription_plans = models.ManyToManyField(
        "SubscriptionPlan",
        related_name="subscription_products",
        blank=True,
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        provider_id = self.paypal_product_id or self.paymongo_product_id or "local"
        return f"{self.name} ({provider_id})"


class SourceWebsite(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True)
    public_id = models.CharField(
        max_length=40,
        unique=True,
        default=source_website_public_id,
        editable=False,
    )
    active = models.BooleanField(default=True)
    allowed_origins = models.JSONField(default=list, blank=True)
    default_success_url = models.URLField(blank=True, null=True)
    default_cancel_url = models.URLField(blank=True, null=True)
    default_failed_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PaymentButton(models.Model):
    CHECKOUT_MODE_CHOICES = [
        ("hosted_checkout", "Hosted Checkout"),
        ("paymongo_recurring", "PayMongo Recurring"),
        ("paymongo_link", "PayMongo Payment Link"),
    ]

    public_id = models.CharField(
        max_length=40,
        unique=True,
        default=payment_button_public_id,
        editable=False,
    )
    source_website = models.ForeignKey(
        SourceWebsite,
        on_delete=models.PROTECT,
        related_name="payment_buttons",
    )
    product = models.ForeignKey(
        SubscriptionProduct,
        on_delete=models.PROTECT,
        related_name="payment_buttons",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payment_buttons",
    )
    label = models.CharField(max_length=120, default="Subscribe Now")
    description = models.TextField(blank=True, null=True)
    checkout_mode = models.CharField(
        max_length=30,
        choices=CHECKOUT_MODE_CHOICES,
        default="hosted_checkout",
    )
    active = models.BooleanField(default=True)
    success_url = models.URLField(blank=True, null=True)
    cancel_url = models.URLField(blank=True, null=True)
    failed_url = models.URLField(blank=True, null=True)
    payment_link_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Existing PayMongo payment link URL, for example https://pm.link/org-.../b5vnlvt.",
    )
    payment_link_reference = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
        help_text="PayMongo payment link reference number, for example b5vnlvt.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_website__name", "product__name", "plan__price"]

    def __str__(self):
        return f"{self.label} - {self.plan}"


class Customer(models.Model):
    source_website = models.ForeignKey(
        SourceWebsite,
        on_delete=models.SET_NULL,
        related_name="customers",
        blank=True,
        null=True,
    )
    email = models.EmailField(blank=True, null=True, db_index=True)
    name = models.CharField(max_length=180, blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    paymongo_customer_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["email", "name"]

    def __str__(self):
        return self.email or self.name or f"Customer {self.pk}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("checkout_created", "Checkout Created"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("refunded", "Refunded"),
        ("partially_refunded", "Partially Refunded"),
    ]

    internal_reference_id = models.CharField(
        max_length=40,
        unique=True,
        default=transaction_reference_id,
        editable=False,
        db_index=True,
    )
    source_website = models.ForeignKey(
        SourceWebsite,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    product = models.ForeignKey(
        SubscriptionProduct,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    payment_button = models.ForeignKey(
        PaymentButton,
        on_delete=models.SET_NULL,
        related_name="transactions",
        blank=True,
        null=True,
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        related_name="transactions",
        blank=True,
        null=True,
    )
    customer_email = models.EmailField(blank=True, null=True)
    customer_name = models.CharField(max_length=180, blank=True, null=True)
    customer_phone = models.CharField(max_length=40, blank=True, null=True)
    customer_billing_details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending", db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_centavos = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="PHP")
    paymongo_checkout_session_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    paymongo_link_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    paymongo_reference_number = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    paymongo_payment_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    paymongo_payment_intent_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    paymongo_subscription_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    checkout_url = models.URLField(max_length=1000, blank=True, null=True)
    paymongo_status = models.CharField(max_length=80, blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    raw_checkout_request = models.JSONField(default=dict, blank=True)
    raw_checkout_response = models.JSONField(default=dict, blank=True)
    raw_webhook_payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.internal_reference_id} - {self.status}"


class PayMongoWebhookEvent(models.Model):
    PROCESSING_STATUS_CHOICES = [
        ("received", "Received"),
        ("processed", "Processed"),
        ("duplicate", "Duplicate"),
        ("invalid", "Invalid"),
        ("failed", "Failed"),
    ]

    paymongo_event_id = models.CharField(max_length=120, unique=True, db_index=True)
    event_type = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        related_name="webhook_events",
        blank=True,
        null=True,
    )
    signature_header = models.TextField(blank=True, null=True)
    verified = models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=30,
        choices=PROCESSING_STATUS_CHOICES,
        default="received",
    )
    raw_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.paymongo_event_id} - {self.event_type or 'unknown'}"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("incomplete", "Incomplete"),
        ("incomplete_cancelled", "Incomplete Cancelled"),
        ("pending", "Pending"),
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("unpaid", "Unpaid"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("failed", "Failed"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        related_name="paymongo_subscriptions",
        blank=True,
        null=True,
    )
    source_website = models.ForeignKey(
        SourceWebsite,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="paymongo_subscriptions",
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        related_name="activated_subscriptions",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending", db_index=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    paymongo_subscription_id = models.CharField(max_length=120, blank=True, null=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-current_period_end", "-created_at"]

    @property
    def is_active(self):
        if self.status != "active":
            return False
        if not self.current_period_end:
            return True
        return self.current_period_end >= timezone.now()

    @staticmethod
    def period_end_for_plan(plan, start_at=None):
        start_at = start_at or timezone.now()
        if getattr(plan, "billingInterval", "") == "weekly":
            return start_at + timedelta(days=7)
        if getattr(plan, "billingInterval", "") == "yearly":
            return start_at + timedelta(days=365)
        if getattr(plan, "billingInterval", "") == "monthly":
            return start_at + timedelta(days=30)
        return None

    def __str__(self):
        return f"{self.plan} - {self.status}"

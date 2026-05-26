from django.contrib import admin

from .models import (
    Customer,
    PaymentButton,
    PayMongoWebhookEvent,
    SourceWebsite,
    Subscription,
    SubscriptionPlan,
    SubscriptionProduct,
    Transaction,
    UserSubscription,
)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
        "price",
        "currency",
        "billingInterval",
        "type",
        "status",
        "paypalPlanId",
        "paymongo_plan_id",
    )
 

@admin.register(SubscriptionProduct)
class SubscriptionProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "paypal_product_id",
        "paymongo_product_id",
        "status",
        "createdAt",
    )
    search_fields = ("name", "paypal_product_id", "paymongo_product_id")
    list_filter = ("status", "product_type", "category")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "status",
        "paypal_subscription_id",
        "paymongo_customer_id",
        "paymongo_subscription_id",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "paypal_subscription_id",
        "paymongo_customer_id",
        "paymongo_subscription_id",
    )


@admin.register(SourceWebsite)
class SourceWebsiteAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "public_id", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "slug", "public_id")


@admin.register(PaymentButton)
class PaymentButtonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "public_id",
        "label",
        "source_website",
        "product",
        "plan",
        "checkout_mode",
        "active",
    )
    list_filter = ("active", "checkout_mode", "source_website")
    search_fields = ("public_id", "label", "source_website__name", "product__name", "plan__name")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "source_website", "paymongo_customer_id", "created_at")
    list_filter = ("source_website",)
    search_fields = ("email", "name", "phone", "paymongo_customer_id")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "internal_reference_id",
        "status",
        "source_website",
        "plan",
        "amount",
        "currency",
        "customer_email",
        "paymongo_checkout_session_id",
        "paymongo_payment_id",
        "created_at",
    )
    list_filter = ("status", "source_website", "currency", "created_at")
    search_fields = (
        "internal_reference_id",
        "customer_email",
        "paymongo_checkout_session_id",
        "paymongo_payment_id",
        "paymongo_payment_intent_id",
    )
    readonly_fields = (
        "internal_reference_id",
        "raw_checkout_request",
        "raw_checkout_response",
        "raw_webhook_payload",
        "created_at",
        "updated_at",
    )


@admin.register(PayMongoWebhookEvent)
class PayMongoWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "paymongo_event_id",
        "event_type",
        "verified",
        "processing_status",
        "transaction",
        "created_at",
    )
    list_filter = ("verified", "processing_status", "event_type", "created_at")
    search_fields = ("paymongo_event_id", "event_type", "transaction__internal_reference_id")
    readonly_fields = ("raw_payload", "signature_header", "created_at", "updated_at", "processed_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "source_website",
        "plan",
        "status",
        "current_period_start",
        "current_period_end",
        "paymongo_subscription_id",
    )
    list_filter = ("status", "source_website", "plan")
    search_fields = ("customer__email", "customer__name", "paymongo_subscription_id")

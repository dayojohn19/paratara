from django.contrib import admin
from .models import SubscriptionPlan, SubscriptionProduct, UserSubscription


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
 

admin.site.register(SubscriptionProduct)


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

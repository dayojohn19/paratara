from django.contrib import admin
from .models import PayPalCustomerSubscription, SubscriptionPlan, PayPalProduct

admin.site.register(PayPalCustomerSubscription)


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
    )
 

admin.site.register(PayPalProduct)

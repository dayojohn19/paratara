# subscriptions/urls.py
from django.urls import path
from .views import (
    create_subscription,
    create_subscription_plan_view,
    get_access_token_view,
    create_paypal_product_view,
    paypal_client_config_view,
    setup_page,
    subscription_plans_list_page,
    subscription_page,
)
from .webhooks import paypal_webhook, paypal_onapprove_webhook

app_name = "subscription"

urlpatterns = [
    path("", subscription_page, name="subscription_page"),
    path("plans/", subscription_plans_list_page, name="plans_list"),
    path("setup/", setup_page, name="subscription_setup"),
    path("setup/access-token/", get_access_token_view, name="subscription_get_access_token"),
    path("paypal/client-config/", paypal_client_config_view, name="paypal_client_config"),
    path("setup/create-product/", create_paypal_product_view, name="subscription_create_product"),
    path("setup/create-plan/", create_subscription_plan_view, name="subscription_create_plan"),
    path("create/", create_subscription, name="create_subscription"),
    path("webhook/paypal/", paypal_webhook, name="paypal_webhook"),
    path("webhook/paypal/on-approve/", paypal_onapprove_webhook, name="paypal_onapprove_webhook"),
]

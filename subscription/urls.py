# subscriptions/urls.py
from django.urls import path
from .views import (
    create_subscription,
    create_subscription_plan_view,
    embed_button_js,
    failed_redirect,
    get_access_token_view,
    paymongo_webhook,
    paymongo_cancel,
    paymongo_failed,
    paymongo_setup_page,
    paymongo_success,
    create_paypal_product_view,
    paypal_client_config_view,
    setup_page,
    start_paymongo_checkout,
    success_redirect,
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
    path("paymongo/setup/", paymongo_setup_page, name="paymongo_setup"),
    path("embed/button.js", embed_button_js, name="paymongo_embed_button_js"),
    path("pay/<str:button_public_id>/", start_paymongo_checkout, name="paymongo_start_checkout"),
    path("create/", create_subscription, name="create_subscription"),
    path("webhook/paypal/", paypal_webhook, name="paypal_webhook"),
    path("webhook/paypal/on-approve/", paypal_onapprove_webhook, name="paypal_onapprove_webhook"),
    path("webhook/paymongo/", paymongo_webhook, name="paymongo_webhook_legacy"),
    path("paymongo/webhook/", paymongo_webhook, name="paymongo_webhook"),
    path("paymongo/success/<str:internal_reference_id>/", paymongo_success, name="paymongo_success"),
    path("paymongo/cancel/<str:internal_reference_id>/", paymongo_cancel, name="paymongo_cancel"),
    path("paymongo/failed/<str:internal_reference_id>/", paymongo_failed, name="paymongo_failed"),
    path("paymongo/success/", success_redirect, name="paymongo_success_redirect"),
    path("paymongo/failed/", failed_redirect, name="paymongo_failed_redirect"),
]

# subscriptions/urls.py
from django.urls import path
from .views import create_subscription
from .webhooks import paypal_webhook

urlpatterns = [
    path("create/", create_subscription),
    path("webhook/paypal/", paypal_webhook),
]

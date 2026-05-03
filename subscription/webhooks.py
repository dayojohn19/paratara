# subscriptions/webhooks.py
import json
import requests
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PayPalSubscription
from .paypal import get_paypal_access_token

@csrf_exempt
def paypal_webhook(request):
    body = request.body.decode("utf-8")
    headers = request.headers

    token = get_paypal_access_token()

    verify_response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/notifications/verify-webhook-signature",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
            "cert_url": headers.get("PAYPAL-CERT-URL"),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": json.loads(body),
        },
    )

    if verify_response.json()["verification_status"] != "SUCCESS":
        return HttpResponse(status=400)

    event = json.loads(body)
    event_type = event["event_type"]
    resource = event["resource"]
# subscriptions/webhooks.py
    from resorts.models import ResortItem

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        resort_id = resource["custom_id"]
        resort = ResortItem.objects.get(id=resort_id)

        PayPalSubscription.objects.update_or_create(
            paypal_subscription_id=resource["id"],
            defaults={
                "resort": resort,
                "plan_id": resource["plan_id"],
                "status": "ACTIVE",
                "started_at": resource.get("start_time"),
                "next_billing_time": resource["billing_info"]["next_billing_time"],
            }
        )

        # Enable resort
        resort.is_active = True
        resort.save()

    elif event_type in [
        "BILLING.SUBSCRIPTION.CANCELLED",
        "BILLING.SUBSCRIPTION.SUSPENDED",
        "BILLING.SUBSCRIPTION.EXPIRED",
    ]:
        sub = PayPalSubscription.objects.get(
            paypal_subscription_id=resource["id"]
        )

        sub.status = resource["status"]
        sub.save()

        # Disable resort
        sub.resort.is_active = False
        sub.resort.save()
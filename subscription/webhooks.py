# subscriptions/webhooks.py
import json
import time
from decimal import Decimal, InvalidOperation
import requests
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .models import PayPalCustomerSubscription
from .paypal import get_paypal_access_token


@csrf_exempt
def paypal_webhook(request):
    return JsonResponse({"ok": True, "message": "PayPal webhook endpoint is ready."})


@csrf_exempt
def paypal_onapprove_webhook(request):
    print("[subscription.webhooks] paypal_onapprove_webhook called", flush=True)
    time.sleep(1)
    if request.method != "POST":
        print("[subscription.webhooks] invalid method", flush=True)
        time.sleep(1)
        return JsonResponse({"ok": False, "error": "Method not allowed. Use POST."}, status=405)

    try:
        print("[subscription.webhooks] parsing request body", flush=True)
        time.sleep(1)
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        print("[subscription.webhooks] invalid JSON payload", flush=True)
        time.sleep(1)
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    subscription_id = (payload.get("subscription_id") or "").strip()
    print(f"[subscription.webhooks] subscription_id received: {subscription_id}", flush=True)
    time.sleep(1)
    if not subscription_id:
        print("[subscription.webhooks] missing subscription_id", flush=True)
        time.sleep(1)
        return JsonResponse({"ok": False, "error": "subscription_id is required."}, status=400)

    try:
        print("[subscription.webhooks] requesting PayPal access token", flush=True)
        time.sleep(1)
        access_token = get_paypal_access_token()
        print("[subscription.webhooks] access token retrieved", flush=True)
        time.sleep(1)
        from django.conf import settings
        paypal_api_base = getattr(settings, "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
        print(f"[subscription.webhooks] fetching PayPal subscription details: {subscription_id}", flush=True)
        time.sleep(1)
        details_response = requests.get(
            f"{paypal_api_base}/v1/billing/subscriptions/{subscription_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=20,
        )
        details_response.raise_for_status()
        details = details_response.json()
        print("[subscription.webhooks] PayPal subscription details retrieved", flush=True)
        time.sleep(1)
    except requests.RequestException as exc:
        print(f"[subscription.webhooks] failed to fetch PayPal details: {exc}", flush=True)
        time.sleep(1)
        return JsonResponse({"ok": False, "error": f"Failed to fetch PayPal subscription details: {exc}"}, status=400)

    subscriber = details.get("subscriber") or {}
    subscriber_name = subscriber.get("name") or {}
    payer_id = ((subscriber.get("payer_id") or "").strip() or None)
    email = ((subscriber.get("email_address") or "").strip() or None)
    full_name = " ".join(
        part for part in [
            subscriber_name.get("given_name"),
            subscriber_name.get("surname")
        ]
        if part
    ).strip() or None

    paypal_subscription_id = (details.get("id") or "").strip() or subscription_id
    plan_id = (details.get("plan_id") or "").strip() or ""
    status_value = (details.get("status") or "CREATED").strip().upper()
    if status_value not in {"CREATED", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED"}:
        status_value = "CREATED"

    billing_info = details.get("billing_info") or {}
    shipping_amount = details.get("shipping_amount") or {}
    last_payment = billing_info.get("last_payment") or {}
    last_payment_amount = last_payment.get("amount") or {}

    try:
        shipping_amount_value = Decimal(str(shipping_amount.get("value"))) if shipping_amount.get("value") is not None else None
    except (InvalidOperation, TypeError, ValueError):
        shipping_amount_value = None
    try:
        last_payment_amount_value = Decimal(str(last_payment_amount.get("value"))) if last_payment_amount.get("value") is not None else None
    except (InvalidOperation, TypeError, ValueError):
        last_payment_amount_value = None

    start_time = parse_datetime(details.get("start_time") or "")
    create_time = parse_datetime(details.get("create_time") or "")
    status_update_time = parse_datetime(details.get("status_update_time") or "")
    next_billing_time = parse_datetime(billing_info.get("next_billing_time") or "")
    last_payment_date = parse_datetime((last_payment.get("time") or ""))

    obj, _ = PayPalCustomerSubscription.objects.update_or_create(
        paypal_subscription_id=paypal_subscription_id,
        defaults={
            "name": full_name,
            "email": email,
            "paypal_payer_id": payer_id,
            "plan_id": plan_id,
            "subscription_status": status_value,
            "status": status_value,
            "started_at": start_time,
            "paypal_create_time": create_time,
            "paypal_status_update_time": status_update_time,
            "next_billing_time": next_billing_time,
            "last_payment_date": last_payment_date,
            "quantity": (details.get("quantity") or None),
            "shipping_amount_value": shipping_amount_value,
            "shipping_amount_currency": shipping_amount.get("currency_code"),
            "failed_payments_count": billing_info.get("failed_payments_count"),
            "cycle_executions": billing_info.get("cycle_executions") or [],
            "billing_info": billing_info,
            "subscriber": subscriber,
            "last_payment": last_payment,
            "last_payment_amount_value": last_payment_amount_value,
            "last_payment_amount_currency": last_payment_amount.get("currency_code"),
        },
    )
    print(f"[subscription.webhooks] subscription saved: {obj.paypal_subscription_id}", flush=True)
    time.sleep(1)

    return JsonResponse(
        {
            "ok": True,
            "message": "Subscription captured from PayPal details.",
            "subscription_id": obj.paypal_subscription_id,
            "status": obj.status,
        }
    )

# subscriptions/webhooks.py
import json
import time
from decimal import Decimal, InvalidOperation
import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt

from .models import PayPalCustomerSubscription
from .paypal import get_paypal_access_token
from userProfile.models import UserCredentialsBackUP
from userProfile.services import ensure_user_profile
from userProfile.views import send_password_reset_email


PAYPAL_DETAILS_MAX_ATTEMPTS = 4
PAYPAL_DETAILS_RETRY_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
PAYPAL_DETAILS_RETRY_DELAYS = (1, 2, 4)


def _is_retryable_paypal_error(exc):
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code in PAYPAL_DETAILS_RETRY_STATUS_CODES or response is None


def _fetch_paypal_subscription_details(subscription_id, access_token, paypal_api_base):
    last_error = None
    for attempt in range(1, PAYPAL_DETAILS_MAX_ATTEMPTS + 1):
        try:
            print(
                f"[subscription.webhooks] PayPal details attempt {attempt}/{PAYPAL_DETAILS_MAX_ATTEMPTS}: {subscription_id}",
                flush=True,
            )
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
            return details_response.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= PAYPAL_DETAILS_MAX_ATTEMPTS or not _is_retryable_paypal_error(exc):
                raise

            delay = PAYPAL_DETAILS_RETRY_DELAYS[min(attempt - 1, len(PAYPAL_DETAILS_RETRY_DELAYS) - 1)]
            print(
                f"[subscription.webhooks] PayPal details fetch failed, retrying in {delay}s: {exc}",
                flush=True,
            )
            time.sleep(delay)

    raise last_error


def _normalize_username(value):
    username = slugify(value or "").replace("-", "_").lower().strip("_")
    return username or "paypal_user"


def _unique_username(UserModel, base_username, *, normalize=True):
    username_field = UserModel.USERNAME_FIELD
    max_length = UserModel._meta.get_field(username_field).max_length or 150
    if normalize:
        base_username = _normalize_username(base_username)
    else:
        base_username = (base_username or "").strip()

    base_username = base_username[:max_length] or "paypal_user"
    candidate = base_username
    counter = 1

    while UserModel._default_manager.filter(**{username_field: candidate}).exists():
        suffix = f"_{counter}"
        candidate = f"{base_username[:max_length - len(suffix)]}{suffix}"
        counter += 1

    return candidate


def _paypal_backup_password(*, payer_id, subscription_id):
    backup_value = f"paypal:{payer_id or subscription_id or 'subscription'}"
    max_length = UserCredentialsBackUP._meta.get_field("userPassword").max_length
    return backup_value[:max_length]


def _ensure_paypal_user_backup(user, *, payer_id, subscription_id):
    if UserCredentialsBackUP.objects.filter(userID=user.pk).exists():
        return

    UserCredentialsBackUP.objects.create(
        userID=user.pk,
        userPassword=_paypal_backup_password(
            payer_id=payer_id,
            subscription_id=subscription_id,
        ),
    )


def _build_password_reset_link(user, *, request=None):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_path = reverse("userProfile:resetPassword", kwargs={"uidb64": uidb64, "token": token})

    if request is not None:
        return request.build_absolute_uri(reset_path)

    from django.conf import settings

    base_url = (getattr(settings, "PASSWORD_RESET_BASE_URL", "") or "").strip()
    if not base_url:
        domain = (getattr(settings, "PYTHONANYWHERE_DOMAIN", "") or "").strip()
        if domain:
            base_url = f"https://{domain}"

    if not base_url:
        allowed_hosts = [
            host.strip()
            for host in (getattr(settings, "ALLOWED_HOSTS", []) or [])
            if host and host.strip() and host.strip() not in {"localhost", "127.0.0.1", "[::1]"}
        ]
        if allowed_hosts:
            base_url = f"https://{allowed_hosts[0]}"

    if not base_url:
        return None

    return f"{base_url.rstrip('/')}{reset_path}"


def _send_paypal_password_reset_email(user, *, request=None):
    target_email = (getattr(user, "email", "") or "").strip()
    if "@" not in target_email:
        return False

    reset_link = _build_password_reset_link(user, request=request)
    if not reset_link:
        print(
            f"[subscription.webhooks] skip password reset email, no reset base URL for user={user.pk}",
            flush=True,
        )
        return False

    try:
        return send_password_reset_email(email=target_email, reset_link=reset_link)
    except Exception as exc:
        print(
            f"[subscription.webhooks] failed to send password reset email user={user.pk}: {exc}",
            flush=True,
        )
        return False


def _get_or_create_paypal_user(*, email, full_name, subscriber_name, payer_id, subscription_id, request=None):
    UserModel = get_user_model()
    given_name = (subscriber_name.get("given_name") or "").strip()
    surname = (subscriber_name.get("surname") or "").strip()

    if email:
        existing_user = UserModel._default_manager.filter(email__iexact=email).order_by("id").first()
        if existing_user is not None:
            changed_fields = []
            if given_name and not existing_user.first_name:
                existing_user.first_name = given_name
                changed_fields.append("first_name")
            if surname and not existing_user.last_name:
                existing_user.last_name = surname
                changed_fields.append("last_name")
            if changed_fields:
                existing_user.save(update_fields=changed_fields)
            ensure_user_profile(
                existing_user,
                name=full_name or existing_user.username,
                contact=email,
            )
            _ensure_paypal_user_backup(
                existing_user,
                payer_id=payer_id,
                subscription_id=subscription_id,
            )
            return existing_user

    if email:
        base_username = email.lower()
    elif payer_id:
        base_username = f"paypal_{payer_id}"
    else:
        base_username = f"paypal_{subscription_id}"

    username_field = UserModel.USERNAME_FIELD
    max_length = UserModel._meta.get_field(username_field).max_length or 150
    if not email:
        normalized_base_username = _normalize_username(base_username)[:max_length] or "paypal_user"
        existing_user = UserModel._default_manager.filter(
            **{username_field: normalized_base_username}
        ).order_by("id").first()
        if existing_user is not None:
            ensure_user_profile(
                existing_user,
                name=full_name or existing_user.username,
                contact=payer_id or subscription_id,
            )
            _ensure_paypal_user_backup(
                existing_user,
                payer_id=payer_id,
                subscription_id=subscription_id,
            )
            return existing_user

    user = UserModel._default_manager.create_user(
        username=_unique_username(UserModel, base_username, normalize=not email),
        email=email or "",
        password=None,
        first_name=given_name,
        last_name=surname,
    )
    ensure_user_profile(
        user,
        name=full_name or user.username,
        contact=email or payer_id or subscription_id,
    )
    _ensure_paypal_user_backup(
        user,
        payer_id=payer_id,
        subscription_id=subscription_id,
    )
    if email:
        _send_paypal_password_reset_email(user, request=request)
    return user


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
        details = _fetch_paypal_subscription_details(subscription_id, access_token, paypal_api_base)
        print("[subscription.webhooks] PayPal subscription details retrieved", flush=True)
        time.sleep(1)
    except requests.RequestException as exc:
        print(f"[subscription.webhooks] failed to fetch PayPal details: {exc}", flush=True)
        time.sleep(1)
        status_code = 503 if _is_retryable_paypal_error(exc) else 400
        return JsonResponse(
            {
                "ok": False,
                "error": f"Failed to fetch PayPal subscription details: {exc}",
                "retryable": status_code == 503,
            },
            status=status_code,
        )

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
    subscription_user = _get_or_create_paypal_user(
        email=email,
        full_name=full_name,
        subscriber_name=subscriber_name,
        payer_id=payer_id,
        subscription_id=subscription_id,
        request=request,
    )

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
            "user": subscription_user,
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
    profile = ensure_user_profile(
        subscription_user,
        name=full_name or getattr(subscription_user, "username", ""),
        contact=email or payer_id or paypal_subscription_id,
    )
    if profile.paypal_customer_subscription_id != obj.id:
        profile.paypal_customer_subscription = obj
        profile.save(update_fields=["paypal_customer_subscription"])

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

import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation


class PayMongoAPIError(Exception):
    pass


class PayMongoSignatureError(SuspiciousOperation):
    pass


def amount_to_centavos(amount):
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Amount must be a valid number.") from exc

    if decimal_amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    return int((decimal_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_payment_base_url(request=None):
    configured_base = (getattr(settings, "DJANGO_PAYMENT_BASE_URL", "") or "").strip()
    if configured_base:
        return configured_base.rstrip("/")
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return ""


def build_checkout_metadata(*, source_website, product, plan, customer_email, internal_reference_id):
    return {
        "source_website": source_website.slug,
        "source_website_id": source_website.public_id,
        "product_id": str(product.pk),
        "plan_id": str(plan.pk),
        "plan_slug": plan.slug,
        "customer_email": customer_email or "",
        "internal_reference_id": internal_reference_id,
    }


def make_embed_token(button):
    payload = {
        "button_public_id": button.public_id,
        "source_public_id": button.source_website.public_id,
    }
    return signing.dumps(payload, salt="subscription.paymongo.embed")


def verify_embed_token(token, button):
    max_age = getattr(settings, "PAYMONGO_EMBED_TOKEN_MAX_AGE", 60 * 60 * 24 * 365)
    try:
        payload = signing.loads(token or "", salt="subscription.paymongo.embed", max_age=max_age)
    except signing.SignatureExpired as exc:
        raise SuspiciousOperation("Expired payment button token.") from exc
    except signing.BadSignature as exc:
        raise SuspiciousOperation("Invalid payment button token.") from exc

    if payload.get("button_public_id") != button.public_id:
        raise SuspiciousOperation("Payment button token does not match button.")
    if payload.get("source_public_id") != button.source_website.public_id:
        raise SuspiciousOperation("Payment button token does not match source website.")
    return payload


def request_origin(request):
    origin = (request.META.get("HTTP_ORIGIN") or "").strip()
    if origin:
        return normalize_origin(origin)

    referer = (request.META.get("HTTP_REFERER") or "").strip()
    if referer:
        return normalize_origin(referer)
    return ""


def normalize_origin(value):
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def origin_is_allowed(source_website, origin):
    origin = normalize_origin(origin)
    allowed_origins = [
        normalize_origin(item)
        for item in (source_website.allowed_origins or [])
        if normalize_origin(item)
    ]

    if not allowed_origins:
        return bool(getattr(settings, "DEBUG", False))

    return origin in allowed_origins


def parse_paymongo_signature(signature_header):
    values = {}
    for item in (signature_header or "").split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _json_dumps(payload):
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


class PayMongoClient:
    def __init__(self, secret_key=None, public_key=None, webhook_secret=None, mode=None):
        self.secret_key = secret_key or getattr(settings, "PAYMONGO_SECRET_KEY", "")
        self.public_key = public_key or getattr(settings, "PAYMONGO_PUBLIC_KEY", "")
        self.webhook_secret = webhook_secret or getattr(settings, "PAYMONGO_WEBHOOK_SECRET", "")
        self.mode = (mode or getattr(settings, "PAYMONGO_MODE", "test") or "test").lower()
        self.timeout = getattr(settings, "PAYMONGO_TIMEOUT", 30)
        self.api_base = getattr(settings, "PAYMONGO_API_BASE", "https://api.paymongo.com").rstrip("/")
        self.checkout_api_version = getattr(settings, "PAYMONGO_CHECKOUT_API_VERSION", "v1")

    def _headers(self):
        if not self.secret_key:
            raise ImproperlyConfigured("PAYMONGO_SECRET_KEY is not configured.")

        encoded = base64.b64encode(f"{self.secret_key}:".encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, endpoint, api_version=None):
        version = api_version or "v1"
        endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{self.api_base}/{version}{endpoint}"

    def _request(self, method, endpoint, payload=None, api_version=None):
        try:
            response = requests.request(
                method,
                self._url(endpoint, api_version=api_version),
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PayMongoAPIError(str(exc)) from exc

        if not response.ok:
            try:
                details = response.json()
            except ValueError:
                details = response.text
            raise PayMongoAPIError(f"PayMongo API error {response.status_code}: {details}")

        try:
            return response.json()
        except ValueError as exc:
            raise PayMongoAPIError("PayMongo returned invalid JSON.") from exc

    def create_checkout_session(
        self,
        *,
        transaction,
        line_item_name,
        description,
        success_url,
        cancel_url,
        metadata,
        allowed_payment_methods=None,
    ):
        payment_methods = allowed_payment_methods or getattr(
            settings,
            "PAYMONGO_ALLOWED_PAYMENT_METHODS",
            ["card", "gcash", "paymaya", "grab_pay", "qrph"],
        )
        if isinstance(payment_methods, str):
            payment_methods = [item.strip() for item in payment_methods.split(",") if item.strip()]

        attributes = {
            "send_email_receipt": True,
            "show_description": True,
            "show_line_items": True,
            "description": description or line_item_name,
            "reference_number": transaction.internal_reference_id,
            "payment_method_types": payment_methods,
            "line_items": [
                {
                    "currency": transaction.currency,
                    "amount": transaction.amount_centavos,
                    "name": line_item_name,
                    "quantity": 1,
                }
            ],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
        }

        payload = {"data": {"attributes": attributes}}
        response = self._request(
            "POST",
            "/checkout_sessions",
            payload=payload,
            api_version=self.checkout_api_version,
        )
        return payload, response

    def retrieve_checkout_session(self, checkout_session_id):
        return self._request(
            "GET",
            f"/checkout_sessions/{checkout_session_id}",
            api_version=self.checkout_api_version,
        )

    def create_customer(self, *, email, name=None, phone=None, metadata=None):
        attributes = {
            "email": email,
            "name": name,
            "phone": phone,
            "metadata": metadata or {},
        }
        attributes = {key: value for key, value in attributes.items() if value}
        return self._request("POST", "/customers", payload={"data": {"attributes": attributes}})

    def create_subscription(self, **attributes):
        if not getattr(settings, "PAYMONGO_ENABLE_RECURRING", False):
            raise ImproperlyConfigured("PAYMONGO_ENABLE_RECURRING is disabled.")
        return self._request("POST", "/subscriptions", payload={"data": {"attributes": attributes}})

    def verify_webhook_signature(self, raw_body, signature_header):
        if not self.webhook_secret:
            raise ImproperlyConfigured("PAYMONGO_WEBHOOK_SECRET is not configured.")

        parsed = parse_paymongo_signature(signature_header)
        timestamp = parsed.get("t")
        signature_key = "li" if self.mode == "live" else "te"
        supplied_signature = parsed.get(signature_key)

        if not timestamp or not supplied_signature:
            raise PayMongoSignatureError("Missing PayMongo webhook timestamp or signature.")

        tolerance = getattr(settings, "PAYMONGO_WEBHOOK_TOLERANCE_SECONDS", 300)
        try:
            timestamp_int = int(timestamp)
        except (TypeError, ValueError) as exc:
            raise PayMongoSignatureError("Invalid PayMongo webhook timestamp.") from exc

        if abs(int(time.time()) - timestamp_int) > tolerance:
            raise PayMongoSignatureError("PayMongo webhook timestamp is outside tolerance.")

        signed_payload = timestamp.encode("utf-8") + b"." + raw_body
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, supplied_signature):
            raise PayMongoSignatureError("Invalid PayMongo webhook signature.")

        return True


def extract_event_id(payload):
    event_id = payload.get("data", {}).get("id") or payload.get("id")
    if event_id:
        return str(event_id)
    return "evt_missing_" + hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()[:32]


def extract_event_type(payload):
    return (
        payload.get("data", {}).get("attributes", {}).get("type")
        or payload.get("type")
        or ""
    )


def extract_event_object(payload):
    attributes = payload.get("data", {}).get("attributes", {})
    event_object = attributes.get("data")
    if isinstance(event_object, dict):
        return event_object
    return payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}


def extract_object_attributes(event_object):
    if not isinstance(event_object, dict):
        return {}
    return event_object.get("attributes") or {}


def _find_first_key(value, key):
    if isinstance(value, dict):
        if key in value and value.get(key):
            return value.get(key)
        for child in value.values():
            found = _find_first_key(child, key)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first_key(child, key)
            if found:
                return found
    return None


def extract_metadata(payload):
    event_object = extract_event_object(payload)
    attributes = extract_object_attributes(event_object)
    metadata = attributes.get("metadata") or _find_first_key(payload, "metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def extract_payment_identifiers(payload):
    event_object = extract_event_object(payload)
    attributes = extract_object_attributes(event_object)
    object_id = event_object.get("id")
    object_type = event_object.get("type", "")

    checkout_session_id = None
    payment_id = None
    payment_intent_id = None
    subscription_id = None

    if object_type == "checkout_session" or str(object_id or "").startswith("cs_"):
        checkout_session_id = object_id
    elif object_type == "payment" or str(object_id or "").startswith("pay_"):
        payment_id = object_id
    elif object_type == "payment_intent" or str(object_id or "").startswith("pi_"):
        payment_intent_id = object_id
    elif object_type == "subscription" or str(object_id or "").startswith("sub_"):
        subscription_id = object_id

    payment_id = payment_id or attributes.get("payment_id") or _find_first_key(payload, "payment_id")
    payment_intent_id = payment_intent_id or attributes.get("payment_intent_id") or _find_first_key(payload, "payment_intent_id")
    checkout_session_id = checkout_session_id or attributes.get("checkout_session_id") or _find_first_key(payload, "checkout_session_id")
    subscription_id = subscription_id or attributes.get("subscription_id") or _find_first_key(payload, "subscription_id")

    payments = attributes.get("payments")
    if isinstance(payments, list) and payments:
        first_payment = payments[0]
        if isinstance(first_payment, dict):
            payment_id = payment_id or first_payment.get("id")

    return {
        "checkout_session_id": checkout_session_id,
        "payment_id": payment_id,
        "payment_intent_id": payment_intent_id,
        "subscription_id": subscription_id,
        "paymongo_status": attributes.get("status") or _find_first_key(payload, "status"),
    }


def checkout_url_from_response(response):
    return response.get("data", {}).get("attributes", {}).get("checkout_url")


def checkout_session_id_from_response(response):
    return response.get("data", {}).get("id")

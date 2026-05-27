import base64
import hashlib
import hmac
import json
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode, urlparse

import requests
from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation


class PayMongoAPIError(Exception):
    pass


class PayMongoSignatureError(SuspiciousOperation):
    pass


def _service_flow_print(function_name, process_type, message=""):
    file_origin = "subscription/services/paymongo.py"
    suffix = f" {message}" if message else ""
    print(f"[{file_origin}] [{function_name}] [{process_type}]{suffix}", flush=True)
    delay = getattr(settings, "PAYMONGO_FLOW_PRINT_DELAY_SECONDS", 1.0)
    try:
        delay = float(delay)
    except (TypeError, ValueError):
        delay = 1.0
    if delay > 0:
        time.sleep(delay)


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
        self.customer_api_version = getattr(settings, "PAYMONGO_CUSTOMER_API_VERSION", "v2")

    def _headers(self):
        if not self.secret_key:
            raise ImproperlyConfigured("PAYMONGO_SECRET_KEY is not configured.")

        _service_flow_print("_headers", "auth_header_prepare", "building PayMongo Basic Auth header without exposing secret")
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
        url = self._url(endpoint, api_version=api_version)
        _service_flow_print(
            "_request",
            "api_request_start",
            f"method={method} url={url}",
        )
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            _service_flow_print("_request", "api_request_error", f"method={method} url={url} error={exc}")
            raise PayMongoAPIError(str(exc)) from exc

        _service_flow_print(
            "_request",
            "api_response_received",
            f"method={method} url={url} status_code={response.status_code}",
        )
        if not response.ok:
            try:
                details = response.json()
            except ValueError:
                details = response.text
            _service_flow_print("_request", "api_response_error", f"status_code={response.status_code}")
            raise PayMongoAPIError(f"PayMongo API error {response.status_code}: {details}")

        try:
            parsed_response = response.json()
        except ValueError as exc:
            _service_flow_print("_request", "api_response_invalid_json", f"method={method} url={url}")
            raise PayMongoAPIError("PayMongo returned invalid JSON.") from exc
        _service_flow_print("_request", "api_response_json_ok", f"method={method} url={url}")
        return parsed_response

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

        metadata = dict(metadata or {})
        paymongo_customer_id = None
        if getattr(settings, "PAYMONGO_ATTACH_CUSTOMER_TO_CHECKOUT", True):
            paymongo_customer_id = getattr(getattr(transaction, "customer", None), "paymongo_customer_id", None)
            if paymongo_customer_id:
                metadata["paymongo_customer_id"] = paymongo_customer_id

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
        if paymongo_customer_id:
            attributes["customer_id"] = paymongo_customer_id

        payload = {"data": {"attributes": attributes}}
        _service_flow_print(
            "create_checkout_session",
            "checkout_payload_ready",
            (
                f"reference={transaction.internal_reference_id} amount={transaction.amount_centavos} "
                f"currency={transaction.currency} payment_methods={','.join(payment_methods)} "
                f"customer_id={paymongo_customer_id or '-'}"
            ),
        )
        try:
            response = self._request(
                "POST",
                "/checkout_sessions",
                payload=payload,
                api_version=self.checkout_api_version,
            )
        except PayMongoAPIError as exc:
            if not paymongo_customer_id or not getattr(settings, "PAYMONGO_CHECKOUT_CUSTOMER_ID_FALLBACK", True):
                raise

            _service_flow_print(
                "create_checkout_session",
                "checkout_customer_id_retry_without_link",
                f"reference={transaction.internal_reference_id} customer_id={paymongo_customer_id} error={exc}",
            )
            fallback_attributes = dict(attributes)
            fallback_attributes.pop("customer_id", None)
            fallback_payload = {"data": {"attributes": fallback_attributes}}
            response = self._request(
                "POST",
                "/checkout_sessions",
                payload=fallback_payload,
                api_version=self.checkout_api_version,
            )
            payload = fallback_payload

        _service_flow_print(
            "create_checkout_session",
            "checkout_created",
            f"reference={transaction.internal_reference_id} checkout_session_id={response.get('data', {}).get('id') or '-'}",
        )
        return payload, response

    def retrieve_checkout_session(self, checkout_session_id):
        _service_flow_print("retrieve_checkout_session", "checkout_retrieve_start", f"checkout_session_id={checkout_session_id}")
        return self._request(
            "GET",
            f"/checkout_sessions/{checkout_session_id}",
            api_version=self.checkout_api_version,
        )

    def retrieve_customer(self, *, email=None, phone=None):
        if str(self.customer_api_version).lower() == "v2":
            raise PayMongoAPIError("PayMongo v2 Customers API does not document email/phone lookup.")

        query = {}
        if email:
            query["email"] = email
        if phone:
            query["phone_number"] = phone
        if not query:
            raise PayMongoAPIError("Email or phone is required to retrieve a PayMongo customer.")
        query_string = urlencode(query)
        _service_flow_print("retrieve_customer", "customer_lookup_start", f"query_keys={','.join(sorted(query.keys()))}")
        return self._request("GET", f"/customers?{query_string}")

    def retrieve_customer_by_id(self, customer_id):
        _service_flow_print("retrieve_customer_by_id", "customer_lookup_start", f"customer_id={customer_id}")
        return self._request(
            "GET",
            f"/customers/{customer_id}",
            api_version=self.customer_api_version,
        )

    def create_customer(self, *, email, name=None, phone=None, metadata=None):
        _service_flow_print("create_customer", "customer_payload_start", f"email={email or '-'}")
        first_name = None
        last_name = None
        name = (name or "").strip()
        if name:
            name_parts = name.split(None, 1)
            first_name = name_parts[0]
            if len(name_parts) > 1:
                last_name = name_parts[1]

        if str(self.customer_api_version).lower() == "v2":
            payload = {
                "name": name or email,
                "email": email,
                "mobile_phone": phone,
                "live_mode": self.mode == "live",
            }
            payload = {key: value for key, value in payload.items() if value not in (None, "")}
            _service_flow_print("create_customer", "customer_v2_payload_ready", f"fields={','.join(sorted(payload.keys()))}")
            return self._request("POST", "/customers", payload=payload, api_version="v2")

        attributes = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
        }
        attributes = {key: value for key, value in attributes.items() if value}
        _service_flow_print("create_customer", "customer_payload_ready", f"fields={','.join(sorted(attributes.keys()))}")
        return self._request("POST", "/customers", payload={"data": {"attributes": attributes}})

    def create_subscription(self, **attributes):
        _service_flow_print("create_subscription", "subscription_payload_start", f"fields={','.join(sorted(attributes.keys()))}")
        if not getattr(settings, "PAYMONGO_ENABLE_RECURRING", False):
            _service_flow_print("create_subscription", "subscription_disabled", "PAYMONGO_ENABLE_RECURRING is false")
            raise ImproperlyConfigured("PAYMONGO_ENABLE_RECURRING is disabled.")
        return self._request("POST", "/subscriptions", payload={"data": {"attributes": attributes}})

    def verify_webhook_signature(self, raw_body, signature_header):
        _service_flow_print(
            "verify_webhook_signature",
            "signature_input_received",
            f"bytes={len(raw_body or b'')} mode={self.mode}",
        )
        if not self.webhook_secret:
            raise ImproperlyConfigured("PAYMONGO_WEBHOOK_SECRET is not configured.")

        parsed = parse_paymongo_signature(signature_header)
        timestamp = parsed.get("t")
        signature_key = "li" if self.mode == "live" else "te"
        supplied_signature = parsed.get(signature_key)

        if not timestamp or not supplied_signature:
            _service_flow_print("verify_webhook_signature", "signature_missing", f"signature_key={signature_key}")
            raise PayMongoSignatureError("Missing PayMongo webhook timestamp or signature.")

        tolerance = getattr(settings, "PAYMONGO_WEBHOOK_TOLERANCE_SECONDS", 300)
        try:
            timestamp_int = int(timestamp)
        except (TypeError, ValueError) as exc:
            _service_flow_print("verify_webhook_signature", "signature_timestamp_invalid", f"timestamp={timestamp}")
            raise PayMongoSignatureError("Invalid PayMongo webhook timestamp.") from exc

        if abs(int(time.time()) - timestamp_int) > tolerance:
            _service_flow_print("verify_webhook_signature", "signature_timestamp_rejected", f"timestamp={timestamp}")
            raise PayMongoSignatureError("PayMongo webhook timestamp is outside tolerance.")

        signed_payload = timestamp.encode("utf-8") + b"." + raw_body
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, supplied_signature):
            _service_flow_print("verify_webhook_signature", "signature_digest_rejected", f"signature_key={signature_key}")
            raise PayMongoSignatureError("Invalid PayMongo webhook signature.")

        _service_flow_print("verify_webhook_signature", "signature_verified", f"signature_key={signature_key}")
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


def _nested_payment_object(value):
    if not isinstance(value, dict):
        return {}
    if value.get("type") == "payment" or str(value.get("id") or "").startswith("pay_"):
        return value
    data = value.get("data")
    if isinstance(data, dict) and (data.get("type") == "payment" or str(data.get("id") or "").startswith("pay_")):
        return data
    return {}


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
    payment_link_id = None
    external_reference_number = None
    payment_id = None
    payment_intent_id = None
    subscription_id = None

    if object_type == "checkout_session" or str(object_id or "").startswith("cs_"):
        checkout_session_id = object_id
    elif object_type == "link" or str(object_id or "").startswith("link_"):
        payment_link_id = object_id
    elif object_type == "payment" or str(object_id or "").startswith("pay_"):
        payment_id = object_id
    elif object_type == "payment_intent" or str(object_id or "").startswith("pi_"):
        payment_intent_id = object_id
    elif object_type == "subscription" or str(object_id or "").startswith(("sub_", "subs_")):
        subscription_id = object_id

    payment_id = payment_id or attributes.get("payment_id") or _find_first_key(payload, "payment_id")
    payment_intent_id = payment_intent_id or attributes.get("payment_intent_id") or _find_first_key(payload, "payment_intent_id")
    checkout_session_id = checkout_session_id or attributes.get("checkout_session_id") or _find_first_key(payload, "checkout_session_id")
    payment_link_id = payment_link_id or attributes.get("link_id") or _find_first_key(payload, "link_id")
    external_reference_number = (
        attributes.get("reference_number")
        or attributes.get("external_reference_number")
        or _find_first_key(payload, "external_reference_number")
        or _find_first_key(payload, "reference_number")
    )
    subscription_id = subscription_id or attributes.get("subscription_id") or _find_first_key(payload, "subscription_id")

    payments = attributes.get("payments")
    if isinstance(payments, list) and payments:
        first_payment = payments[0]
        payment_object = _nested_payment_object(first_payment)
        if payment_object:
            payment_attributes = payment_object.get("attributes") or {}
            payment_id = payment_id or payment_object.get("id")
            payment_intent_id = payment_intent_id or payment_attributes.get("payment_intent_id")
            external_reference_number = external_reference_number or payment_attributes.get("external_reference_number")

    payment_intent = attributes.get("payment_intent")
    if isinstance(payment_intent, dict):
        payment_intent_id = payment_intent_id or payment_intent.get("id")

    subscription = attributes.get("subscription")
    if isinstance(subscription, dict):
        subscription_id = subscription_id or subscription.get("id")

    return {
        "checkout_session_id": checkout_session_id,
        "payment_link_id": payment_link_id,
        "external_reference_number": external_reference_number,
        "payment_id": payment_id,
        "payment_intent_id": payment_intent_id,
        "subscription_id": subscription_id,
        "paymongo_status": attributes.get("status") or _find_first_key(payload, "status"),
    }


def checkout_url_from_response(response):
    return response.get("data", {}).get("attributes", {}).get("checkout_url")


def checkout_session_id_from_response(response):
    return response.get("data", {}).get("id")

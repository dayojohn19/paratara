import base64

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_paymongo_api_base():
    return getattr(settings, "PAYMONGO_API_BASE", "https://api.paymongo.com/v1")


def _get_paymongo_timeout():
    return getattr(settings, "PAYMONGO_TIMEOUT", 30)


def _get_paymongo_secret_key():
    secret_key = getattr(settings, "PAYMONGO_SECRET_KEY", "")
    if not secret_key:
        raise ImproperlyConfigured("PAYMONGO_SECRET_KEY is not configured.")
    return secret_key


def _get_paymongo_headers():
    secret_key = _get_paymongo_secret_key()
    encoded = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _paymongo_post(endpoint, attributes):
    response = requests.post(
        f"{_get_paymongo_api_base()}{endpoint}",
        json={"data": {"attributes": attributes}},
        headers=_get_paymongo_headers(),
        timeout=_get_paymongo_timeout(),
    )
    response.raise_for_status()
    return response.json()


def create_product(
    name,
    description=None,
    metadata=None,
    **extra_attributes,
):
    attributes = {
        "name": name,
        "description": description,
        "metadata": metadata or {},
    }
    attributes.update(extra_attributes)
    attributes = {key: value for key, value in attributes.items() if value is not None}
    return _paymongo_post("/products", attributes)


def create_customer(
    email,
    first_name=None,
    last_name=None,
    phone=None,
    metadata=None,
    **extra_attributes,
):
    attributes = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "metadata": metadata or {},
    }
    attributes.update(extra_attributes)
    attributes = {key: value for key, value in attributes.items() if value is not None}
    return _paymongo_post("/customers", attributes)


def create_plan(
    name,
    amount,
    interval,
    product_id=None,
    currency="PHP",
    description=None,
    metadata=None,
    **extra_attributes,
):
    attributes = {
        "product": product_id,
        "name": name,
        "amount": amount,
        "interval": interval,
        "currency": currency,
        "description": description,
        "metadata": metadata or {},
    }
    attributes.update(extra_attributes)
    attributes = {key: value for key, value in attributes.items() if value is not None}
    return _paymongo_post("/plans", attributes)


def create_subscription(customer_id, plan_id, **extra_attributes):
    attributes = {
        "customer": customer_id,
        "plan": plan_id,
    }
    attributes.update(extra_attributes)
    return _paymongo_post("/subscriptions", attributes)


def create_payment_intent(
    amount,
    currency="PHP",
    payment_method_allowed=None,
    capture_type="automatic",
    payment_method_options=None,
    metadata=None,
    **extra_attributes,
):
    attributes = {
        "amount": amount,
        "currency": currency,
        "capture_type": capture_type,
        "payment_method_allowed": payment_method_allowed or ["card"],
        "payment_method_options": payment_method_options or {"card": {"request_three_d_secure": "any"}},
        "metadata": metadata or {},
    }
    attributes.update(extra_attributes)
    return _paymongo_post("/payment_intents", attributes)


def create_payment_method(
    method_type,
    billing=None,
    details=None,
    metadata=None,
    **extra_attributes,
):
    attributes = {
        "type": method_type,
        "billing": billing or {},
        "details": details or {},
        "metadata": metadata or {},
    }
    attributes.update(extra_attributes)
    return _paymongo_post("/payment_methods", attributes)


def attach_payment_method(
    payment_intent_id,
    payment_method_id,
    client_key,
    return_url=None,
    **extra_attributes,
):
    attributes = {
        "payment_method": payment_method_id,
        "client_key": client_key,
        "return_url": return_url,
    }
    attributes.update(extra_attributes)
    attributes = {key: value for key, value in attributes.items() if value is not None}
    return _paymongo_post(f"/payment_intents/{payment_intent_id}/attach", attributes)

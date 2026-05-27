import requests
from django.conf import settings


def get_paypal_access_token():
    paypal_api_base = getattr(settings, "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
    response = requests.post(
        f"{paypal_api_base}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_paypal_product(access_token, name, description, product_type="SERVICE", category="SOFTWARE"):
    paypal_api_base = getattr(settings, "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
    url = f"{paypal_api_base}/v1/catalogs/products"

    payload = {
        "name": name,
        "description": description,
        "type": product_type,
        "category": category,
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()


def create_paypal_billing_plan(
    access_token,
    product_id,
    plan_name,
    plan_description,
    price,
    currency="USD",
    billing_interval="monthly",
):
    paypal_api_base = getattr(settings, "PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")
    url = f"{paypal_api_base}/v1/billing/plans"

    interval_unit_map = {
        "weekly": "WEEK",
        "monthly": "MONTH",
        "yearly": "YEAR",
    }
    interval_unit = interval_unit_map.get(billing_interval, "MONTH")
    payload = {
        "product_id": product_id,
        "name": plan_name,
        "description": plan_description or plan_name,
        "status": "ACTIVE",
        "billing_cycles": [
            {
                "frequency": {
                    "interval_unit": interval_unit,
                    "interval_count": 1,
                },
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {
                        "value": f"{price:.2f}",
                        "currency_code": currency,
                    }
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee": {
                "value": "0",
                "currency_code": currency,
            },
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    return response.json()

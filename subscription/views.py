from django.shortcuts import redirect, render
from django.db.models import Prefetch

# Create your views here.
# subscriptions/views.py
import json
import time
import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from resorts.models import resortItem
from .models import SubscriptionPlan, SubscriptionProduct
from .paypal import (
    get_paypal_access_token,
    create_paypal_product,
    create_paypal_billing_plan,
)


def _debug_step(message):
    print(f"[subscription.views] {message}", flush=True)
    time.sleep(0.5)


def subscription_page(request):
    return render(request, "subscription/subscription.html")


def subscription_plans_list_page(request):
    active_plans = SubscriptionPlan.objects.filter(status="active").order_by("price", "name")
    products = SubscriptionProduct.objects.order_by("name").prefetch_related(
        Prefetch("plans_fk", queryset=active_plans, to_attr="active_fk_plans"),
        Prefetch("subscription_plans", queryset=active_plans, to_attr="active_m2m_plans"),
    )

    product_rows = []
    for product in products:
        merged = {}
        for plan in getattr(product, "active_fk_plans", []):
            merged[plan.id] = plan
        for plan in getattr(product, "active_m2m_plans", []):
            merged[plan.id] = plan
        product_rows.append(
            {
                "product": product,
                "plans": sorted(merged.values(), key=lambda p: (p.price, p.name)),
            }
        )

    return render(
        request,
        "subscription/plans_list.html",
        {"product_rows": product_rows},
    )


def setup_page(request):
    return render(request, "subscription/setup.html")


def paypal_client_config_view(request):
    client_id = getattr(settings, "PAYPAL_CLIENT_ID", "")
    if not client_id:
        return JsonResponse(
            {"ok": False, "error": "PayPal client ID is not configured."},
            status=500,
        )
    return JsonResponse({"ok": True, "client_id": client_id})


def get_access_token_view(request):
    _debug_step("get_access_token_view called")
    if request.method != "POST":
        _debug_step("invalid method for get_access_token_view")
        return JsonResponse(
            {"ok": False, "error": "Method not allowed. Use POST."},
            status=405,
        )

    try:
        _debug_step("requesting PayPal access token")
        token = get_paypal_access_token()
        _debug_step("PayPal access token retrieved successfully")
        return JsonResponse({"ok": True, "access_token": token})
    except requests.RequestException as exc:
        _debug_step(f"PayPal access token request failed: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


def create_paypal_product_view(request):
    _debug_step("create_paypal_product_view called")
    if request.method != "POST":
        _debug_step("invalid method for create_paypal_product_view")
        return JsonResponse(
            {"ok": False, "error": "Method not allowed. Use POST."},
            status=405,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        _debug_step("invalid JSON payload in create_paypal_product_view")
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    access_token = (payload.get("access_token") or "").strip()
    name = (payload.get("name") or "Premium Membership").strip() or "Premium Membership"
    description = (payload.get("description") or "Premium Subscription").strip() or "Premium Subscription"
    product_type = (payload.get("type") or "SERVICE").strip().upper()
    category = (payload.get("category") or "SOFTWARE").strip().upper()

    if not access_token:
        _debug_step("missing access_token in product payload")
        return JsonResponse({"ok": False, "error": "access_token is required."}, status=400)

    try:
        _debug_step("posting product to PayPal")
        paypal_response = create_paypal_product(
            access_token=access_token,
            name=name,
            description=description,
            product_type=product_type,
            category=category,
        )
        _debug_step("PayPal product created successfully")
    except requests.RequestException as exc:
        _debug_step(f"PayPal product creation failed: {exc}")
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    product_id = paypal_response.get("id")

    if product_id:
        _debug_step(f"saving PayPal product locally: {product_id}")
        SubscriptionProduct.objects.update_or_create(
            paypal_product_id=product_id,
            defaults={
                "name": name,
                "description": description,
                "product_type": product_type,
                "category": category,
                "status": paypal_response.get("status"),
                "raw_response": paypal_response,
            },
        )
        _debug_step("local SubscriptionProduct save complete")

    return JsonResponse(
        {
            "ok": True,
            "message": "PayPal product created.",
            "paypal": paypal_response,
            "product_id": product_id,
        }
    )


def create_subscription_plan_view(request):
    _debug_step("create_subscription_plan_view called")
    if request.method != "POST":
        _debug_step("invalid method for create_subscription_plan_view")
        return JsonResponse(
            {"ok": False, "error": "Method not allowed. Use POST."},
            status=405,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        _debug_step("invalid JSON payload in create_subscription_plan_view")
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    name = (payload.get("name") or "").strip()
    raw_slug = (payload.get("slug") or "").strip()
    description = (payload.get("description") or "").strip() or None
    raw_price = str(payload.get("price") or "").strip()
    currency = (payload.get("currency") or "USD").strip().upper()
    billing_interval = (payload.get("billingInterval") or "").strip().lower()
    plan_type = (payload.get("type") or "subscription").strip().lower()
    status_value = (payload.get("status") or "active").strip().lower()
    image_url = (payload.get("imageUrl") or "").strip() or None
    paypal_product_id = (payload.get("paypalProductId") or "").strip() or None
    paypal_plan_id = (payload.get("paypalPlanId") or "").strip() or None
    features = payload.get("features", [])

    if not name:
        _debug_step("validation failed: missing name")
        return JsonResponse({"ok": False, "error": "Name is required."}, status=400)
    if not raw_price:
        _debug_step("validation failed: missing price")
        return JsonResponse({"ok": False, "error": "Price is required."}, status=400)
    if billing_interval not in {"monthly", "yearly"}:
        _debug_step("validation failed: invalid billing interval")
        return JsonResponse(
            {"ok": False, "error": "Billing interval must be monthly or yearly."},
            status=400,
        )
    if plan_type not in {"subscription", "one_time"}:
        _debug_step("validation failed: invalid plan type")
        return JsonResponse(
            {"ok": False, "error": "Type must be subscription or one_time."},
            status=400,
        )
    if status_value not in {"active", "inactive"}:
        _debug_step("validation failed: invalid status")
        return JsonResponse(
            {"ok": False, "error": "Status must be active or inactive."},
            status=400,
        )

    try:
        price = Decimal(raw_price)
    except (InvalidOperation, ValueError):
        _debug_step("validation failed: invalid numeric price")
        return JsonResponse({"ok": False, "error": "Price must be a valid number."}, status=400)

    if isinstance(features, str):
        features = [item.strip() for item in features.split(",") if item.strip()]
    elif not isinstance(features, list):
        features = []

    base_slug = slugify(raw_slug or name)
    if not base_slug:
        _debug_step("validation failed: empty generated slug")
        return JsonResponse({"ok": False, "error": "Unable to generate a valid slug."}, status=400)

    unique_slug = base_slug
    suffix = 1
    while SubscriptionPlan.objects.filter(slug=unique_slug).exists():
        _debug_step(f"slug already exists, trying: {unique_slug}")
        unique_slug = f"{base_slug}-{suffix}"
        suffix += 1

    subscription_product_obj = None
    paypal_product_response = None
    if paypal_product_id:
        _debug_step(f"looking up SubscriptionProduct by PayPal product id: {paypal_product_id}")
        subscription_product_obj = SubscriptionProduct.objects.filter(
            paypal_product_id=paypal_product_id
        ).first()
        if not subscription_product_obj:
            _debug_step("validation failed: PayPal product not found")
            return JsonResponse(
                {
                    "ok": False,
                    "error": "PayPal product not found. Create product first.",
                },
                status=400,
            )

    paypal_plan_response = None
    if plan_type == "subscription":
        try:
            _debug_step("requesting access token for PayPal subscription plan flow")
            access_token = get_paypal_access_token()

            if not subscription_product_obj:
                _debug_step("creating PayPal product for subscription plan")
                paypal_product_response = create_paypal_product(
                    access_token=access_token,
                    name=name,
                    description=description or name,
                    product_type="SERVICE",
                    category="SOFTWARE",
                )
                paypal_product_id = paypal_product_response.get("id")
                if not paypal_product_id:
                    return JsonResponse(
                        {
                            "ok": False,
                            "error": "PayPal product creation succeeded but returned no product id.",
                        },
                        status=400,
                    )
                subscription_product_obj, _ = SubscriptionProduct.objects.update_or_create(
                    paypal_product_id=paypal_product_id,
                    defaults={
                        "name": name,
                        "description": description or name,
                        "product_type": "SERVICE",
                        "category": "SOFTWARE",
                        "status": paypal_product_response.get("status"),
                        "raw_response": paypal_product_response,
                    },
                )
                _debug_step(f"PayPal product created and saved: {paypal_product_id}")

            if not paypal_plan_id:
                _debug_step("creating billing plan in PayPal")
                paypal_plan_response = create_paypal_billing_plan(
                    access_token=access_token,
                    product_id=subscription_product_obj.paypal_product_id,
                    plan_name=name,
                    plan_description=description or name,
                    price=price,
                    currency=currency,
                    billing_interval=billing_interval,
                )
                paypal_plan_id = paypal_plan_response.get("id")
                _debug_step(f"PayPal billing plan created: {paypal_plan_id}")
        except requests.RequestException as exc:
            _debug_step(f"PayPal product/plan creation failed: {exc}")
            return JsonResponse(
                {
                    "ok": False,
                    "error": f"Failed to create PayPal product/plan: {exc}",
                },
                status=400,
            )

    _debug_step("creating local SubscriptionPlan record")
    plan = SubscriptionPlan.objects.create(
        name=name,
        slug=unique_slug,
        description=description,
        price=price,
        currency=currency,
        billingInterval=billing_interval,
        type=plan_type,
        status=status_value,
        features=features,
        imageUrl=image_url,
        subscriptionProduct=subscription_product_obj,
        paypalPlanId=paypal_plan_id,
    )
    _debug_step(f"local SubscriptionPlan created: {plan.id}")

    if subscription_product_obj:
        _debug_step("linking SubscriptionPlan to SubscriptionProduct via M2M")
        subscription_product_obj.subscription_plans.add(plan)
        _debug_step("M2M link complete")

    return JsonResponse(
        {
            "ok": True,
            "message": "Subscription plan created.",
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "slug": plan.slug,
                "paypalPlanId": plan.paypalPlanId,
                "paypalProductId": (
                    plan.subscriptionProduct.paypal_product_id if plan.subscriptionProduct else None
                ),
            },
            "paypal": {
                "product": paypal_product_response,
                "plan": paypal_plan_response,
            },
        }
    )

# subscriptions/views.py
@login_required
def create_subscription(request):
    data = json.loads(request.body)
    plan_id = data["plan_id"]
    resort_id = data["resort_id"]

    resort = resortItem.objects.get(
        id=resort_id,
    )

    token = get_paypal_access_token()

    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/billing/subscriptions",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "plan_id": plan_id,
            "custom_id": str(resort.id),  # 🔑 KEY
            "application_context": {
                "brand_name": "Paratara",
                "user_action": "SUBSCRIBE_NOW",
                "return_url": "https://yourdomain.com/paypal/success/",
                "cancel_url": "https://yourdomain.com/paypal/cancel/",
            },
        },
    )

    response.raise_for_status()
    return JsonResponse(response.json())


@csrf_exempt
def paymongo_webhook(request):
    if request.method != "POST":
        return JsonResponse(
            {"ok": False, "error": "Method not allowed. Use POST."},
            status=405,
        )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    event_type = (
        payload.get("data", {}).get("attributes", {}).get("type")
        or payload.get("type")
        or ""
    )

    _debug_step(f"paymongo_webhook received event: {event_type or 'unknown'}")
    return JsonResponse(
        {
            "ok": True,
            "message": "PayMongo webhook received.",
            "event_type": event_type,
        }
    )


def success_redirect(request):
    target_url = (
        getattr(settings, "PAYMONGO_SUCCESS_REDIRECT_URL", "").strip()
        or f"{reverse('subscription:plans_list')}?payment=success"
    )
    return redirect(target_url)


def failed_redirect(request):
    target_url = (
        getattr(settings, "PAYMONGO_FAILED_REDIRECT_URL", "").strip()
        or f"{reverse('subscription:plans_list')}?payment=failed"
    )
    return redirect(target_url)

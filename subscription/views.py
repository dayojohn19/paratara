from datetime import datetime, timedelta, timezone as dt_timezone

from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Prefetch

# Create your views here.
# subscriptions/views.py
import json
import time
import requests
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.db import IntegrityError, OperationalError, transaction as db_transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from resorts.models import resortItem
from userProfile.models import UserCredentialsBackUP
from userProfile.services import ensure_user_profile
from .forms import PaymentButtonForm, SourceWebsiteForm, SubscriptionPlanForm, SubscriptionProductForm
from .models import (
    Customer,
    PaymentButton,
    PayMongoWebhookEvent,
    SourceWebsite,
    Subscription,
    SubscriptionPlan,
    SubscriptionProduct,
    Transaction,
    UserSubscription,
)
from .paypal import (
    get_paypal_access_token,
    create_paypal_product,
    create_paypal_billing_plan,
)
from .services.paymongo import (
    PayMongoAPIError,
    PayMongoClient,
    PayMongoSignatureError,
    amount_to_centavos,
    build_checkout_metadata,
    checkout_session_id_from_response,
    checkout_url_from_response,
    extract_event_id,
    extract_event_type,
    extract_metadata,
    extract_payment_identifiers,
    get_payment_base_url,
    make_embed_token,
    origin_is_allowed,
    request_origin,
    verify_embed_token,
)


def _debug_step(message):
    print(f"[subscription.views] {message}", flush=True)
    time.sleep(0.5)


def _payment_flow_print(function_name, process_type, message=""):
    file_origin = "subscription/views.py"
    suffix = f" {message}" if message else ""
    print(f"[{file_origin}] [{function_name}] [{process_type}]{suffix}", flush=True)
    delay = getattr(settings, "PAYMONGO_FLOW_PRINT_DELAY_SECONDS", 1.0)
    try:
        delay = float(delay)
    except (TypeError, ValueError):
        delay = 1.0
    if delay > 0:
        time.sleep(delay)


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
    if billing_interval not in {"weekly", "monthly", "yearly"}:
        _debug_step("validation failed: invalid billing interval")
        return JsonResponse(
            {"ok": False, "error": "Billing interval must be weekly, monthly, or yearly."},
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


def _admin_change_url(model_name, obj):
    if not obj or not obj.pk:
        return ""
    return reverse(f"admin:subscription_{model_name}_change", args=[obj.pk])


def _return_url(request, transaction, outcome):
    base_url = get_payment_base_url(request)
    return f"{base_url}{reverse(f'subscription:paymongo_{outcome}', args=[transaction.internal_reference_id])}"


def _external_outcome_url(transaction, outcome):
    button = transaction.payment_button
    source = transaction.source_website
    button_url = getattr(button, f"{outcome}_url", "") if button else ""
    source_url = getattr(source, f"default_{outcome}_url", "") if source else ""
    return (button_url or source_url or "").strip()


def _button_embed_data(button, request=None):
    base_url = get_payment_base_url(request)
    token = make_embed_token(button)
    script = (
        f'<script src="{base_url}/subscription/embed/button.js" '
        f'data-button-id="{button.public_id}" '
        f'data-embed-token="{token}" '
        f'data-label="{button.label}"></script>'
    )
    form = (
        f'<form action="{base_url}/subscription/pay/{button.public_id}/" method="POST">\n'
        f'  <input type="hidden" name="embed_token" value="{token}">\n'
        f'  <button type="submit">{button.label}</button>\n'
        f'</form>'
    )
    return {"token": token, "script": script, "form": form}


@staff_member_required
def paymongo_setup_page(request):
    source_form = SourceWebsiteForm(prefix="source")
    product_form = SubscriptionProductForm(prefix="product")
    plan_form = SubscriptionPlanForm(prefix="plan")
    button_form = PaymentButtonForm(prefix="button")

    if request.method == "POST":
        action = request.POST.get("action")
        form_by_action = {
            "create_source": SourceWebsiteForm(request.POST, prefix="source"),
            "create_product": SubscriptionProductForm(request.POST, prefix="product"),
            "create_plan": SubscriptionPlanForm(request.POST, prefix="plan"),
            "create_button": PaymentButtonForm(request.POST, prefix="button"),
        }
        selected_form = form_by_action.get(action)

        if selected_form is None:
            messages.error(request, "Unknown setup action.")
        elif selected_form.is_valid():
            selected_form.save()
            messages.success(request, "PayMongo setup item saved.")
            return redirect("subscription:paymongo_setup")
        else:
            messages.error(request, "Please correct the highlighted fields.")
            if action == "create_source":
                source_form = selected_form
            elif action == "create_product":
                product_form = selected_form
            elif action == "create_plan":
                plan_form = selected_form
            elif action == "create_button":
                button_form = selected_form

    source_websites = SourceWebsite.objects.order_by("name")
    products = SubscriptionProduct.objects.order_by("name")
    plans = SubscriptionPlan.objects.select_related("subscriptionProduct").order_by("price", "name")
    buttons = PaymentButton.objects.select_related(
        "source_website",
        "product",
        "plan",
    ).order_by("-created_at")
    transactions = Transaction.objects.select_related(
        "source_website",
        "product",
        "plan",
        "customer",
        "payment_button",
    ).order_by("-created_at")[:25]
    webhook_events = PayMongoWebhookEvent.objects.select_related("transaction").order_by("-created_at")[:25]

    button_rows = []
    for button in buttons:
        embed_data = _button_embed_data(button, request=request)
        last_transaction = button.transactions.order_by("-created_at").first()
        button_rows.append(
            {
                "button": button,
                "embed_script": embed_data["script"],
                "fallback_form": embed_data["form"],
                "last_transaction": last_transaction,
                "admin_url": _admin_change_url("paymentbutton", button),
            }
        )

    return render(
        request,
        "subscription/paymongosetup.html",
        {
            "source_form": source_form,
            "product_form": product_form,
            "plan_form": plan_form,
            "button_form": button_form,
            "source_websites": source_websites,
            "products": products,
            "plans": plans,
            "button_rows": button_rows,
            "transactions": transactions,
            "webhook_events": webhook_events,
            "paymongo_mode": getattr(settings, "PAYMONGO_MODE", "test"),
            "payment_base_url": get_payment_base_url(request),
        },
    )


@require_GET
def embed_button_js(request):
    javascript = r"""
(function () {
  var script = document.currentScript;
  if (!script) return;

  var buttonId = script.getAttribute("data-button-id") || "";
  var embedToken = script.getAttribute("data-embed-token") || "";
  if (!buttonId || !embedToken) {
    console.error("PayMongo button embed is missing data-button-id or data-embed-token.");
    return;
  }

  var scriptUrl = new URL(script.src);
  var form = document.createElement("form");
  form.method = "POST";
  form.action = scriptUrl.origin + "/subscription/pay/" + encodeURIComponent(buttonId) + "/";
  form.target = "_top";
  form.style.display = "inline-block";
  form.style.margin = "0";

  function hidden(name, value) {
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value || "";
    form.appendChild(input);
  }

  hidden("embed_token", embedToken);
  hidden("customer_email", script.getAttribute("data-customer-email"));
  hidden("customer_name", script.getAttribute("data-customer-name"));
  hidden("customer_phone", script.getAttribute("data-customer-phone"));

  var button = document.createElement("button");
  button.type = "submit";
  button.textContent = script.getAttribute("data-label") || "Subscribe Now";
  button.style.border = "0";
  button.style.borderRadius = "8px";
  button.style.padding = "12px 18px";
  button.style.cursor = "pointer";
  button.style.font = "600 15px system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  button.style.background = script.getAttribute("data-background") || "#0f766e";
  button.style.color = script.getAttribute("data-color") || "#ffffff";
  form.appendChild(button);

  script.parentNode.insertBefore(form, script.nextSibling);
})();
"""
    response = HttpResponse(javascript, content_type="application/javascript")
    response["Cache-Control"] = "public, max-age=300"
    return response


def _json_or_html_error(request, message, status=400):
    accept_header = request.META.get("HTTP_ACCEPT", "")
    if "application/json" in accept_header:
        return JsonResponse({"ok": False, "error": message}, status=status)
    return HttpResponse(message, status=status)


def _compact_payment_dict(value):
    if not isinstance(value, dict):
        return {}
    compacted = {}
    for key, item in value.items():
        if isinstance(item, dict):
            nested = _compact_payment_dict(item)
            if nested:
                compacted[key] = nested
        elif item not in (None, ""):
            compacted[key] = str(item).strip() if isinstance(item, str) else item
    return compacted


def _paymongo_customer_metadata(metadata, billing_details=None):
    metadata = dict(metadata or {})
    billing_details = _compact_payment_dict(billing_details or {})
    if billing_details:
        existing_billing = metadata.get("paymongo_billing") or {}
        if isinstance(existing_billing, dict):
            existing_billing.update(billing_details)
            metadata["paymongo_billing"] = _compact_payment_dict(existing_billing)
        else:
            metadata["paymongo_billing"] = billing_details
    return metadata


def _update_customer_billing_details(customer, billing_details):
    if customer is None or not billing_details:
        return
    metadata = _paymongo_customer_metadata(customer.metadata, billing_details)
    changed_fields = []
    if customer.metadata != metadata:
        customer.metadata = metadata
        changed_fields.append("metadata")
    name = _clean_payment_value(billing_details.get("name"))
    phone = _clean_payment_value(billing_details.get("phone"))
    if name and not customer.name:
        customer.name = name
        changed_fields.append("name")
    if phone and not customer.phone:
        customer.phone = phone
        changed_fields.append("phone")
    if changed_fields:
        customer.save(update_fields=list(dict.fromkeys(changed_fields + ["updated_at"])))
        _payment_flow_print(
            "_update_customer_billing_details",
            "customer_billing_saved",
            f"customer_id={customer.pk} fields={','.join(changed_fields)}",
        )


def _paymongo_customer_id_from_response(response):
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        return _clean_payment_value(data.get("id")) or None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                paymongo_customer_id = _clean_payment_value(item.get("id"))
                if paymongo_customer_id:
                    return paymongo_customer_id
    return None


def _paymongo_customer_phone(value):
    phone = _clean_payment_value(value)
    if not phone:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) < 7 or len(digits) > 15:
        return None
    if phone.startswith("+"):
        return f"+{digits}"
    if digits.startswith("09") and len(digits) == 11:
        return f"+63{digits[1:]}"
    if digits.startswith("9") and len(digits) == 10:
        return f"+63{digits}"
    if digits.startswith("63") and len(digits) == 12:
        return f"+{digits}"
    return None


def _save_paymongo_customer_sync(customer, paymongo_customer_id, raw_response, sync_source):
    if customer is None or not paymongo_customer_id:
        return customer

    metadata = dict(customer.metadata or {})
    metadata["paymongo_customer_sync_source"] = sync_source
    metadata["paymongo_customer_last_response"] = raw_response
    metadata["paymongo_customer_synced_at"] = timezone.now().isoformat()
    update_fields = ["metadata", "updated_at"]

    if customer.paymongo_customer_id != paymongo_customer_id:
        customer.paymongo_customer_id = paymongo_customer_id
        update_fields.append("paymongo_customer_id")

    customer.metadata = metadata
    try:
        customer.save(update_fields=list(dict.fromkeys(update_fields)))
    except IntegrityError as exc:
        _payment_flow_print(
            "_save_paymongo_customer_sync",
            "customer_sync_id_conflict",
            f"customer_id={customer.pk} paymongo_customer_id={paymongo_customer_id} error={exc}",
        )
        metadata["paymongo_customer_sync_error"] = f"Duplicate PayMongo customer id: {paymongo_customer_id}"
        customer.paymongo_customer_id = None
        customer.metadata = metadata
        customer.save(update_fields=["metadata", "updated_at"])
        return customer

    _payment_flow_print(
        "_save_paymongo_customer_sync",
        "customer_sync_saved",
        f"customer_id={customer.pk} paymongo_customer_id={paymongo_customer_id} source={sync_source}",
    )
    return customer


def _sync_paymongo_customer_resource(customer):
    if customer is None:
        return None

    if not getattr(settings, "PAYMONGO_CREATE_CUSTOMER_RESOURCE", True):
        _payment_flow_print(
            "_sync_paymongo_customer_resource",
            "customer_sync_skip",
            "PAYMONGO_CREATE_CUSTOMER_RESOURCE is false",
        )
        return customer

    if customer.paymongo_customer_id:
        _payment_flow_print(
            "_sync_paymongo_customer_resource",
            "customer_sync_skip",
            f"customer_id={customer.pk} already has paymongo_customer_id={customer.paymongo_customer_id}",
        )
        return customer

    if not customer.email:
        _payment_flow_print(
            "_sync_paymongo_customer_resource",
            "customer_sync_skip",
            f"customer_id={customer.pk} missing email",
        )
        return customer

    try:
        client = PayMongoClient()
        customer_api_version = str(getattr(settings, "PAYMONGO_CUSTOMER_API_VERSION", "v2")).lower()
        if customer_api_version == "v1":
            _payment_flow_print(
                "_sync_paymongo_customer_resource",
                "customer_lookup_start",
                f"customer_id={customer.pk} email={customer.email}",
            )
            try:
                lookup_response = client.retrieve_customer(email=customer.email)
                paymongo_customer_id = _paymongo_customer_id_from_response(lookup_response)
                if paymongo_customer_id:
                    return _save_paymongo_customer_sync(
                        customer,
                        paymongo_customer_id,
                        lookup_response,
                        "lookup",
                    )
            except PayMongoAPIError as exc:
                _payment_flow_print(
                    "_sync_paymongo_customer_resource",
                    "customer_lookup_failed",
                    f"customer_id={customer.pk} error={exc}",
                )
        else:
            _payment_flow_print(
                "_sync_paymongo_customer_resource",
                "customer_lookup_skip",
                f"customer_id={customer.pk} api_version={customer_api_version}",
            )

        _payment_flow_print(
            "_sync_paymongo_customer_resource",
            "customer_create_start",
            f"customer_id={customer.pk} email={customer.email} api_version={customer_api_version}",
        )
        phone = _paymongo_customer_phone(customer.phone)
        try:
            create_response = client.create_customer(
                email=customer.email,
                name=customer.name,
                phone=phone,
            )
        except PayMongoAPIError as exc:
            if not phone:
                raise
            _payment_flow_print(
                "_sync_paymongo_customer_resource",
                "customer_create_retry_without_phone",
                f"customer_id={customer.pk} error={exc}",
            )
            create_response = client.create_customer(
                email=customer.email,
                name=customer.name,
                phone=None,
            )

        paymongo_customer_id = _paymongo_customer_id_from_response(create_response)
        return _save_paymongo_customer_sync(
            customer,
            paymongo_customer_id,
            create_response,
            "create",
        )
    except (PayMongoAPIError, ImproperlyConfigured, OperationalError) as exc:
        metadata = dict(customer.metadata or {})
        metadata["paymongo_customer_sync_error"] = str(exc)[:500]
        metadata["paymongo_customer_sync_failed_at"] = timezone.now().isoformat()
        customer.metadata = metadata
        customer.save(update_fields=["metadata", "updated_at"])
        _payment_flow_print(
            "_sync_paymongo_customer_resource",
            "customer_sync_failed",
            f"customer_id={customer.pk} error={exc}",
        )
        return customer


def _get_or_create_customer(source_website, *, email, name, phone, billing_details=None):
    _payment_flow_print(
        "_get_or_create_customer",
        "customer_input",
        f"source={source_website.slug} raw_email={email or '-'} raw_name={name or '-'} raw_phone={phone or '-'}",
    )
    email = (email or "").strip().lower() or None
    name = (name or "").strip() or None
    phone = (phone or "").strip() or None
    _payment_flow_print(
        "_get_or_create_customer",
        "customer_normalized",
        f"email={email or '-'} name={name or '-'} phone={phone or '-'}",
    )

    if not email and not name and not phone:
        _payment_flow_print("_get_or_create_customer", "customer_skip", "no customer details supplied")
        return None

    if email:
        _payment_flow_print("_get_or_create_customer", "customer_lookup", f"email={email}")
        customer = Customer.objects.filter(
            source_website=source_website,
            email__iexact=email,
        ).order_by("id").first()
        if customer:
            _payment_flow_print("_get_or_create_customer", "customer_found", f"customer_id={customer.pk}")
            changed_fields = []
            if name and customer.name != name:
                customer.name = name
                changed_fields.append("name")
            if phone and customer.phone != phone:
                customer.phone = phone
                changed_fields.append("phone")
            if billing_details:
                merged_metadata = _paymongo_customer_metadata(customer.metadata, billing_details)
                if customer.metadata != merged_metadata:
                    customer.metadata = merged_metadata
                    changed_fields.append("metadata")
            if changed_fields:
                customer.save(update_fields=changed_fields)
                _payment_flow_print(
                    "_get_or_create_customer",
                    "customer_updated",
                    f"customer_id={customer.pk} fields={','.join(changed_fields)}",
                )
            else:
                _payment_flow_print("_get_or_create_customer", "customer_unchanged", f"customer_id={customer.pk}")
            return _sync_paymongo_customer_resource(customer)

    customer = Customer.objects.create(
        source_website=source_website,
        email=email,
        name=name,
        phone=phone,
        metadata=_paymongo_customer_metadata({}, billing_details),
    )
    _payment_flow_print("_get_or_create_customer", "customer_created", f"customer_id={customer.pk}")
    return _sync_paymongo_customer_resource(customer)


@csrf_exempt
@require_POST
def start_paymongo_checkout(request, button_public_id):
    _payment_flow_print(
        "start_paymongo_checkout",
        "request_received",
        f"button_public_id={button_public_id} method={request.method}",
    )
    button = get_object_or_404(
        PaymentButton.objects.select_related("source_website", "product", "plan"),
        public_id=button_public_id,
        active=True,
        source_website__active=True,
        plan__status="active",
    )
    _payment_flow_print(
        "start_paymongo_checkout",
        "button_loaded",
        (
            f"button={button.public_id} source={button.source_website.slug} "
            f"product_id={button.product_id} plan_id={button.plan_id} mode={button.checkout_mode}"
        ),
    )

    origin = request_origin(request)
    _payment_flow_print(
        "start_paymongo_checkout",
        "origin_detected",
        f"origin={origin or '-'} allowed={button.source_website.allowed_origins or []}",
    )
    if not origin_is_allowed(button.source_website, origin):
        _payment_flow_print("start_paymongo_checkout", "origin_rejected", f"origin={origin or '-'}")
        return _json_or_html_error(request, "Payment button origin is not allowed.", status=403)
    _payment_flow_print("start_paymongo_checkout", "origin_accepted", f"origin={origin or '-'}")

    try:
        _payment_flow_print("start_paymongo_checkout", "embed_token_check", "verifying signed payment button token")
        verify_embed_token(request.POST.get("embed_token"), button)
    except SuspiciousOperation as exc:
        _payment_flow_print("start_paymongo_checkout", "embed_token_rejected", str(exc))
        return _json_or_html_error(request, str(exc), status=403)
    _payment_flow_print("start_paymongo_checkout", "embed_token_accepted", "signed token matched button and source")

    if button.checkout_mode == "paymongo_recurring" and not getattr(settings, "PAYMONGO_ENABLE_RECURRING", True):
        _payment_flow_print("start_paymongo_checkout", "recurring_rejected", "PAYMONGO_ENABLE_RECURRING is false")
        return _json_or_html_error(request, "PayMongo recurring billing is not enabled.", status=400)
    _payment_flow_print("start_paymongo_checkout", "checkout_mode_accepted", f"mode={button.checkout_mode}")

    customer = _get_or_create_customer(
        button.source_website,
        email=request.POST.get("customer_email"),
        name=request.POST.get("customer_name"),
        phone=request.POST.get("customer_phone"),
    )
    _payment_flow_print(
        "start_paymongo_checkout",
        "customer_ready",
        f"customer_id={getattr(customer, 'pk', None) or '-'} email={getattr(customer, 'email', None) or '-'}",
    )

    try:
        amount_centavos = amount_to_centavos(button.plan.price)
    except ValueError as exc:
        _payment_flow_print("start_paymongo_checkout", "amount_rejected", str(exc))
        return _json_or_html_error(request, str(exc), status=400)
    _payment_flow_print(
        "start_paymongo_checkout",
        "amount_calculated",
        f"plan_price={button.plan.price} currency={button.plan.currency} centavos={amount_centavos}",
    )

    payment_transaction = Transaction.objects.create(
        source_website=button.source_website,
        product=button.product,
        plan=button.plan,
        payment_button=button,
        customer=customer,
        customer_email=getattr(customer, "email", None),
        customer_name=getattr(customer, "name", None),
        customer_phone=getattr(customer, "phone", None),
        amount=button.plan.price,
        amount_centavos=amount_centavos,
        currency=(button.plan.currency or "PHP").upper(),
        paymongo_reference_number=button.payment_link_reference,
        checkout_url=button.payment_link_url if button.checkout_mode == "paymongo_link" else None,
    )
    _payment_flow_print(
        "start_paymongo_checkout",
        "transaction_created",
        (
            f"reference={payment_transaction.internal_reference_id} "
            f"transaction_id={payment_transaction.pk} status={payment_transaction.status}"
        ),
    )

    metadata = build_checkout_metadata(
        source_website=button.source_website,
        product=button.product,
        plan=button.plan,
        customer_email=payment_transaction.customer_email,
        internal_reference_id=payment_transaction.internal_reference_id,
    )
    metadata.update(button.metadata or {})
    if button.checkout_mode == "paymongo_link":
        metadata["paymongo_payment_link_reference"] = button.payment_link_reference or ""
        metadata["paymongo_payment_link_url"] = button.payment_link_url or ""
    _payment_flow_print(
        "start_paymongo_checkout",
        "metadata_built",
        f"reference={payment_transaction.internal_reference_id} metadata_keys={','.join(sorted(metadata.keys()))}",
    )

    if button.checkout_mode == "paymongo_link":
        if not button.payment_link_url or not button.payment_link_reference:
            _payment_flow_print(
                "start_paymongo_checkout",
                "payment_link_rejected",
                "missing PayMongo payment link URL or reference number",
            )
            payment_transaction.status = "failed"
            payment_transaction.failure_reason = "Payment button is missing PayMongo payment link URL or reference number."
            payment_transaction.save(update_fields=["status", "failure_reason", "updated_at"])
            return _json_or_html_error(request, "Payment button is missing PayMongo payment link details.", status=400)

        payment_transaction.status = "checkout_created"
        payment_transaction.paymongo_status = "payment_link_redirected"
        payment_transaction.raw_checkout_request = {
            "mode": "paymongo_link",
            "payment_link_url": button.payment_link_url,
            "payment_link_reference": button.payment_link_reference,
            "metadata": metadata,
        }
        payment_transaction.save(
            update_fields=[
                "status",
                "paymongo_status",
                "raw_checkout_request",
                "updated_at",
            ]
        )
        _payment_flow_print(
            "start_paymongo_checkout",
            "redirect_to_paymongo_link",
            (
                f"reference={payment_transaction.internal_reference_id} "
                f"payment_link_reference={button.payment_link_reference}"
            ),
        )
        return redirect(button.payment_link_url)

    try:
        client = PayMongoClient()
        _payment_flow_print(
            "start_paymongo_checkout",
            "paymongo_checkout_create",
            f"reference={payment_transaction.internal_reference_id}",
        )
        checkout_request, checkout_response = client.create_checkout_session(
            transaction=payment_transaction,
            line_item_name=button.plan.name,
            description=button.description or button.plan.description or button.product.description or button.plan.name,
            success_url=_return_url(request, payment_transaction, "success"),
            cancel_url=_return_url(request, payment_transaction, "cancel"),
            metadata=metadata,
        )
    except (PayMongoAPIError, ImproperlyConfigured) as exc:
        _payment_flow_print(
            "start_paymongo_checkout",
            "paymongo_checkout_failed",
            f"reference={payment_transaction.internal_reference_id} error={exc}",
        )
        payment_transaction.status = "failed"
        payment_transaction.failure_reason = str(exc)
        payment_transaction.save(update_fields=["status", "failure_reason", "updated_at"])
        return _json_or_html_error(request, "Unable to create PayMongo checkout session.", status=502)

    checkout_url = checkout_url_from_response(checkout_response)
    checkout_session_id = checkout_session_id_from_response(checkout_response)
    _payment_flow_print(
        "start_paymongo_checkout",
        "paymongo_checkout_response",
        f"reference={payment_transaction.internal_reference_id} checkout_session_id={checkout_session_id or '-'}",
    )
    if not checkout_url:
        _payment_flow_print(
            "start_paymongo_checkout",
            "paymongo_checkout_missing_url",
            f"reference={payment_transaction.internal_reference_id}",
        )
        payment_transaction.status = "failed"
        payment_transaction.failure_reason = "PayMongo did not return a checkout_url."
        payment_transaction.raw_checkout_request = checkout_request
        payment_transaction.raw_checkout_response = checkout_response
        payment_transaction.save(
            update_fields=[
                "status",
                "failure_reason",
                "raw_checkout_request",
                "raw_checkout_response",
                "updated_at",
            ]
        )
        return _json_or_html_error(request, "PayMongo did not return a checkout URL.", status=502)

    payment_transaction.status = "checkout_created"
    payment_transaction.paymongo_checkout_session_id = checkout_session_id
    payment_transaction.checkout_url = checkout_url
    payment_transaction.raw_checkout_request = checkout_request
    payment_transaction.raw_checkout_response = checkout_response
    payment_transaction.save(
        update_fields=[
            "status",
            "paymongo_checkout_session_id",
            "checkout_url",
            "raw_checkout_request",
            "raw_checkout_response",
            "updated_at",
        ]
    )
    _payment_flow_print(
        "start_paymongo_checkout",
        "redirect_to_paymongo",
        f"reference={payment_transaction.internal_reference_id} checkout_url={checkout_url}",
    )

    return redirect(checkout_url)


def _find_transaction_from_payload(payload):
    metadata = extract_metadata(payload)
    internal_reference_id = metadata.get("internal_reference_id")
    identifiers = extract_payment_identifiers(payload)

    qs = Transaction.objects.select_for_update()
    if internal_reference_id:
        transaction_obj = qs.filter(internal_reference_id=internal_reference_id).first()
        if transaction_obj:
            return transaction_obj, metadata, identifiers

    lookup_fields = {
        "paymongo_checkout_session_id": identifiers.get("checkout_session_id"),
        "paymongo_payment_id": identifiers.get("payment_id"),
        "paymongo_payment_intent_id": identifiers.get("payment_intent_id"),
        "paymongo_subscription_id": identifiers.get("subscription_id"),
    }
    for field_name, value in lookup_fields.items():
        if value:
            transaction_obj = qs.filter(**{field_name: value}).first()
            if transaction_obj:
                return transaction_obj, metadata, identifiers

    transaction_obj = _find_or_create_payment_link_transaction(payload, identifiers)
    if transaction_obj:
        return transaction_obj, metadata, identifiers

    return None, metadata, identifiers


def _find_or_create_payment_link_transaction(payload, identifiers):
    external_reference_number = (identifiers.get("external_reference_number") or "").strip()
    if not external_reference_number:
        return None

    _payment_flow_print(
        "_find_or_create_payment_link_transaction",
        "reference_lookup",
        f"payment_link_reference={external_reference_number}",
    )
    existing_transaction = (
        Transaction.objects.select_for_update()
        .filter(
            payment_button__checkout_mode="paymongo_link",
            paymongo_reference_number__iexact=external_reference_number,
            status__in=["pending", "checkout_created"],
            paymongo_payment_id__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if existing_transaction:
        _payment_flow_print(
            "_find_or_create_payment_link_transaction",
            "pending_transaction_found",
            f"reference={existing_transaction.internal_reference_id}",
        )
        return existing_transaction

    button = (
        PaymentButton.objects.select_related("source_website", "product", "plan")
        .filter(
            checkout_mode="paymongo_link",
            payment_link_reference__iexact=external_reference_number,
            active=True,
            source_website__active=True,
            plan__status="active",
        )
        .order_by("-created_at")
        .first()
    )
    if not button:
        _payment_flow_print(
            "_find_or_create_payment_link_transaction",
            "button_not_found",
            f"payment_link_reference={external_reference_number}",
        )
        return None

    try:
        amount_centavos = amount_to_centavos(button.plan.price)
    except ValueError as exc:
        _payment_flow_print(
            "_find_or_create_payment_link_transaction",
            "amount_rejected",
            f"button={button.public_id} error={exc}",
        )
        return None

    transaction_obj = Transaction.objects.create(
        source_website=button.source_website,
        product=button.product,
        plan=button.plan,
        payment_button=button,
        amount=button.plan.price,
        amount_centavos=amount_centavos,
        currency=(button.plan.currency or "PHP").upper(),
        status="pending",
        checkout_url=button.payment_link_url,
        paymongo_link_id=identifiers.get("payment_link_id"),
        paymongo_reference_number=external_reference_number,
        raw_checkout_request={
            "mode": "paymongo_link_webhook_only",
            "payment_link_url": button.payment_link_url,
            "payment_link_reference": external_reference_number,
        },
        raw_webhook_payload=payload,
    )
    _payment_flow_print(
        "_find_or_create_payment_link_transaction",
        "transaction_created",
        f"reference={transaction_obj.internal_reference_id} button={button.public_id}",
    )
    return transaction_obj


def _status_for_paymongo_event(event_type, paymongo_status):
    event_type = event_type or ""
    paymongo_status = (paymongo_status or "").lower()

    if event_type.startswith("subscription."):
        return None
    if event_type in {"checkout_session.payment.paid", "link.payment.paid", "payment.paid"} or paymongo_status in {"paid", "succeeded"}:
        return "paid"
    if event_type in {"payment.failed", "checkout_session.payment.failed", "link.payment.failed"} or paymongo_status in {"failed"}:
        return "failed"
    if event_type in {"payment.refunded", "payment.refund.updated"}:
        return "refunded"
    if paymongo_status in {"cancelled", "canceled"}:
        return "cancelled"
    if paymongo_status == "expired":
        return "expired"
    return None


def _normalize_paymongo_subscription_status(value):
    return (value or "").strip().lower().replace("canceled", "cancelled")


def _subscription_status_from_event(event_type, paymongo_status):
    event_type = event_type or ""
    paymongo_status = _normalize_paymongo_subscription_status(paymongo_status)

    if event_type in {"subscription.activated", "subscription.invoice.paid"} or paymongo_status == "active":
        return "active"
    if event_type in {"subscription.past_due", "subscription.invoice.payment_failed"}:
        return "past_due"
    if event_type == "subscription.unpaid" or paymongo_status == "unpaid":
        return "unpaid"
    if event_type == "subscription.updated" and paymongo_status in {"cancelled", "incomplete_cancelled", "incomplete"}:
        return paymongo_status
    if paymongo_status in {"cancelled", "incomplete_cancelled", "incomplete", "past_due"}:
        return paymongo_status
    if event_type in {"payment.failed", "checkout_session.payment.failed", "link.payment.failed"}:
        return "failed"
    if event_type in {"payment.refunded", "payment.refund.updated"}:
        return "cancelled"
    return None


def _legacy_status_for_subscription_status(local_status):
    if local_status == "active":
        return "ACTIVE"
    if local_status in {"cancelled", "incomplete_cancelled"}:
        return "CANCELLED"
    if local_status == "expired":
        return "EXPIRED"
    if local_status == "failed":
        return "FAILED"
    if local_status == "unpaid":
        return "UNPAID"
    if local_status == "past_due":
        return "PAST_DUE"
    return "SUSPENDED"


def _subscription_status_label(details, local_status):
    paymongo_status = _normalize_paymongo_subscription_status(details.get("paymongo_status"))
    if paymongo_status in {"active", "past_due", "unpaid", "cancelled", "incomplete", "incomplete_cancelled"}:
        return paymongo_status.upper()
    return (local_status or "SUSPENDED").upper()


def _subscription_access_enabled(local_status):
    return local_status == "active"


def _payload_event_attributes(payload):
    data = payload.get("data") if isinstance(payload, dict) else {}
    event_attributes = data.get("attributes") if isinstance(data, dict) else {}
    return event_attributes if isinstance(event_attributes, dict) else {}


def _payload_event_object(payload):
    event_attributes = _payload_event_attributes(payload)
    event_object = event_attributes.get("data") or {}
    return event_object if isinstance(event_object, dict) else {}


def _payload_event_object_attributes(payload):
    event_object = _payload_event_object(payload)
    attributes = event_object.get("attributes") or {}
    return attributes if isinstance(attributes, dict) else {}


def _paymongo_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=dt_timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return None


def _subscription_payload_details(payload, event_type, identifiers):
    event_object = _payload_event_object(payload)
    attributes = _payload_event_object_attributes(payload)
    object_type = event_object.get("type") or ""
    subscription_id = identifiers.get("subscription_id")
    invoice_id = None
    invoice_status = None
    payment_intent_id = identifiers.get("payment_intent_id")
    paymongo_status = identifiers.get("paymongo_status")

    if object_type == "subscription" or str(event_object.get("id") or "").startswith(("sub_", "subs_")):
        subscription_id = subscription_id or event_object.get("id") or attributes.get("id")
        paymongo_status = attributes.get("status") or paymongo_status
    elif object_type == "invoice" or str(event_object.get("id") or "").startswith("inv_"):
        invoice_id = event_object.get("id") or attributes.get("id")
        invoice_status = attributes.get("status")
        subscription_id = subscription_id or attributes.get("subscription_id")
        payment_intent_id = payment_intent_id or attributes.get("payment_intent_id")

    local_status = _subscription_status_from_event(event_type, paymongo_status)
    return {
        "local_status": local_status,
        "paymongo_status": _normalize_paymongo_subscription_status(paymongo_status) or None,
        "subscription_id": subscription_id,
        "invoice_id": invoice_id,
        "invoice_status": invoice_status,
        "payment_intent_id": payment_intent_id,
        "customer_id": attributes.get("customer_id"),
        "plan_id": attributes.get("plan_id"),
        "cancelled_at": _paymongo_datetime(attributes.get("cancelled_at")),
        "next_billing_schedule": _paymongo_datetime(attributes.get("next_billing_schedule")),
        "raw_attributes": attributes,
    }


def _find_subscription_for_event(transaction_obj, details):
    subscription_id = details.get("subscription_id")
    qs = Subscription.objects.select_for_update()
    if subscription_id:
        subscription_obj = qs.filter(paymongo_subscription_id=subscription_id).order_by("-created_at").first()
        if subscription_obj:
            return subscription_obj

    if transaction_obj:
        subscription_obj = (
            transaction_obj.activated_subscriptions.select_for_update()
            .order_by("-created_at")
            .first()
        )
        if subscription_obj:
            return subscription_obj

        if transaction_obj.customer_id:
            return (
                qs.filter(
                    customer=transaction_obj.customer,
                    source_website=transaction_obj.source_website,
                    plan=transaction_obj.plan,
                )
                .order_by("-created_at")
                .first()
            )

    return None


def _find_user_subscription_for_event(transaction_obj, subscription_obj, details):
    subscription_id = details.get("subscription_id")
    qs = UserSubscription.objects.select_for_update()
    if subscription_id:
        user_subscription = qs.filter(paymongo_subscription_id=subscription_id).order_by("-created_at").first()
        if user_subscription:
            return user_subscription

    if transaction_obj:
        user_subscription = qs.filter(receipt_number=transaction_obj.internal_reference_id).order_by("-created_at").first()
        if user_subscription:
            return user_subscription

    if subscription_obj and subscription_obj.transaction_id:
        user_subscription = qs.filter(receipt_number=subscription_obj.transaction.internal_reference_id).order_by("-created_at").first()
        if user_subscription:
            return user_subscription

    if subscription_obj and subscription_obj.customer_id:
        customer_email = _normalize_payment_email(getattr(subscription_obj.customer, "email", ""))
        if customer_email:
            user_subscription = qs.filter(email__iexact=customer_email, plan=subscription_obj.plan).order_by("-created_at").first()
            if user_subscription:
                return user_subscription

    return None


def _update_paymongo_subscription_access(transaction_obj, payload, event_type, identifiers):
    details = _subscription_payload_details(payload, event_type, identifiers)
    local_status = details.get("local_status")
    subscription_id = details.get("subscription_id")

    if not local_status:
        return False

    _payment_flow_print(
        "_update_paymongo_subscription_access",
        "subscription_event_start",
        f"event_type={event_type or '-'} subscription_id={subscription_id or '-'} local_status={local_status}",
    )
    subscription_obj = _find_subscription_for_event(transaction_obj, details)
    user_subscription = _find_user_subscription_for_event(transaction_obj, subscription_obj, details)

    if not subscription_obj and not user_subscription:
        _payment_flow_print(
            "_update_paymongo_subscription_access",
            "subscription_not_found",
            f"subscription_id={subscription_id or '-'}",
        )
        return False

    now = timezone.now()
    metadata_update = {
        "last_paymongo_event_type": event_type,
        "last_paymongo_status": details.get("paymongo_status") or local_status,
        "last_paymongo_invoice_id": details.get("invoice_id"),
        "last_paymongo_invoice_status": details.get("invoice_status"),
        "last_paymongo_payment_intent_id": details.get("payment_intent_id"),
        "last_paymongo_event_at": now.isoformat(),
    }

    if subscription_obj:
        subscription_fields = ["status", "metadata", "updated_at"]
        subscription_obj.status = local_status
        if subscription_id and subscription_obj.paymongo_subscription_id != subscription_id:
            subscription_obj.paymongo_subscription_id = subscription_id
            subscription_fields.append("paymongo_subscription_id")
        if details.get("next_billing_schedule"):
            subscription_obj.current_period_end = details["next_billing_schedule"]
            subscription_fields.append("current_period_end")
        if local_status == "active" and not subscription_obj.current_period_start:
            subscription_obj.current_period_start = now
            subscription_fields.append("current_period_start")
        subscription_metadata = dict(subscription_obj.metadata or {})
        subscription_metadata.update(_compact_payment_dict(metadata_update))
        subscription_obj.metadata = subscription_metadata
        subscription_obj.save(update_fields=list(dict.fromkeys(subscription_fields)))
        _payment_flow_print(
            "_update_paymongo_subscription_access",
            "local_subscription_updated",
            f"subscription_id={subscription_obj.pk} status={subscription_obj.status}",
        )

    if user_subscription:
        legacy_status = _legacy_status_for_subscription_status(local_status)
        user_subscription.status = legacy_status
        user_subscription.subscription_status = _subscription_status_label(details, local_status)
        if subscription_id:
            user_subscription.paymongo_subscription_id = subscription_id
        if subscription_obj and subscription_obj.current_period_end:
            user_subscription.next_billing_time = subscription_obj.current_period_end
        if local_status == "active":
            user_subscription.last_payment_date = now
        if local_status in {"past_due", "unpaid", "failed"}:
            user_subscription.failed_payments_count = (user_subscription.failed_payments_count or 0) + 1

        billing_info = dict(user_subscription.billing_info or {})
        billing_info.update(_compact_payment_dict(metadata_update))
        billing_info["access_enabled"] = _subscription_access_enabled(local_status)
        user_subscription.billing_info = billing_info
        user_subscription.save()
        _payment_flow_print(
            "_update_paymongo_subscription_access",
            "user_subscription_updated",
            f"user_subscription_id={user_subscription.pk} status={user_subscription.status} subscription_status={user_subscription.subscription_status}",
        )

    return True


def _activate_subscription_for_transaction(transaction_obj, identifiers):
    _payment_flow_print(
        "_activate_subscription_for_transaction",
        "subscription_activation_start",
        f"reference={transaction_obj.internal_reference_id} customer_id={getattr(transaction_obj.customer, 'pk', None) or '-'}",
    )
    now = timezone.now()
    current_subscription = None

    if transaction_obj.customer:
        _payment_flow_print(
            "_activate_subscription_for_transaction",
            "subscription_lookup",
            f"customer_id={transaction_obj.customer_id} plan_id={transaction_obj.plan_id}",
        )
        current_subscription = (
            Subscription.objects.select_for_update()
            .filter(
                customer=transaction_obj.customer,
                source_website=transaction_obj.source_website,
                plan=transaction_obj.plan,
            )
            .order_by("-current_period_end", "-created_at")
            .first()
        )
        if current_subscription:
            _payment_flow_print(
                "_activate_subscription_for_transaction",
                "subscription_found",
                f"subscription_id={current_subscription.pk} status={current_subscription.status}",
            )
        else:
            _payment_flow_print("_activate_subscription_for_transaction", "subscription_not_found", "creating new subscription")

    if current_subscription and current_subscription.current_period_end and current_subscription.current_period_end > now:
        period_start = current_subscription.current_period_end
    else:
        period_start = now

    period_end = None
    if transaction_obj.plan.type == "subscription":
        period_end = Subscription.period_end_for_plan(transaction_obj.plan, period_start)
    _payment_flow_print(
        "_activate_subscription_for_transaction",
        "subscription_period_calculated",
        f"period_start={period_start.isoformat()} period_end={period_end.isoformat() if period_end else '-'}",
    )

    if not current_subscription:
        current_subscription = Subscription.objects.create(
            customer=transaction_obj.customer,
            source_website=transaction_obj.source_website,
            plan=transaction_obj.plan,
        )
        _payment_flow_print(
            "_activate_subscription_for_transaction",
            "subscription_created",
            f"subscription_id={current_subscription.pk}",
        )

    current_subscription.transaction = transaction_obj
    current_subscription.status = "active"
    current_subscription.current_period_start = period_start
    current_subscription.current_period_end = period_end
    current_subscription.paymongo_subscription_id = identifiers.get("subscription_id")
    current_subscription.metadata = {
        "activated_by_transaction": transaction_obj.internal_reference_id,
    }
    current_subscription.save(
        update_fields=[
            "transaction",
            "status",
            "current_period_start",
            "current_period_end",
            "paymongo_subscription_id",
            "metadata",
            "updated_at",
        ]
    )
    _payment_flow_print(
        "_activate_subscription_for_transaction",
        "subscription_activated",
        f"subscription_id={current_subscription.pk} status={current_subscription.status}",
    )
    return current_subscription


def _normalize_payment_email(value):
    email = _clean_payment_value(value).lower()
    if "@" not in email:
        return ""
    return email


def _unique_paymongo_username(UserModel, email):
    username_field = UserModel.USERNAME_FIELD
    max_length = UserModel._meta.get_field(username_field).max_length or 150
    base_username = email[:max_length]
    candidate = base_username
    counter = 1

    while UserModel._default_manager.filter(**{username_field: candidate}).exists():
        suffix = f"_{counter}"
        candidate = f"{base_username[:max_length - len(suffix)]}{suffix}"
        counter += 1

    return candidate


def _paymongo_backup_password(transaction_obj):
    backup_value = (
        f"paymongo:{transaction_obj.paymongo_payment_id}"
        if transaction_obj.paymongo_payment_id
        else f"paymongo:{transaction_obj.paymongo_checkout_session_id or transaction_obj.internal_reference_id}"
    )
    max_length = UserCredentialsBackUP._meta.get_field("userPassword").max_length
    return backup_value[:max_length]


def _ensure_paymongo_user_backup(user, transaction_obj):
    if user is None or not getattr(user, "pk", None):
        _payment_flow_print("_ensure_paymongo_user_backup", "backup_skip", "missing user")
        return None

    _payment_flow_print(
        "_ensure_paymongo_user_backup",
        "backup_lookup",
        f"user_id={user.pk} reference={transaction_obj.internal_reference_id}",
    )
    backup, created = UserCredentialsBackUP.objects.get_or_create(
        userID=user.pk,
        defaults={"userPassword": _paymongo_backup_password(transaction_obj)},
    )
    _payment_flow_print(
        "_ensure_paymongo_user_backup",
        "backup_created" if created else "backup_found",
        f"user_id={user.pk} backup_id={backup.pk}",
    )
    return backup


def _ensure_paymongo_user_profile(transaction_obj, metadata=None):
    _payment_flow_print(
        "_ensure_paymongo_user_profile",
        "user_profile_start",
        f"reference={transaction_obj.internal_reference_id}",
    )
    metadata = metadata or {}
    email = _normalize_payment_email(
        transaction_obj.customer_email
        or metadata.get("customer_email")
        or getattr(transaction_obj.customer, "email", "")
    )
    if not email:
        _payment_flow_print("_ensure_paymongo_user_profile", "user_profile_skip", "no valid email available")
        return None, None

    _payment_flow_print("_ensure_paymongo_user_profile", "user_lookup", f"email={email}")
    UserModel = get_user_model()
    user = UserModel._default_manager.filter(email__iexact=email).order_by("id").first()

    if user is None:
        _payment_flow_print("_ensure_paymongo_user_profile", "user_not_found", f"email={email}")
        user = UserModel._default_manager.create_user(
            username=_unique_paymongo_username(UserModel, email),
            email=email,
            password=None,
        )
        _payment_flow_print(
            "_ensure_paymongo_user_profile",
            "user_created",
            f"user_id={user.pk} username={user.username} email={user.email}",
        )
    else:
        _payment_flow_print(
            "_ensure_paymongo_user_profile",
            "user_found",
            f"user_id={user.pk} username={user.username} email={user.email or '-'}",
        )
        changed_fields = []
        if not getattr(user, "email", ""):
            user.email = email
            changed_fields.append("email")
        if changed_fields:
            user.save(update_fields=changed_fields)
            _payment_flow_print(
                "_ensure_paymongo_user_profile",
                "user_updated",
                f"user_id={user.pk} fields={','.join(changed_fields)}",
            )

    profile_name = (
        transaction_obj.customer_name
        or getattr(transaction_obj.customer, "name", "")
        or email
    )
    profile = ensure_user_profile(
        user,
        name=profile_name,
        contact=email,
        signed_from=f"paymongo:{transaction_obj.source_website.slug}",
        overwrite=False,
    )
    _sync_paymongo_profile_billing_details(profile, transaction_obj.customer_billing_details)
    _payment_flow_print(
        "_ensure_paymongo_user_profile",
        "profile_ready",
        f"user_id={user.pk} profile_id={profile.pk} contact={profile.contact or '-'}",
    )
    _ensure_paymongo_user_backup(user, transaction_obj)
    return user, profile


def _login_paymongo_success_user(request, transaction_obj):
    if transaction_obj.status != "paid":
        _payment_flow_print(
            "_login_paymongo_success_user",
            "login_skip",
            f"reference={transaction_obj.internal_reference_id} status={transaction_obj.status}",
        )
        return None

    email = _normalize_payment_email(
        transaction_obj.customer_email or getattr(transaction_obj.customer, "email", "")
    )
    if not email:
        _payment_flow_print(
            "_login_paymongo_success_user",
            "login_skip",
            f"reference={transaction_obj.internal_reference_id} missing customer email",
        )
        return None

    user, profile = _ensure_paymongo_user_profile(transaction_obj)
    if user is None:
        _payment_flow_print(
            "_login_paymongo_success_user",
            "login_skip",
            f"reference={transaction_obj.internal_reference_id} user not available",
        )
        return None

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.set_expiry(1209600)
    local_subscription = transaction_obj.activated_subscriptions.order_by("-created_at").first()
    legacy_subscription = UserSubscription.objects.filter(
        receipt_number=transaction_obj.internal_reference_id,
    ).order_by("-created_at").first()
    request.session["paymongo_last_success"] = {
        "transaction_reference": transaction_obj.internal_reference_id,
        "plan_id": transaction_obj.plan_id,
        "plan_name": transaction_obj.plan.name if transaction_obj.plan_id else "",
        "source_website": transaction_obj.source_website.slug if transaction_obj.source_website_id else "",
        "subscription_id": local_subscription.pk if local_subscription else None,
        "user_subscription_id": legacy_subscription.pk if legacy_subscription else None,
    }
    _payment_flow_print(
        "_login_paymongo_success_user",
        "login_success",
        f"reference={transaction_obj.internal_reference_id} user_id={user.pk} profile_id={getattr(profile, 'pk', None) or '-'}",
    )
    return user


def _sync_paymongo_profile_billing_details(profile, billing_details):
    if profile is None or not billing_details:
        return

    billing_details = _compact_payment_dict(billing_details)
    address = billing_details.get("address") or {}
    field_values = {
        "mobile_number": billing_details.get("phone"),
        "address_line1": address.get("line1"),
        "address_line2": address.get("line2"),
        "address_city": address.get("city"),
        "address_state": address.get("state"),
        "address_postal_code": address.get("postal_code"),
        "address_country": address.get("country"),
    }
    changed_fields = []
    for field_name, value in field_values.items():
        value = _clean_payment_value(value)
        if value and not getattr(profile, field_name, ""):
            setattr(profile, field_name, value)
            changed_fields.append(field_name)

    if billing_details and profile.paymongo_billing_details != billing_details:
        profile.paymongo_billing_details = billing_details
        changed_fields.append("paymongo_billing_details")

    if changed_fields:
        profile.save(update_fields=list(dict.fromkeys(changed_fields)))
        _payment_flow_print(
            "_sync_paymongo_profile_billing_details",
            "profile_billing_saved",
            f"profile_id={profile.pk} fields={','.join(changed_fields)}",
        )


def _ensure_legacy_user_subscription(transaction_obj, identifiers, subscription_obj=None, user=None, profile=None):
    _payment_flow_print(
        "_ensure_legacy_user_subscription",
        "user_subscription_start",
        f"reference={transaction_obj.internal_reference_id}",
    )
    paymongo_subscription_id = identifiers.get("subscription_id")

    existing_qs = UserSubscription.objects.select_for_update()
    user_subscription = None
    if paymongo_subscription_id:
        user_subscription = existing_qs.filter(paymongo_subscription_id=paymongo_subscription_id).first()
        if user_subscription:
            _payment_flow_print(
                "_ensure_legacy_user_subscription",
                "user_subscription_found_by_paymongo_id",
                f"user_subscription_id={user_subscription.pk} paymongo_subscription_id={paymongo_subscription_id}",
            )

    if user_subscription is None:
        user_subscription = existing_qs.filter(receipt_number=transaction_obj.internal_reference_id).first()
        if user_subscription:
            _payment_flow_print(
                "_ensure_legacy_user_subscription",
                "user_subscription_found_by_reference",
                f"user_subscription_id={user_subscription.pk}",
            )

    if user_subscription is None:
        user_subscription = UserSubscription(receipt_number=transaction_obj.internal_reference_id)
        _payment_flow_print("_ensure_legacy_user_subscription", "user_subscription_create", "creating legacy UserSubscription")

    user_subscription.user = user
    user_subscription.plan = transaction_obj.plan
    user_subscription.name = (
        transaction_obj.customer_name
        or getattr(transaction_obj.customer, "name", "")
        or getattr(user, "username", "")
        or transaction_obj.customer_email
    )
    user_subscription.email = transaction_obj.customer_email
    user_subscription.mobile_number = transaction_obj.customer_phone
    user_subscription.paymongo_customer_id = getattr(transaction_obj.customer, "paymongo_customer_id", None)
    if paymongo_subscription_id:
        user_subscription.paymongo_subscription_id = paymongo_subscription_id
    user_subscription.subscription_status = "ACTIVE"
    user_subscription.status = "ACTIVE"
    user_subscription.started_at = getattr(subscription_obj, "current_period_start", None) or transaction_obj.paid_at
    user_subscription.next_billing_time = getattr(subscription_obj, "current_period_end", None)
    user_subscription.last_payment_date = transaction_obj.paid_at
    user_subscription.last_payment_amount_value = transaction_obj.amount
    user_subscription.last_payment_amount_currency = transaction_obj.currency
    user_subscription.billing_info = {
        "source_website": transaction_obj.source_website.slug,
        "local_subscription_id": getattr(subscription_obj, "pk", None),
        "paymongo_billing": transaction_obj.customer_billing_details or {},
        "current_period_start": (
            subscription_obj.current_period_start.isoformat()
            if subscription_obj and subscription_obj.current_period_start
            else None
        ),
        "current_period_end": (
            subscription_obj.current_period_end.isoformat()
            if subscription_obj and subscription_obj.current_period_end
            else None
        ),
    }
    user_subscription.subscriber = {
        "name": user_subscription.name,
        "email": user_subscription.email,
        "phone": user_subscription.mobile_number,
        "address": (transaction_obj.customer_billing_details or {}).get("address", {}),
        "source_website": transaction_obj.source_website.slug,
    }
    user_subscription.last_payment = {
        "paymongo_payment_id": transaction_obj.paymongo_payment_id,
        "paymongo_checkout_session_id": transaction_obj.paymongo_checkout_session_id,
        "paymongo_payment_intent_id": transaction_obj.paymongo_payment_intent_id,
        "transaction_reference": transaction_obj.internal_reference_id,
    }
    user_subscription.save()
    _payment_flow_print(
        "_ensure_legacy_user_subscription",
        "user_subscription_saved",
        f"user_subscription_id={user_subscription.pk} status={user_subscription.status}",
    )

    if profile is not None and profile.user_subscription_id != user_subscription.pk:
        profile.user_subscription = user_subscription
        profile.save(update_fields=["user_subscription"])
        _payment_flow_print(
            "_ensure_legacy_user_subscription",
            "profile_user_subscription_linked",
            f"profile_id={profile.pk} user_subscription_id={user_subscription.pk}",
        )

    return user_subscription


def _clean_payment_value(value):
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    return str(value or "").strip()


def _billing_dicts_from_payload(value):
    if isinstance(value, dict):
        billing = value.get("billing")
        if isinstance(billing, dict):
            yield billing

        attributes = value.get("attributes")
        if isinstance(attributes, dict):
            billing = attributes.get("billing")
            if isinstance(billing, dict):
                yield billing
            yield from _billing_dicts_from_payload(attributes)

        data = value.get("data")
        if isinstance(data, dict):
            yield from _billing_dicts_from_payload(data)

        for child in value.values():
            if child is data or child is attributes:
                continue
            yield from _billing_dicts_from_payload(child)
    elif isinstance(value, list):
        for child in value:
            yield from _billing_dicts_from_payload(child)


def _first_billing_value(billing_dicts, keys):
    for billing in billing_dicts:
        for key in keys:
            value = _clean_payment_value(billing.get(key))
            if value:
                return value
    return ""


def _first_billing_address(billing_dicts):
    for billing in billing_dicts:
        address = billing.get("address")
        if isinstance(address, dict):
            compacted = _compact_payment_dict(
                {
                    "line1": address.get("line1") or address.get("address_line1"),
                    "line2": address.get("line2") or address.get("address_line2"),
                    "city": address.get("city"),
                    "state": address.get("state") or address.get("province") or address.get("region"),
                    "postal_code": address.get("postal_code") or address.get("zip") or address.get("zip_code"),
                    "country": address.get("country"),
                }
            )
            if compacted:
                return compacted

        compacted = _compact_payment_dict(
            {
                "line1": billing.get("address_line1") or billing.get("line1"),
                "line2": billing.get("address_line2") or billing.get("line2"),
                "city": billing.get("city"),
                "state": billing.get("state") or billing.get("province") or billing.get("region"),
                "postal_code": billing.get("postal_code") or billing.get("zip") or billing.get("zip_code"),
                "country": billing.get("country"),
            }
        )
        if compacted:
            return compacted
    return {}


def _first_payload_value(value, keys):
    if isinstance(value, dict):
        for key in keys:
            if key not in value:
                continue
            item = value.get(key)
            if isinstance(item, (dict, list, tuple, set)):
                found = _first_payload_value(item, keys)
                if found:
                    return found
                continue
            if item not in (None, ""):
                return item
        for item in value.values():
            found = _first_payload_value(item, keys)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _first_payload_value(item, keys)
            if found:
                return found
    return None


def _customer_details_from_webhook_payload(payload, metadata):
    metadata = metadata or {}
    billing_dicts = list(_billing_dicts_from_payload(payload))
    address = _first_billing_address(billing_dicts)
    email = _normalize_payment_email(
        metadata.get("customer_email")
        or _first_billing_value(billing_dicts, ("email_address", "email"))
        or _first_payload_value(payload, ("customer_email", "email_address", "email"))
    )
    name = (
        _clean_payment_value(metadata.get("customer_name"))
        or _first_billing_value(billing_dicts, ("name", "full_name", "customer_name"))
        or _clean_payment_value(_first_payload_value(payload, ("customer_name", "full_name")))
    )
    phone = (
        _clean_payment_value(metadata.get("customer_phone"))
        or _first_billing_value(billing_dicts, ("phone_number", "phone", "mobile_number"))
        or _clean_payment_value(_first_payload_value(payload, ("customer_phone", "phone_number", "phone")))
    )
    billing_details = _compact_payment_dict(
        {
            "email": email,
            "name": name,
            "phone": phone,
            "address": address,
        }
    )
    return {
        "email": email,
        "name": name,
        "phone": phone,
        "billing_details": billing_details,
    }


def _process_paymongo_event(webhook_event, payload, event_type):
    _payment_flow_print(
        "_process_paymongo_event",
        "event_processing_start",
        f"event_id={webhook_event.paymongo_event_id} event_type={event_type or '-'}",
    )
    transaction_obj, metadata, identifiers = _find_transaction_from_payload(payload)
    if not transaction_obj:
        if _update_paymongo_subscription_access(None, payload, event_type, identifiers):
            webhook_event.processing_status = "processed"
            webhook_event.error_message = ""
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=["processing_status", "error_message", "processed_at", "updated_at"])
            return None
        _payment_flow_print(
            "_process_paymongo_event",
            "transaction_not_found",
            f"event_id={webhook_event.paymongo_event_id}",
        )
        webhook_event.processing_status = "processed"
        webhook_event.error_message = "No matching transaction found."
        webhook_event.processed_at = timezone.now()
        webhook_event.save(update_fields=["processing_status", "error_message", "processed_at", "updated_at"])
        return None
    _payment_flow_print(
        "_process_paymongo_event",
        "transaction_found",
        f"reference={transaction_obj.internal_reference_id} transaction_id={transaction_obj.pk}",
    )

    was_already_paid = transaction_obj.status == "paid"
    new_status = _status_for_paymongo_event(event_type, identifiers.get("paymongo_status"))
    _payment_flow_print(
        "_process_paymongo_event",
        "status_mapped",
        f"event_type={event_type or '-'} paymongo_status={identifiers.get('paymongo_status') or '-'} new_status={new_status or '-'}",
    )
    update_fields = ["raw_webhook_payload", "paymongo_status", "updated_at"]
    transaction_obj.raw_webhook_payload = payload
    transaction_obj.paymongo_status = identifiers.get("paymongo_status")
    customer_details = _customer_details_from_webhook_payload(payload, metadata)
    billing_details = customer_details.get("billing_details") or {}
    _payment_flow_print(
        "_process_paymongo_event",
        "customer_details_extracted",
        (
            f"email={customer_details['email'] or '-'} "
            f"name={customer_details['name'] or '-'} phone={customer_details['phone'] or '-'}"
        ),
    )
    if billing_details and transaction_obj.customer_billing_details != billing_details:
        transaction_obj.customer_billing_details = billing_details
        update_fields.append("customer_billing_details")
        _payment_flow_print(
            "_process_paymongo_event",
            "transaction_billing_details_set",
            f"fields={','.join(sorted(billing_details.keys()))}",
        )

    if customer_details["email"] and not transaction_obj.customer_email:
        transaction_obj.customer_email = customer_details["email"]
        update_fields.append("customer_email")
        _payment_flow_print("_process_paymongo_event", "transaction_customer_email_set", customer_details["email"])
    if customer_details["name"] and not transaction_obj.customer_name:
        transaction_obj.customer_name = customer_details["name"]
        update_fields.append("customer_name")
        _payment_flow_print("_process_paymongo_event", "transaction_customer_name_set", customer_details["name"])
    if customer_details["phone"] and not transaction_obj.customer_phone:
        transaction_obj.customer_phone = customer_details["phone"]
        update_fields.append("customer_phone")
        _payment_flow_print("_process_paymongo_event", "transaction_customer_phone_set", customer_details["phone"])
    if customer_details["email"] and transaction_obj.customer is None:
        _payment_flow_print("_process_paymongo_event", "customer_record_create_or_lookup", customer_details["email"])
        transaction_obj.customer = _get_or_create_customer(
            transaction_obj.source_website,
            email=customer_details["email"],
            name=customer_details["name"],
            phone=customer_details["phone"],
            billing_details=billing_details,
        )
        update_fields.append("customer")
    elif billing_details and transaction_obj.customer is not None:
        _update_customer_billing_details(transaction_obj.customer, billing_details)

    identifier_field_map = {
        "paymongo_checkout_session_id": identifiers.get("checkout_session_id"),
        "paymongo_link_id": identifiers.get("payment_link_id"),
        "paymongo_reference_number": identifiers.get("external_reference_number"),
        "paymongo_payment_id": identifiers.get("payment_id"),
        "paymongo_payment_intent_id": identifiers.get("payment_intent_id"),
        "paymongo_subscription_id": identifiers.get("subscription_id"),
    }
    for field_name, value in identifier_field_map.items():
        if value and getattr(transaction_obj, field_name) != value:
            setattr(transaction_obj, field_name, value)
            update_fields.append(field_name)
            _payment_flow_print("_process_paymongo_event", "paymongo_identifier_set", f"{field_name}={value}")

    if new_status and transaction_obj.status != new_status:
        transaction_obj.status = new_status
        update_fields.append("status")
        _payment_flow_print("_process_paymongo_event", "transaction_status_set", f"status={new_status}")

    if new_status == "paid" and not transaction_obj.paid_at:
        transaction_obj.paid_at = timezone.now()
        update_fields.append("paid_at")
        _payment_flow_print("_process_paymongo_event", "transaction_paid_at_set", transaction_obj.paid_at.isoformat())

    transaction_obj.save(update_fields=list(dict.fromkeys(update_fields)))
    _payment_flow_print(
        "_process_paymongo_event",
        "transaction_saved",
        f"reference={transaction_obj.internal_reference_id} fields={','.join(list(dict.fromkeys(update_fields)))}",
    )

    if new_status == "paid":
        _payment_flow_print("_process_paymongo_event", "paid_flow_start", f"reference={transaction_obj.internal_reference_id}")
        if was_already_paid:
            _payment_flow_print(
                "_process_paymongo_event",
                "paid_side_effects_skip",
                f"reference={transaction_obj.internal_reference_id} transaction was already paid",
            )
        else:
            subscription_obj = _activate_subscription_for_transaction(transaction_obj, identifiers)
            user, profile = _ensure_paymongo_user_profile(transaction_obj, metadata=metadata)
            _ensure_legacy_user_subscription(
                transaction_obj,
                identifiers,
                subscription_obj=subscription_obj,
                user=user,
                profile=profile,
            )
    elif new_status == "refunded":
        _payment_flow_print("_process_paymongo_event", "refund_flow_start", f"reference={transaction_obj.internal_reference_id}")
        _update_paymongo_subscription_access(transaction_obj, payload, event_type, identifiers)
    elif new_status in {"failed", "cancelled", "expired"} or event_type in {
        "subscription.past_due",
        "subscription.unpaid",
        "subscription.updated",
        "subscription.invoice.payment_failed",
        "subscription.invoice.paid",
        "subscription.activated",
    }:
        _update_paymongo_subscription_access(transaction_obj, payload, event_type, identifiers)

    webhook_event.transaction = transaction_obj
    webhook_event.processing_status = "processed"
    webhook_event.processed_at = timezone.now()
    webhook_event.error_message = ""
    webhook_event.save(
        update_fields=[
            "transaction",
            "processing_status",
            "processed_at",
            "error_message",
            "updated_at",
        ]
    )
    _payment_flow_print(
        "_process_paymongo_event",
        "event_processed",
        f"event_id={webhook_event.paymongo_event_id} reference={transaction_obj.internal_reference_id}",
    )
    return transaction_obj


def _checkout_session_response_is_paid(checkout_response):
    attributes = checkout_response.get("data", {}).get("attributes", {}) if isinstance(checkout_response, dict) else {}
    checkout_status = (attributes.get("status") or "").lower()
    if checkout_status in {"paid", "succeeded"}:
        return True

    payments = attributes.get("payments") or []
    if isinstance(payments, list) and payments:
        return True

    payment_intent = attributes.get("payment_intent") or {}
    payment_intent_attributes = payment_intent.get("attributes") or {}
    payment_intent_status = (payment_intent_attributes.get("status") or "").lower()
    return payment_intent_status in {"paid", "succeeded"}


def _sync_successful_checkout_from_paymongo(transaction_obj):
    _payment_flow_print(
        "_sync_successful_checkout_from_paymongo",
        "sync_start",
        f"reference={transaction_obj.internal_reference_id} checkout_session_id={transaction_obj.paymongo_checkout_session_id or '-'}",
    )
    if transaction_obj.status == "paid":
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_skip",
            f"reference={transaction_obj.internal_reference_id} already paid",
        )
        return False

    if not transaction_obj.paymongo_checkout_session_id:
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_skip",
            f"reference={transaction_obj.internal_reference_id} missing checkout session id",
        )
        return False

    try:
        checkout_response = PayMongoClient().retrieve_checkout_session(transaction_obj.paymongo_checkout_session_id)
    except (PayMongoAPIError, ImproperlyConfigured) as exc:
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_failed",
            f"reference={transaction_obj.internal_reference_id} error={exc}",
        )
        return False

    paid = _checkout_session_response_is_paid(checkout_response)
    _payment_flow_print(
        "_sync_successful_checkout_from_paymongo",
        "sync_checkout_loaded",
        f"reference={transaction_obj.internal_reference_id} paid={paid}",
    )
    if not paid:
        return False

    transaction_obj.refresh_from_db()
    if transaction_obj.status == "paid":
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_skip",
            f"reference={transaction_obj.internal_reference_id} webhook already marked transaction paid",
        )
        return False

    checkout_session_id = checkout_response.get("data", {}).get("id") or transaction_obj.paymongo_checkout_session_id
    event_id = f"sync_{checkout_session_id}_{transaction_obj.internal_reference_id}"[:120]
    payload = {
        "data": {
            "id": event_id,
            "attributes": {
                "type": "checkout_session.payment.paid",
                "data": checkout_response.get("data", {}),
            },
        }
    }

    try:
        with db_transaction.atomic():
            webhook_event, created = PayMongoWebhookEvent.objects.get_or_create(
                paymongo_event_id=event_id,
                defaults={
                    "event_type": "checkout_session.payment.paid",
                    "signature_header": "synced via PayMongo API from success page",
                    "verified": True,
                    "processing_status": "received",
                    "raw_payload": payload,
                },
            )
    except OperationalError as exc:
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_db_locked",
            f"reference={transaction_obj.internal_reference_id} event_id={event_id} error={exc}",
        )
        return False

    if not created:
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_event_duplicate",
            f"event_id={event_id}",
        )
        return False

    _payment_flow_print(
        "_sync_successful_checkout_from_paymongo",
        "sync_event_created",
        f"event_id={event_id}",
    )

    try:
        _process_paymongo_event(webhook_event, payload, "checkout_session.payment.paid")
    except OperationalError as exc:
        _payment_flow_print(
            "_sync_successful_checkout_from_paymongo",
            "sync_processing_db_locked",
            f"event_id={event_id} error={exc}",
        )
        try:
            webhook_event.processing_status = "failed"
            webhook_event.error_message = f"Database locked during success-page sync: {exc}"
            webhook_event.processed_at = timezone.now()
            webhook_event.save(update_fields=["processing_status", "error_message", "processed_at", "updated_at"])
        except OperationalError:
            pass
        return False

    return True


@csrf_exempt
@require_POST
def paymongo_webhook(request):
    _payment_flow_print(
        "paymongo_webhook",
        "webhook_received",
        f"method={request.method} bytes={len(request.body or b'')}",
    )
    raw_body = request.body or b"{}"
    signature_header = request.META.get("HTTP_PAYMONGO_SIGNATURE", "")

    try:
        client = PayMongoClient()
        _payment_flow_print("paymongo_webhook", "signature_verify_start", "checking Paymongo-Signature header")
        client.verify_webhook_signature(raw_body, signature_header)
    except (PayMongoSignatureError, ImproperlyConfigured) as exc:
        _payment_flow_print("paymongo_webhook", "signature_verify_failed", str(exc))
        try:
            invalid_payload = json.loads(raw_body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            invalid_payload = {}
        event_id = f"invalid_{extract_event_id(invalid_payload)}"
        PayMongoWebhookEvent.objects.get_or_create(
            paymongo_event_id=event_id[:120],
            defaults={
                "event_type": extract_event_type(invalid_payload),
                "signature_header": signature_header,
                "verified": False,
                "processing_status": "invalid",
                "raw_payload": invalid_payload,
                "error_message": str(exc),
                "processed_at": timezone.now(),
            },
        )
        return JsonResponse({"ok": False, "error": "Invalid webhook signature."}, status=400)
    _payment_flow_print("paymongo_webhook", "signature_verify_ok", "signature accepted")

    try:
        _payment_flow_print("paymongo_webhook", "json_parse_start", "decoding webhook body")
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        _payment_flow_print("paymongo_webhook", "json_parse_failed", "invalid JSON body")
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    event_id = extract_event_id(payload)
    event_type = extract_event_type(payload)
    _payment_flow_print("paymongo_webhook", "event_extracted", f"event_id={event_id} event_type={event_type or '-'}")

    try:
        with db_transaction.atomic():
            _payment_flow_print("paymongo_webhook", "event_record_lookup", f"event_id={event_id}")
            webhook_event, created = PayMongoWebhookEvent.objects.get_or_create(
                paymongo_event_id=event_id,
                defaults={
                    "event_type": event_type,
                    "signature_header": signature_header,
                    "verified": True,
                    "processing_status": "received",
                    "raw_payload": payload,
                },
            )

            if not created:
                _payment_flow_print("paymongo_webhook", "duplicate_event", f"event_id={event_id}")
                return JsonResponse(
                    {
                        "ok": True,
                        "duplicate": True,
                        "event_id": event_id,
                        "event_type": webhook_event.event_type,
                    }
                )

            _payment_flow_print("paymongo_webhook", "event_record_created", f"event_id={event_id}")
    except IntegrityError:
        _payment_flow_print("paymongo_webhook", "duplicate_event_integrity", f"event_id={event_id}")
        return JsonResponse({"ok": True, "duplicate": True, "event_id": event_id})
    except OperationalError as exc:
        _payment_flow_print("paymongo_webhook", "event_record_db_locked", f"event_id={event_id} error={exc}")
        return JsonResponse({"ok": False, "error": "Database is busy. PayMongo can retry this webhook."}, status=503)
    except Exception as exc:
        _payment_flow_print("paymongo_webhook", "webhook_processing_failed", f"event_id={event_id} error={exc}")
        PayMongoWebhookEvent.objects.filter(paymongo_event_id=event_id).update(
            processing_status="failed",
            error_message=str(exc),
            processed_at=timezone.now(),
        )
        return JsonResponse({"ok": False, "error": "Webhook processing failed."}, status=500)

    try:
        _process_paymongo_event(webhook_event, payload, event_type)
    except OperationalError as exc:
        _payment_flow_print("paymongo_webhook", "webhook_processing_db_locked", f"event_id={event_id} error={exc}")
        PayMongoWebhookEvent.objects.filter(paymongo_event_id=event_id).update(
            processing_status="failed",
            error_message=f"Database locked during webhook processing: {exc}",
            processed_at=timezone.now(),
        )
        return JsonResponse({"ok": False, "error": "Database is busy. PayMongo can retry this webhook."}, status=503)
    except Exception as exc:
        _payment_flow_print("paymongo_webhook", "webhook_processing_failed", f"event_id={event_id} error={exc}")
        PayMongoWebhookEvent.objects.filter(paymongo_event_id=event_id).update(
            processing_status="failed",
            error_message=str(exc),
            processed_at=timezone.now(),
        )
        return JsonResponse({"ok": False, "error": "Webhook processing failed."}, status=500)

    _payment_flow_print("paymongo_webhook", "webhook_complete", f"event_id={event_id} event_type={event_type or '-'}")
    return JsonResponse({"ok": True, "event_id": event_id, "event_type": event_type})


def paymongo_return_page(request, internal_reference_id, outcome):
    _payment_flow_print(
        "paymongo_return_page",
        "return_page_received",
        f"reference={internal_reference_id} outcome={outcome}",
    )
    transaction_obj = get_object_or_404(Transaction, internal_reference_id=internal_reference_id)
    _payment_flow_print(
        "paymongo_return_page",
        "transaction_loaded",
        f"reference={transaction_obj.internal_reference_id} status={transaction_obj.status}",
    )

    if outcome == "success":
        try:
            synced = _sync_successful_checkout_from_paymongo(transaction_obj)
            if synced:
                transaction_obj.refresh_from_db()
                _payment_flow_print(
                    "paymongo_return_page",
                    "success_sync_complete",
                    f"reference={transaction_obj.internal_reference_id} status={transaction_obj.status}",
                )
        except OperationalError as exc:
            _payment_flow_print(
                "paymongo_return_page",
                "success_sync_db_locked",
                f"reference={transaction_obj.internal_reference_id} error={exc}",
            )

    if outcome == "cancel" and transaction_obj.status in {"pending", "checkout_created"}:
        transaction_obj.status = "cancelled"
        transaction_obj.save(update_fields=["status", "updated_at"])
        _payment_flow_print(
            "paymongo_return_page",
            "transaction_cancelled",
            f"reference={transaction_obj.internal_reference_id}",
        )

    external_url = _external_outcome_url(
        transaction_obj,
        "failed" if outcome == "failed" else outcome,
    )
    if outcome == "success" and external_url and transaction_obj.status == "paid":
        logged_in_user = _login_paymongo_success_user(request, transaction_obj)
        if logged_in_user is not None:
            _payment_flow_print(
                "paymongo_return_page",
                "redirect_success_url",
                f"reference={transaction_obj.internal_reference_id} user_id={logged_in_user.pk} url={external_url}",
            )
            return redirect(external_url)

    _payment_flow_print(
        "paymongo_return_page",
        "render_return_page",
        f"reference={transaction_obj.internal_reference_id} external_url={external_url or '-'}",
    )
    status_text = {
        "success": "Payment received by PayMongo. Access activates after webhook verification.",
        "cancel": "Payment checkout was cancelled.",
        "failed": "Payment failed.",
    }.get(outcome, "Payment status updated.")
    safe_outcome = escape(outcome.title())
    safe_status_text = escape(status_text)
    safe_reference = escape(transaction_obj.internal_reference_id)
    safe_status = escape(transaction_obj.get_status_display())
    safe_external_url = escape(external_url)
    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Payment {outcome}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f8fafc; color: #172033; }}
    main {{ max-width: 680px; margin: 12vh auto; padding: 32px; background: #fff; border: 1px solid #d8dee8; border-radius: 8px; }}
    h1 {{ margin-top: 0; font-size: 28px; }}
    code {{ background: #eef2f7; padding: 3px 5px; border-radius: 4px; }}
    a {{ color: #0f766e; font-weight: 700; }}
  </style>
</head>
<body>
  <main>
    <h1>Payment {safe_outcome}</h1>
    <p>{safe_status_text}</p>
    <p>Reference: <code>{safe_reference}</code></p>
    <p>Current status: <strong>{safe_status}</strong></p>
    {f'<p><a href="{safe_external_url}">Return to website</a></p>' if external_url else ''}
  </main>
</body>
</html>
"""
    return HttpResponse(html)


def paymongo_success(request, internal_reference_id):
    return paymongo_return_page(request, internal_reference_id, "success")


def paymongo_cancel(request, internal_reference_id):
    return paymongo_return_page(request, internal_reference_id, "cancel")


def paymongo_failed(request, internal_reference_id):
    return paymongo_return_page(request, internal_reference_id, "failed")


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

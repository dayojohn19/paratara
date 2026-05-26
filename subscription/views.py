from datetime import timedelta

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
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.db import IntegrityError, transaction as db_transaction
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from resorts.models import resortItem
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
        f'data-embed-token="{token}"></script>'
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


def _get_or_create_customer(source_website, *, email, name, phone):
    email = (email or "").strip().lower() or None
    name = (name or "").strip() or None
    phone = (phone or "").strip() or None

    if not email and not name and not phone:
        return None

    if email:
        customer = Customer.objects.filter(
            source_website=source_website,
            email__iexact=email,
        ).order_by("id").first()
        if customer:
            changed_fields = []
            if name and customer.name != name:
                customer.name = name
                changed_fields.append("name")
            if phone and customer.phone != phone:
                customer.phone = phone
                changed_fields.append("phone")
            if changed_fields:
                customer.save(update_fields=changed_fields)
            return customer

    return Customer.objects.create(
        source_website=source_website,
        email=email,
        name=name,
        phone=phone,
    )


@csrf_exempt
@require_POST
def start_paymongo_checkout(request, button_public_id):
    button = get_object_or_404(
        PaymentButton.objects.select_related("source_website", "product", "plan"),
        public_id=button_public_id,
        active=True,
        source_website__active=True,
        plan__status="active",
    )

    origin = request_origin(request)
    if not origin_is_allowed(button.source_website, origin):
        return _json_or_html_error(request, "Payment button origin is not allowed.", status=403)

    try:
        verify_embed_token(request.POST.get("embed_token"), button)
    except SuspiciousOperation as exc:
        return _json_or_html_error(request, str(exc), status=403)

    if button.checkout_mode == "paymongo_recurring" and not getattr(settings, "PAYMONGO_ENABLE_RECURRING", True):
        return _json_or_html_error(request, "PayMongo recurring billing is not enabled.", status=400)

    customer = _get_or_create_customer(
        button.source_website,
        email=request.POST.get("customer_email"),
        name=request.POST.get("customer_name"),
        phone=request.POST.get("customer_phone"),
    )

    try:
        amount_centavos = amount_to_centavos(button.plan.price)
    except ValueError as exc:
        return _json_or_html_error(request, str(exc), status=400)

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
    )

    metadata = build_checkout_metadata(
        source_website=button.source_website,
        product=button.product,
        plan=button.plan,
        customer_email=payment_transaction.customer_email,
        internal_reference_id=payment_transaction.internal_reference_id,
    )
    metadata.update(button.metadata or {})

    try:
        client = PayMongoClient()
        checkout_request, checkout_response = client.create_checkout_session(
            transaction=payment_transaction,
            line_item_name=button.plan.name,
            description=button.description or button.plan.description or button.product.description or button.plan.name,
            success_url=_return_url(request, payment_transaction, "success"),
            cancel_url=_return_url(request, payment_transaction, "cancel"),
            metadata=metadata,
        )
    except (PayMongoAPIError, ImproperlyConfigured) as exc:
        payment_transaction.status = "failed"
        payment_transaction.failure_reason = str(exc)
        payment_transaction.save(update_fields=["status", "failure_reason", "updated_at"])
        return _json_or_html_error(request, "Unable to create PayMongo checkout session.", status=502)

    checkout_url = checkout_url_from_response(checkout_response)
    checkout_session_id = checkout_session_id_from_response(checkout_response)
    if not checkout_url:
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

    return None, metadata, identifiers


def _status_for_paymongo_event(event_type, paymongo_status):
    event_type = event_type or ""
    paymongo_status = (paymongo_status or "").lower()

    if event_type in {"checkout_session.payment.paid", "payment.paid"} or paymongo_status in {"paid", "succeeded"}:
        return "paid"
    if event_type in {"payment.failed", "checkout_session.payment.failed"} or paymongo_status in {"failed"}:
        return "failed"
    if event_type in {"payment.refunded", "payment.refund.updated"}:
        return "refunded"
    if paymongo_status in {"cancelled", "canceled"}:
        return "cancelled"
    if paymongo_status == "expired":
        return "expired"
    return None


def _activate_subscription_for_transaction(transaction_obj, identifiers):
    now = timezone.now()
    current_subscription = None

    if transaction_obj.customer:
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

    if current_subscription and current_subscription.current_period_end and current_subscription.current_period_end > now:
        period_start = current_subscription.current_period_end
    else:
        period_start = now

    period_end = None
    if transaction_obj.plan.type == "subscription":
        period_end = Subscription.period_end_for_plan(transaction_obj.plan, period_start)

    if not current_subscription:
        current_subscription = Subscription.objects.create(
            customer=transaction_obj.customer,
            source_website=transaction_obj.source_website,
            plan=transaction_obj.plan,
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
    return current_subscription


def _process_paymongo_event(webhook_event, payload, event_type):
    transaction_obj, metadata, identifiers = _find_transaction_from_payload(payload)
    if not transaction_obj:
        webhook_event.processing_status = "processed"
        webhook_event.error_message = "No matching transaction found."
        webhook_event.processed_at = timezone.now()
        webhook_event.save(update_fields=["processing_status", "error_message", "processed_at", "updated_at"])
        return None

    new_status = _status_for_paymongo_event(event_type, identifiers.get("paymongo_status"))
    update_fields = ["raw_webhook_payload", "paymongo_status", "updated_at"]
    transaction_obj.raw_webhook_payload = payload
    transaction_obj.paymongo_status = identifiers.get("paymongo_status")

    identifier_field_map = {
        "paymongo_checkout_session_id": identifiers.get("checkout_session_id"),
        "paymongo_payment_id": identifiers.get("payment_id"),
        "paymongo_payment_intent_id": identifiers.get("payment_intent_id"),
        "paymongo_subscription_id": identifiers.get("subscription_id"),
    }
    for field_name, value in identifier_field_map.items():
        if value and getattr(transaction_obj, field_name) != value:
            setattr(transaction_obj, field_name, value)
            update_fields.append(field_name)

    if new_status and transaction_obj.status != new_status:
        transaction_obj.status = new_status
        update_fields.append("status")

    if new_status == "paid" and not transaction_obj.paid_at:
        transaction_obj.paid_at = timezone.now()
        update_fields.append("paid_at")

    transaction_obj.save(update_fields=list(dict.fromkeys(update_fields)))

    if new_status == "paid":
        _activate_subscription_for_transaction(transaction_obj, identifiers)
    elif new_status == "refunded":
        transaction_obj.activated_subscriptions.update(status="cancelled")

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
    return transaction_obj


@csrf_exempt
@require_POST
def paymongo_webhook(request):
    raw_body = request.body or b"{}"
    signature_header = request.META.get("HTTP_PAYMONGO_SIGNATURE", "")

    try:
        client = PayMongoClient()
        client.verify_webhook_signature(raw_body, signature_header)
    except (PayMongoSignatureError, ImproperlyConfigured) as exc:
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

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid JSON payload."}, status=400)

    event_id = extract_event_id(payload)
    event_type = extract_event_type(payload)

    try:
        with db_transaction.atomic():
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
                return JsonResponse(
                    {
                        "ok": True,
                        "duplicate": True,
                        "event_id": event_id,
                        "event_type": webhook_event.event_type,
                    }
                )

            _process_paymongo_event(webhook_event, payload, event_type)
    except IntegrityError:
        return JsonResponse({"ok": True, "duplicate": True, "event_id": event_id})
    except Exception as exc:
        PayMongoWebhookEvent.objects.filter(paymongo_event_id=event_id).update(
            processing_status="failed",
            error_message=str(exc),
            processed_at=timezone.now(),
        )
        return JsonResponse({"ok": False, "error": "Webhook processing failed."}, status=500)

    return JsonResponse({"ok": True, "event_id": event_id, "event_type": event_type})


def paymongo_return_page(request, internal_reference_id, outcome):
    transaction_obj = get_object_or_404(Transaction, internal_reference_id=internal_reference_id)

    if outcome == "cancel" and transaction_obj.status in {"pending", "checkout_created"}:
        transaction_obj.status = "cancelled"
        transaction_obj.save(update_fields=["status", "updated_at"])

    external_url = _external_outcome_url(
        transaction_obj,
        "failed" if outcome == "failed" else outcome,
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

from django.shortcuts import render

# Create your views here.
# subscriptions/views.py
import json
import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from resorts.models import resortItem
from .paypal import get_paypal_access_token
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


# RESTRICTED VIEW - DO NOT ADD ANY OTHER VIEWS HERE
# from django.shortcuts import redirect
# from subscriptions.models import PayPalSubscription

# def subscription_required(view):
#     def wrapper(request, *args, **kwargs):
#         if not PayPalSubscription.objects.filter(
#             user=request.user, status="ACTIVE"
            # user = request.resortItem
#         ).exists():
#             return redirect("/subscribe/")
#         return view(request, *args, **kwargs)
#     return wrapper
# @subscription_required
# def premium_view(request):
#     return render(request, "premium_content.html")    
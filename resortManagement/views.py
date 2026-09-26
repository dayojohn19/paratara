from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseServerError, HttpResponse, JsonResponse
from resorts.models import Packages, resortPackages,resortItem
from userProfile.models import UserCredentials
from userProfile.services import ensure_user_profile
from .forms import CheckinForm
from .models import Checkins, CheckinDay, ResortBookingPayment, ResortManager, ResortSubscription
import calendar
from django.db.models.functions import ExtractDay
from django.contrib.auth.decorators import login_required
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace
# Create your views here.
# resort_id room_id room_month room_year 'previous'
from django.utils import timezone
import requests
from requests.auth import HTTPBasicAuth
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import Q
from django.db import transaction as db_transaction
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import base64
import json
import os
import re
import qrcode
from io import BytesIO
from django.forms.models import model_to_dict
from django.utils.dateparse import parse_datetime
from django.urls import reverse
from subscription.services.paymongo import PayMongoClient, amount_to_centavos


PAYPAL_API_BASE = getattr(settings, 'PAYPAL_API_BASE', 'https://api-m.paypal.com')
PAYPAL_SUBSCRIPTION_PLAN_ID = os.getenv(
    'PAYPAL_SUBSCRIPTION_PLAN_ID',
    getattr(settings, 'PAYPAL_SUBSCRIPTION_PLAN_ID', ''),
)
PAYPAL_SUBSCRIPTION_RETURN_URL = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_RETURN_URL',
    os.getenv('PAYPAL_SUBSCRIPTION_RETURN_URL', 'https://www.paratara.com/resortManagement/subscription/'),
)
PAYPAL_SUBSCRIPTION_CANCEL_URL = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_CANCEL_URL',
    os.getenv('PAYPAL_SUBSCRIPTION_CANCEL_URL', 'https://www.paratara.com/resortManagement/subscription/?cancel=1'),
)
PAYPAL_SUBSCRIPTION_BRAND = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_BRAND_NAME',
    os.getenv('PAYPAL_SUBSCRIPTION_BRAND_NAME', 'Paratara Resort'),
)


def expire_stale_resort_booking_payments():
    return ResortBookingPayment.expire_stale_pending()


def _booking_receipt_redirect(checkin_instance):
    encoded_booking = _booking_receipt_code(checkin_instance)
    return redirect('resort_management:qr', qr_strings=encoded_booking)


def _booking_receipt_code(checkin_instance):
    checkin_data = model_to_dict(checkin_instance)
    resort_details = checkin_instance.resort
    room_details = checkin_instance.room
    checkin_data.update({
        'resort_name_display': (resort_details.RealName or resort_details.name or '') if resort_details else '',
        'resort_address': resort_details.address if resort_details else '',
        'resort_logo': next(
            (
                value
                for value in (
                    resort_details.headerImage,
                    resort_details.virtualpicture,
                    resort_details.resortQRLink,
                )
                if value
            ),
            '',
        ) if resort_details else '',
        'package_name_display': room_details.title if room_details else '',
        'checkin_date_readable': checkin_instance.checkin_date.strftime('%B %d, %Y'),
        'checkout_date_readable': checkin_instance.checkout_date.strftime('%B %d, %Y'),
    })
    encoded_booking = base64.urlsafe_b64encode(
        json.dumps(checkin_data, default=datetime_converter).encode()
    ).decode()
    return encoded_booking


def _send_booking_receipt_email(payment, checkin_instance, request):
    payment.refresh_from_db(fields=['receipt_email_sent_at'])
    if payment.receipt_email_sent_at or not checkin_instance.guest_email:
        return False

    receipt_code = _booking_receipt_code(checkin_instance)
    receipt_url = request.build_absolute_uri(
        reverse('resort_management:qr', args=[receipt_code])
    )
    qr_buffer = BytesIO()
    qrcode.make(receipt_url).save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    resort_name = checkin_instance.resort.RealName or checkin_instance.resort.name
    subject = f'Booking receipt: {checkin_instance.room.title}'
    body = (
        f"Hello {checkin_instance.guest_name},\n\n"
        "Your payment and booking are confirmed.\n\n"
        f"Resort: {resort_name}\n"
        f"Room: {checkin_instance.room.title}\n"
        f"Check-in: {checkin_instance.checkin_date:%B %d, %Y %I:%M %p}\n"
        f"Check-out: {checkin_instance.checkout_date:%B %d, %Y %I:%M %p}\n"
        f"Amount paid: PHP {payment.amount_centavos / 100:,.2f}\n\n"
        f"Open your booking receipt: {receipt_url}\n\n"
        "Your QR booking receipt is attached to this email."
    )
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[checkin_instance.guest_email],
    )
    message.attach('booking-receipt-qr.png', qr_buffer.getvalue(), 'image/png')
    try:
        if message.send(fail_silently=False):
            payment.receipt_email_sent_at = timezone.now()
            payment.save(update_fields=['receipt_email_sent_at', 'updated_at'])
            return True
    except Exception as exc:
        print(
            f'[resortManagement] Booking receipt email failed for payment {payment.pk}: {exc}',
            flush=True,
        )
    return False


def has_active_subscription(resort_id):
    is_subscribed = ResortSubscription.objects.filter(
        resort=resort_id,
        status="ACTIVE"
    ).exists()
    print('Is Subscribed:', is_subscribed)
    return is_subscribed


def _parse_iso_date(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    return parsed.date() if parsed else None


def _resort_id_from_custom_id(custom_id):
    if not custom_id:
        return None
    match = re.search(r'resort-(\d+)', custom_id)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _resort_from_custom_id(custom_id):
    resort_id = _resort_id_from_custom_id(custom_id)
    if not resort_id:
        return None
    return resortItem.objects.filter(id=resort_id).first()

def _handle_paypal_subscription_event(event_type, resource, payload):
    if not event_type or not resource:
        return False

    subscription_id = next(
        (
            resource.get('id'),
            resource.get('subscription_id'),
            resource.get('billing_agreement_id'),
        ),
        None,
    )
    if not subscription_id:
        return False

    subscription = ResortSubscription.objects.filter(paypal_subscription_id=subscription_id).first()
    event_status_map = {
        'BILLING.SUBSCRIPTION.ACTIVATED': ResortSubscription.StatusChoices.ACTIVE,
        'BILLING.SUBSCRIPTION.CANCELLED': ResortSubscription.StatusChoices.CANCELLED,
        'BILLING.SUBSCRIPTION.SUSPENDED': ResortSubscription.StatusChoices.PAUSED,
        'BILLING.SUBSCRIPTION.EXPIRED': ResortSubscription.StatusChoices.EXPIRED,
    }

    billing_info = (resource.get('billing_info') or {})
    last_payment = billing_info.get('last_payment') or {}
    last_payment_id = last_payment.get('id')
    start_date = _parse_iso_date(resource.get('start_time') or payload.get('create_time'))
    next_billing_time = _parse_iso_date(billing_info.get('next_billing_time'))
    fallback_start = start_date or timezone.now().date()
    fallback_end = next_billing_time or (fallback_start + timedelta(days=30))
    custom_id = resource.get('custom_id') or payload.get('custom_id')

    created = False
    if not subscription:
        target_resort = _resort_from_custom_id(custom_id)
        if not target_resort:
            return False
        subscription = ResortSubscription.objects.create(
            resort=target_resort,
            paypal_subscription_id=subscription_id,
            manager=None,
            start_date=fallback_start,
            end_date=fallback_end,
            status=event_status_map.get(event_type, ResortSubscription.StatusChoices.PENDING) or ResortSubscription.StatusChoices.PENDING,
            auto_renew=event_type == 'BILLING.SUBSCRIPTION.ACTIVATED',
            last_payment_reference=last_payment_id or '',
            notes=f'PayPal webhook {event_type}',
        )
        created = True

    updated = created
    new_status = event_status_map.get(event_type)
    if new_status and subscription.status != new_status:
        subscription.status = new_status
        updated = True

    if event_type == 'BILLING.SUBSCRIPTION.ACTIVATED' and not subscription.auto_renew:
        subscription.auto_renew = True
        updated = True
    elif event_type in {'BILLING.SUBSCRIPTION.CANCELLED', 'BILLING.SUBSCRIPTION.SUSPENDED', 'BILLING.SUBSCRIPTION.EXPIRED'} and subscription.auto_renew:
        subscription.auto_renew = False
        updated = True

    start_date = _parse_iso_date(resource.get('start_time') or payload.get('create_time'))
    if start_date and subscription.start_date != start_date:
        subscription.start_date = start_date
        updated = True

    event_date = _parse_iso_date(payload.get('event_time') or payload.get('create_time') or resource.get('update_time'))
    if event_date and event_type in {'BILLING.SUBSCRIPTION.CANCELLED', 'BILLING.SUBSCRIPTION.SUSPENDED', 'BILLING.SUBSCRIPTION.EXPIRED'}:
        if subscription.end_date != event_date:
            subscription.end_date = event_date
            updated = True

    if last_payment_id and subscription.last_payment_reference != last_payment_id:
        subscription.last_payment_reference = last_payment_id
        updated = True

    if updated:
        subscription.save()
    return updated

@csrf_exempt
def paypal_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid payload'}, status=400)

    event_type = payload.get('event_type')
    resource = payload.get('resource', {})

    allowed_events = settings.PAYPAL_WEBHOOK_EVENTS
    if allowed_events and allowed_events.lower() != 'all events':
        normalized = {event.strip() for event in allowed_events.split(',') if event.strip()}
        if normalized and event_type not in normalized:
            return JsonResponse({
                'status': 'skipped',
                'reason': 'untracked event',
                'subscription_updated': False,
            })

    subscription_updated = _handle_paypal_subscription_event(event_type, resource, payload)

    # TODO: add verification (verify-webhook-signature) when credentials are available
    return JsonResponse({'status': 'ok', 'subscription_updated': subscription_updated})

def _is_resort_manager(user, resort: resortItem) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    try:
        return resort.adminManager.filter(pk=user.pk).exists()
    except Exception:
        return False


def _latest_subscription(resort):
    return ResortSubscription.objects.filter(resort=resort).order_by('-end_date').first()


def _paypal_access_token():
    if not settings.PAYPAL_WEBHOOK_CLIENT or not settings.PAYPAL_WEBHOOK_SECRET:
        raise ValueError("PayPal client credentials not configured.")
    response = requests.post(
        f"{PAYPAL_API_BASE}/v1/oauth2/token",
        auth=HTTPBasicAuth(settings.PAYPAL_WEBHOOK_CLIENT, settings.PAYPAL_WEBHOOK_SECRET),
        data={'grant_type': 'client_credentials'},
        headers={'Accept': 'application/json'},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get('access_token')


def _create_paypal_subscription(resort, user, notes='', token=None):
    if not PAYPAL_SUBSCRIPTION_PLAN_ID:
        raise ValueError('PayPal subscription plan ID is not configured.')
    payload = {
        'plan_id': PAYPAL_SUBSCRIPTION_PLAN_ID,
        'subscriber': {
            'name': {
                'given_name': user.first_name or 'Manager',
                'surname': user.last_name or 'Resort',
            },
            'email_address': user.email or settings.DEFAULT_FROM_EMAIL,
        },
        'application_context': {
            'brand_name': PAYPAL_SUBSCRIPTION_BRAND,
            'locale': 'en-US',
            'shipping_preference': 'NO_SHIPPING',
            'user_action': 'SUBSCRIBE_NOW',
            'landing_page': 'billing',
            'show_pay_with_paypal': True,
            'return_url': f"{PAYPAL_SUBSCRIPTION_RETURN_URL}?resort_id={resort.id}",
            'cancel_url': f"{PAYPAL_SUBSCRIPTION_CANCEL_URL}?resort_id={resort.id}",
        },
        'notes': notes,
        'custom_id': f"resort-{resort.id}",
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token or _paypal_access_token()}',
    }
    response = requests.post(
        f"{PAYPAL_API_BASE}/v1/billing/subscriptions",
        json=payload,
        headers=headers,
        timeout=10,
    )
    if response.status_code not in {201, 200}:
        raise ValueError(f"PayPal subscription creation failed: {response.text}")
    data = response.json()
    approve_link = next((link['href'] for link in data.get('links', []) if link.get('rel') == 'approve'), None)
    if not approve_link:
        raise ValueError('PayPal response is missing approval link.')
    return {'approve_url': approve_link, 'id': data.get('id')}


@login_required
def subscription_detail(request, resort_id):
    resort = get_object_or_404(resortItem, id=resort_id)
    if not _is_resort_manager(request.user, resort):
        raise PermissionDenied("You are not allowed to access this subscription page.")

    subscription = _latest_subscription(resort)
    # contact_email = subscription.resort_contactEmail if subscription else None
    return render(request, 'resortManagement/subscription.html', {
        'subscription': subscription,
        'resort': resort,
        'subscription_status_url': reverse('resort_management:subscription_status', args=[resort_id]),
        'subscription_subscribe_url': reverse('resort_management:subscription_subscribe', args=[resort_id]),
        'subscription_contact_email': getattr(settings, 'PAYPAL_SUBSCRIPTION_SUPPORT_EMAIL', 'support@paratara.com'),
        # 'subscription_contact_email': contact_email or 'support@paratara.com',
        'resort_display_name': resort.RealName or resort.name or 'this resort',
    })


@login_required
def subscription_status(request, resort_id):
    resort = get_object_or_404(resortItem, id=resort_id)
    if not _is_resort_manager(request.user, resort):
        raise PermissionDenied("You are not allowed to check this subscription status.")

    subscription = _latest_subscription(resort)
    if not subscription:
        return JsonResponse({'status': 'none', 'message': 'No subscription record found.'}, status=404)

    data = {
        'status': subscription.status,
        'status_label': subscription.get_status_display(),
        'is_active': subscription.is_active,
        'remaining_days': subscription.remaining_days,
        'manager_name': str(subscription.manager) if subscription.manager else None,
        'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
        'end_date': subscription.end_date.isoformat() if subscription.end_date else None,
        'last_payment_reference': subscription.last_payment_reference,
        'notes': subscription.notes,
    }
    return JsonResponse(data)


@require_POST
@login_required
def subscription_subscribe(request, resort_id):
    resort = get_object_or_404(resortItem, id=resort_id)
    if not _is_resort_manager(request.user, resort):
        raise PermissionDenied("You are not allowed to request a subscription for this resort.")

    subscription = _latest_subscription(resort)
    if subscription and subscription.is_active:
        return JsonResponse({
            'status': 'already_active',
            'message': 'An active subscription already exists.',
        }, status=409)

    try:
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        payload = {}
    notes = payload.get('notes', 'Subscription requested from dashboard.')
    try:
        paypal_result = _create_paypal_subscription(resort, request.user, notes=notes)
    except (ValueError, requests.RequestException) as exc:
        return JsonResponse({'message': str(exc)}, status=502)

    return JsonResponse({
        'status': 'pending',
        'status_label': 'Awaiting PayPal approval',
        'approve_url': paypal_result['approve_url'],
        'paypal_subscription_id': paypal_result.get('id'),
        'notes': notes,
    })

def generate_calendar(request,target_model):
    def get_mark_dates(model_date_target):
        marked_dates = {}  # {date: 'checkin'/'checkout'/'stay'}
        # check_lists = Checkins.objects.filter(room=room_target)
        check_lists = Checkins.objects.filter(room=model_date_target).order_by('-checked_in')
        check_lists_checked = Checkins.objects.filter(room=model_date_target, checked_in=True )
        for checkin in check_lists_checked:
            start = checkin.checkin_date.date()
            end = checkin.checkout_date.date()
            current = start
            while current <= end:
                if current == start:
                    marked_dates[current] = 'checkin'
                elif current == end:
                    marked_dates[current] = 'checkout'
                else:
                    marked_dates[current] = 'stay'
                current += timedelta(days=1)        
        return marked_dates
                
    cal = calendar.Calendar(firstweekday=6)
    now = datetime.now()
    month = now.month
    year = now.year
    month_days = cal.itermonthdates(year, month)
    days = []
    marked_dates = get_mark_dates(target_model)
    for day in month_days:
        days.append({
            'date': day,
            'in_month': day.month == month,
            'status': marked_dates.get(day),  # None if not booked
        })

    weeks = [days[i:i+7] for i in range(0, len(days), 7)]
    context = {
        'month_name': calendar.month_name[month],
        'month': calendar.month_name[month],
        'weeks':weeks,
        'resort_id' : 1,
        'room_id' : 1,
        # Add these 
        # 'room_month' : 1,
        # 'room_item'
        # 'resortItem'
        # "rooms": roomItem, 
        # 'form': CheckinForm()
        'year' : year,
        'room_year' : 2025,
        'day' :day,
    }
    return context

def viewGuestlists(request, resort_id):
    # try:
    whatresort = resortItem.objects.get(pk=resort_id)
    if _is_resort_manager(request.user, whatresort):

        guestlists = Checkins.objects.filter(resort__pk=resort_id).order_by('-checkin_date')
        context = {
            'resort_id':resort_id,
            'guestlists':guestlists,
            
            'resortObject':whatresort,
            'resortID':whatresort.id,
            'resortName':whatresort.name,
            'resortRealName':whatresort.RealName

        }
        return render(request, 'resortManagement/guestlists.html', context)
    # except Exception as e:
    # print('Error: ',e)
    raise PermissionDenied("You are not allowed to access this page.")
def put_checkin_id(request):
    "Put ID on Check in"
    from userProfile.cloudinary_uploader import uploadtoCloudinary
    checkin_id = request.POST.get('checkin_id')
    checkobj = Checkins.objects.get(id=checkin_id)
    # Prefer uploaded file, fall back to POSTed URL
    file_obj = request.FILES.get('image')
    if file_obj:
        raw_name = getattr(file_obj, 'name', 'checkin')
        safe_filename = "".join(c for c in raw_name if c.isalnum() or c in "._-").rstrip()
        public_id = f"checkin_{checkin_id}_{safe_filename}"
        try:
            uploaded_url = uploadtoCloudinary(request, file_obj, public_id)
            checkobj.id_picture = uploaded_url
            checkobj.save()
            return checkobj.id_picture
        except Exception as e:
            print(f"Cloudinary upload failed: {e}")
    # Fallback: try to use Upload_and_get_URL if no file or upload failed
    try:
        from imageapp.imageuploader import Upload_and_get_URL
        url = Upload_and_get_URL(request)
        checkobj.id_picture = url
        checkobj.save()
        return checkobj.id_picture
    except Exception:
        return None

def upload_image_ajax(request):
    from userProfile.cloudinary_uploader import uploadtoCloudinary
    # Support AJAX file upload under key 'image'
    file_obj = request.FILES.get('image')
    if not file_obj:
        return JsonResponse({"success": False, "error": "No file uploaded"}, status=400)
    raw_name = getattr(file_obj, 'name', 'upload')
    safe_filename = "".join(c for c in raw_name if c.isalnum() or c in "._-").rstrip()
    # Use timestamp to avoid collisions
    import time
    public_id = f"upload_{int(time.time())}_{safe_filename}"
    try:
        uploaded_url = uploadtoCloudinary(request, file_obj, public_id)
        return JsonResponse({
            "success": True,
            "url": uploaded_url
        })
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    # if request.method == "POST" and request.FILES.get("image"):
    #     # form = ImageForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         uploaded = form.save()
    #         return JsonResponse({
    #             "success": True,
    #             "url": uploaded.image.url  # assuming model has `image` field
    #         })
    #     return JsonResponse({"success": False, "errors": form.errors}, status=400)
    # return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

# Upload_and_get_URL(request) with files
# return [url_to_use, url_to_backup]


def get_client_ip(request):
    # First, check for X-Forwarded-For (if behind a proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list of IPs
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Fallback to REMOTE_ADDR
        ip = request.META.get('REMOTE_ADDR')
    return ip


def my_view(request):
    # 1. Get client IP
    client_ip = get_client_ip(request)
    print("Client IP:", client_ip)

    # 2. Lookup timezone from IP
    try:
        response = requests.get(f'https://ipapi.co/{client_ip}/json/').json()
        user_timezone = response.get('timezone')  # e.g., 'Asia/Manila'
        print('Current Timezone: ',user_timezone)
    except Exception:
        user_timezone = 'UTC'  # fallback

    print("Detected timezone:", user_timezone)

    # 3. Activate timezone for this request
    if user_timezone:
        timezone.activate(user_timezone)
    else:
        timezone.activate('UTC')

    # 4. Example: current time in user's timezone
    local_time = timezone.localtime(timezone.now())
    print("Local time:", local_time)
    import time
    time.sleep(5)
    # Continue your view logic
    return 




def marked_calendar(request, resort_id=1, room_id=1, month=None, year=1, whatstep=1):
    expire_stale_resort_booking_payments()
    checklist = []   
    isManager = False
    if month is None:
        now = datetime.now()
        month = now.month
        year = now.year
    if year <= 1:
        now = datetime.now()
        month = now.month
        year = now.year
    whatresort = resortItem.objects.get(id=resort_id)
    isManager = _is_resort_manager(request.user, whatresort)


# Get target room
    room_target = Packages.objects.get(id=room_id)
    if request.method == 'POST':
        if whatstep == 'next':
            month += 1
        elif whatstep == 'previous':
            month -= 1
        elif whatstep == 'checkout':
            checkid = request.POST.get('checked_id')
            checkitem = Checkins.objects.get(id=checkid)
            checkitem.checked_in = False
            checkitem.save()
            print('Checked Out')
        elif whatstep == 'request':
            checkid = request.POST.get('checked_id')
            new_request = request.POST.get('special_requests')
            checkitem = Checkins.objects.get(id=checkid)
            checkitem.special_requests = new_request
            checkitem.save()            
        elif whatstep == 'id_picture':
            try:
                put_checkin_id(request)
            except:
                print('No ID PICTURE')
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1

    # Calendar grid range (includes leading/trailing days outside the month)
    cal = calendar.Calendar(firstweekday=6)
    month_days = list(cal.itermonthdates(year, month))
    first_visible_day = month_days[0]
    last_visible_day = month_days[-1]

    # Build marked_dates with statuses
    marked_dates = {}  # {date: 'checkin'/'checkout'/'stay'}
    check_lists = Checkins.objects.filter(room=room_target).order_by('-checked_in')

    # Mark ANY booking that overlaps the visible calendar grid.
    # This keeps availability coloring correct even if `checked_in` was toggled.
    overlapping_bookings = (
        Checkins.objects.filter(
            room=room_target,
            checkin_date__date__lte=last_visible_day,
            checkout_date__date__gte=first_visible_day,
        )
        .order_by('checkin_date')
    )

    for checkin in overlapping_bookings:
        start = max(checkin.checkin_date.date(), first_visible_day)
        end = min(checkin.checkout_date.date(), last_visible_day)
        current = start
        while current <= end:
            if current == checkin.checkin_date.date():
                marked_dates[current] = 'checkin'
            elif current == checkin.checkout_date.date():
                marked_dates[current] = 'checkout'
            else:
                marked_dates[current] = 'stay'
            current += timedelta(days=1)

    days = []
    for day in month_days:
        days.append({
            'date': day,
            'in_month': day.month == month,
            'status': marked_dates.get(day),  # None if not booked
        })

    weeks = [days[i:i+7] for i in range(0, len(days), 7)]
    print('Weeks: ', weeks)

    context = {
        'form':CheckinForm(
            initial={
            'room': room_target,
            'resort': room_target.packageName.ItemOfResort,
            'guest_name': '',
            'guest_email': '',
            'guest_phone': '',
            'special_requests': '',
                }
            ),
        'isManager':isManager,
        'check_list': check_lists,
        'weeks': weeks,
        'month' : month,
        'year' : year,
        'room_id': room_id,
        'month_name': calendar.month_name[month],
        'room_item':room_target,

        'resortObject':whatresort,
        'resortID': whatresort.id,
        'resortName': whatresort.name,
        'resortRealName': whatresort.RealName,   

        # For templates that check for a dedicated manager flag
        'managerUser': 'managerUser' if isManager else '',
        
        "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        
         
        
    }
    # messages.success(request, "✅ MovedPayment completed and booking saved successfully!")
    print('Context: ')
    return render(request, 'resortManagement/calendar.html', context)    


 

# # 


def datetime_converter(o):
    from datetime import datetime
    if isinstance(o, datetime):
        return o.isoformat()
# @login_required


def room_checkin(request):
    print('Room Checkin')
    
    if request.method == 'POST':
        my_view(request)
        form = CheckinForm(request.POST)
        if form.is_valid():
            checkin_instance = form.save(commit=False)
            request.session['form_submitted'] = True
            # Ensure the difference is at least 1 day
            checkin_date = checkin_instance.checkin_date.date()
            checkout_date = checkin_instance.checkout_date.date()
            delta = checkout_date - checkin_date 
            print('\n\n Time Delta: ',delta.days)
            if delta.days >= 0:
                # form.save()
                try:
                    checkin_instance.id_picture = request.POST.get('checkin_id_url')
                    print('Added check in id')
                except:
                    print('cant add checkin id')
                checkin_instance.save()
                try:
                    user = ensure_user_profile(request.user)
                    manager = ResortManager.objects.get_or_create(profile=user)[0]
                    checkin_instance.checked_in_by = manager                
                    manager.checked_visitor.add(checkin_instance)
                    manager.save()
                except:
                    print('Self Checkin')
                # Save each day in the range
                # if CheckinDay.objects.filter(checkin=checkin_instance.room, checkinday=checkin_instance.checkin_date) > 0:
                #     return 'Sory double check in'
                # if CheckinDay.objects.filter(checkin=checkin_instance.room, day=checkin_instance.checkin_date and checkoutday != checkin_instance.checkin_date)
                # if CheckinDay.objects.filter( Q(checkin=checkin_instance.room) & Q(day=checkin_instance.checkin_date) & ~Q(checkoutday=checkin_instance.checkin_date))                
                exists = CheckinDay.objects.filter( Q(checkin=checkin_instance.room) & Q(day=checkin_instance.checkin_date) & Q(checkoutday=checkin_instance.checkin_date)).exists()                
                if exists:
                    print('\n\n\nSorry existing date: \n\n')
                    return 'Sorry Checkin exist'

                for i in range(delta.days + 1): 
                    day = checkin_date + timedelta(days=i)
                    CheckinDay.objects.create(checkin=checkin_instance.room, day=day, checkinday = checkin_instance.checkin_date, checkoutday = checkin_instance.checkout_date )
                # Redirect or render success

                # return redirect('some-success-page')
                # Making CheckinObject string URL
                checkin_dict = model_to_dict(checkin_instance)
                resort_details = checkin_instance.resort
                room_details = checkin_instance.room
                resort_name_display = ''
                resort_address = ''
                resort_logo = ''
                if resort_details:
                    resort_name_display = resort_details.RealName or resort_details.name or ''
                    resort_address = resort_details.address or ''
                    resort_logo = next(
                        (
                            value
                            for value in (
                                resort_details.headerImage,
                                resort_details.virtualpicture,
                                resort_details.resortQRLink,
                            )
                            if value
                        ),
                        '',
                    )
                package_name_display = room_details.title if room_details else ''
                checkin_dict.update({
                    'resort_name_display': resort_name_display,
                    'resort_address': resort_address,
                    'resort_logo': resort_logo,
                    'package_name_display': package_name_display,
                    'checkin_date_readable': checkin_instance.checkin_date.strftime('%B %d, %Y'),
                    'checkout_date_readable': checkin_instance.checkout_date.strftime('%B %d, %Y'),
                })
                
                json_str = json.dumps(checkin_dict, default=datetime_converter)
                # json_str = json.dumps(checkin_dict)
                strurl = base64.urlsafe_b64encode(json_str.encode()).decode()

                messages.success(request, "✅ Payment completed and booking saved successfully!")
                messages.success(request,  f'✅ Payment completed! <a href="/resortManagement/qr/{strurl}">Download Booking</a>')
                form = CheckinForm()
            else:
                print('Put atleast 1 day')
                form.add_error(None, "Check-in duration must be at least 1 day.")
                

        return redirect('resort_management:movemarkedcalendarnamed', resort_id=checkin_instance.resort.id, room_id=checkin_instance.room.id, month=checkin_instance.checkin_date.month, year=checkin_instance.checkin_date.year , whatstep='id_picture')
        # return room_availability(request, resort_id=2, room_id=checkin_instance.room.id, month=checkin_instance.checkin_date.month, year=checkin_instance.checkin_date.year)
        # return redirect('resort_management:room_availability', room_id=checkin_instance.room.id, room_month=checkin_instance.checkin_date.month, room_year=checkin_instance.checkin_date.year)
    if request.method == 'GET':
        # Render the check-in form
        return render(request, 'resortManagement/room_availability.html')
    if request.method == 'PUT':
        # Handle the PUT request (if needed)
        return HttpResponseServerError('Cant view Room Availability')
    else:
        return HttpResponseServerError('Cant view Room Availability')

@require_POST
def start_paymongo_room_booking(request):
    expire_stale_resort_booking_payments()
    form = CheckinForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Please complete the booking details and dates.'}, status=400)

    booking = form.save(commit=False)
    room = booking.room
    resort = booking.resort
    if not room or not resort or room.packageName.ItemOfResort_id != resort.pk:
        return JsonResponse({'error': 'The selected room does not belong to this resort.'}, status=400)

    nights = (booking.checkout_date.date() - booking.checkin_date.date()).days
    if nights < 1:
        return JsonResponse({'error': 'Select at least one night.'}, status=400)

    booking_data = {
        'room': room.pk,
        'resort': resort.pk,
        'guest_name': booking.guest_name,
        'guest_email': booking.guest_email,
        'guest_phone': booking.guest_phone,
        'special_requests': booking.special_requests,
        'checkin_date': booking.checkin_date.isoformat(),
        'checkout_date': booking.checkout_date.isoformat(),
    }

    overlaps = Checkins.objects.filter(
        room=room,
        checkin_date__date__lt=booking.checkout_date.date(),
        checkout_date__date__gt=booking.checkin_date.date(),
    ).exists()
    if overlaps:
        return JsonResponse({'error': 'Those dates are no longer available.'}, status=409)

    pending_cutoff = timezone.now() - timedelta(minutes=30)
    for pending in ResortBookingPayment.objects.filter(
        status='pending',
        created_at__gte=pending_cutoff,
    ).only('booking_data', 'checkout_session_id'):
        data = pending.booking_data
        if str(data.get('room')) != str(room.pk):
            continue
        pending_start = parse_datetime(data.get('checkin_date', ''))
        pending_end = parse_datetime(data.get('checkout_date', ''))
        if (
            pending_start and pending_end
            and pending_start.date() < booking.checkout_date.date()
            and pending_end.date() > booking.checkin_date.date()
        ):
            if data != booking_data:
                return JsonResponse(
                    {'error': 'Those dates already have a pending checkout. Complete or cancel that checkout first.'},
                    status=409,
                )
            if not pending.checkout_session_id:
                pending.status = 'failed'
                pending.failure_reason = 'Pending checkout had no PayMongo session id.'
                pending.save(update_fields=['status', 'failure_reason', 'updated_at'])
                continue
            try:
                existing_session = PayMongoClient().retrieve_checkout_session(pending.checkout_session_id)
            except Exception:
                return JsonResponse(
                    {'error': 'Could not resume the existing PayMongo checkout. Please try again shortly.'},
                    status=502,
                )
            existing_data = existing_session.get('data') or {}
            existing_attributes = existing_data.get('attributes') or {}
            existing_status = str(existing_attributes.get('status') or '').lower()
            existing_url = existing_attributes.get('checkout_url')
            if existing_data.get('id') == pending.checkout_session_id and existing_url and existing_status not in {
                'expired', 'cancelled', 'canceled'
            }:
                return JsonResponse({'checkout_url': existing_url, 'resumed': True})
            if existing_status in {'expired', 'cancelled', 'canceled'}:
                pending.status = 'cancelled'
                pending.failure_reason = f'PayMongo checkout {existing_status}.'
                pending.save(update_fields=['status', 'failure_reason', 'updated_at'])
                continue
            return JsonResponse(
                {'error': 'The existing checkout is unavailable. Please contact the resort before retrying.'},
                status=409,
            )

    total = (Decimal(str(room.price)) * nights * Decimal('1.053')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    try:
        amount_centavos = amount_to_centavos(total)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    payment = ResortBookingPayment.objects.create(
        amount_centavos=amount_centavos,
        currency='PHP',
        booking_data=booking_data,
    )
    return_path = reverse('resort_management:paymongo_booking_return', args=[payment.pk])
    return_url = request.build_absolute_uri(return_path)
    checkout_transaction = SimpleNamespace(
        internal_reference_id=f'room-{payment.pk.hex[:24]}',
        amount_centavos=amount_centavos,
        currency='PHP',
        customer=None,
    )

    try:
        _, response = PayMongoClient().create_checkout_session(
            transaction=checkout_transaction,
            line_item_name=f'{room.title} booking',
            description=f'{nights} night booking at {resort.RealName or resort.name}',
            success_url=return_url,
            cancel_url=f'{return_url}?cancel=1',
            metadata={
                'resort_booking_payment_id': str(payment.pk),
                'resort_id': str(resort.pk),
                'room_id': str(room.pk),
            },
        )
    except Exception as exc:
        payment.status = 'failed'
        payment.failure_reason = str(exc)[:1000]
        payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
        return JsonResponse({'error': 'Could not start PayMongo checkout. Please try again.'}, status=502)

    checkout_data = response.get('data') or {}
    checkout_url = (checkout_data.get('attributes') or {}).get('checkout_url')
    checkout_session_id = checkout_data.get('id')
    if not checkout_url or not checkout_session_id:
        payment.status = 'failed'
        payment.failure_reason = 'PayMongo did not return a checkout URL and session id.'
        payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
        return JsonResponse({'error': 'PayMongo did not return a valid checkout session.'}, status=502)

    payment.checkout_session_id = checkout_session_id
    payment.save(update_fields=['checkout_session_id', 'updated_at'])
    return JsonResponse({'checkout_url': checkout_url})


def paymongo_room_booking_return(request, payment_id):
    payment = get_object_or_404(ResortBookingPayment, pk=payment_id)
    booking_data = payment.booking_data
    checkin_date = parse_datetime(booking_data['checkin_date'])
    redirect_args = {
        'resort_id': booking_data['resort'],
        'room_id': booking_data['room'],
        'month': checkin_date.month,
        'year': checkin_date.year,
        'whatstep': 'id_picture',
    }
    calendar_url = 'resort_management:movemarkedcalendarnamed'

    if payment.status == 'paid' and payment.checkin_id:
        _send_booking_receipt_email(payment, payment.checkin, request)
        return _booking_receipt_redirect(payment.checkin)
    if request.GET.get('cancel') == '1':
        if payment.status == 'pending':
            payment.status = 'cancelled'
            payment.save(update_fields=['status', 'updated_at'])
        messages.warning(request, 'PayMongo checkout was cancelled; no booking was created.')
        return redirect(calendar_url, **redirect_args)
    if not payment.checkout_session_id:
        messages.error(request, 'The PayMongo checkout session could not be found.')
        return redirect(calendar_url, **redirect_args)

    try:
        response = PayMongoClient().retrieve_checkout_session(payment.checkout_session_id)
    except Exception:
        messages.error(request, 'We could not verify payment yet. Please contact the resort before retrying.')
        return redirect(calendar_url, **redirect_args)

    checkout_data = response.get('data') or {}
    if checkout_data.get('id') != payment.checkout_session_id:
        messages.error(request, 'PayMongo returned a different checkout session; the booking was not finalized.')
        return redirect(calendar_url, **redirect_args)
    attributes = checkout_data.get('attributes') or {}
    checkout_status = str(attributes.get('status') or '').lower()
    paid_payment_items = []
    for payment_item in attributes.get('payments') or []:
        if not isinstance(payment_item, dict):
            continue
        payment_attributes = payment_item.get('attributes') or {}
        payment_status = str(payment_attributes.get('status') or '').lower()
        if payment_status in {'paid', 'succeeded'}:
            paid_payment_items.append(payment_attributes)
    if checkout_status not in {'paid', 'succeeded'} and not paid_payment_items:
        messages.info(request, 'PayMongo has not confirmed this payment. Your booking is not finalized.')
        return redirect(calendar_url, **redirect_args)

    paid_amounts = []
    payments_to_validate = paid_payment_items or (attributes.get('payments') or [])
    for payment_item in payments_to_validate:
        payment_attributes = payment_item if isinstance(payment_item, dict) else {}
        if payment_attributes.get('amount') is not None:
            paid_amounts.append(int(payment_attributes['amount']))
        currency = str(payment_attributes.get('currency') or '').upper()
        if currency and currency != payment.currency.upper():
            payment.status = 'failed'
            payment.failure_reason = f'Unexpected payment currency: {currency}.'
            payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
            messages.error(request, 'The paid currency does not match the booking. Contact support.')
            return redirect(calendar_url, **redirect_args)
    if paid_amounts and sum(paid_amounts) != payment.amount_centavos:
        payment.status = 'failed'
        payment.failure_reason = 'PayMongo payment amount does not match the booking total.'
        payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
        messages.error(request, 'The paid amount did not match the booking total. Contact support.')
        return redirect(calendar_url, **redirect_args)

    form = CheckinForm(booking_data)
    if not form.is_valid():
        payment.failure_reason = f'Paid booking details are invalid: {form.errors.as_json()}'
        payment.save(update_fields=['failure_reason', 'updated_at'])
        messages.error(request, 'Payment was received, but booking details need staff assistance.')
        return redirect(calendar_url, **redirect_args)

    booking = None
    dates_conflicted = False
    with db_transaction.atomic():
        payment = ResortBookingPayment.objects.select_for_update().get(pk=payment_id)
        if payment.status == 'paid' and payment.checkin_id:
            booking = payment.checkin
        else:
            cleaned_booking = form.save(commit=False)
            overlap = Checkins.objects.select_for_update().filter(
                room_id=cleaned_booking.room_id,
                checkin_date__date__lt=cleaned_booking.checkout_date.date(),
                checkout_date__date__gt=cleaned_booking.checkin_date.date(),
            ).exists()
            if overlap:
                payment.status = 'paid'
                payment.failure_reason = 'Payment was confirmed after the room dates were booked by another guest.'
                payment.save(update_fields=['status', 'failure_reason', 'updated_at'])
                dates_conflicted = True
            else:
                booking = cleaned_booking
                booking.save()
                try:
                    manager_profile = ensure_user_profile(request.user)
                    manager = ResortManager.objects.get_or_create(profile=manager_profile)[0]
                    booking.checked_in_by = manager
                    booking.save(update_fields=['checked_in_by'])
                    manager.checked_visitor.add(booking)
                except Exception:
                    pass
                day = booking.checkin_date.date()
                while day <= booking.checkout_date.date():
                    CheckinDay.objects.create(
                        checkin=booking.room,
                        day=day,
                        checkinday=booking.checkin_date,
                        checkoutday=booking.checkout_date,
                    )
                    day += timedelta(days=1)
                payment.status = 'paid'
                payment.checkin = booking
                payment.save(update_fields=['status', 'checkin', 'updated_at'])
    if dates_conflicted:
        messages.error(request, 'PayMongo received your payment, but the dates were booked meanwhile. Contact the resort to resolve it.')
        return redirect(calendar_url, **redirect_args)
    _send_booking_receipt_email(payment, booking, request)
    return _booking_receipt_redirect(booking)


def room_list(request, resortPackage_id=None):
    # TODO Edit it to only filter the rooms with user
    resort = resortItem.objects.get(id=resortPackage_id)
    request.session['resort_item'] = resort.id    
    resort_rooms = []
    resort_items = resortPackages.objects.filter(ItemOfResort=resort)
    for item in resort_items:
        for i in item.subPackages.all():
            resort_rooms.append(i)
    # request.session['resort_rooms'] = resort_rooms     
    request.session['resort_object'] = resortPackage_id

    request.resortRooms = resort_rooms

    calendar_item_object = generate_calendar(request , 1)
    context = {
        'resortRooms':request.resortRooms,
        'resortID': resort.id,
        'resortName': resort.name,
        'resortRealName': resort.RealName,        
        'resortObject':resort        
        # 'month':1,
        # 'year':1,
        # 'whatstepvalue':'upload_id'
        
    }
    return render(request, "resortManagement/room_list.html", context)

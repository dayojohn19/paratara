
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseServerError, HttpResponse, JsonResponse
from resorts.models import Packages, resortPackages,resortItem
from userProfile.models import UserCredentials
from .forms import CheckinForm
from userProfile.models import userPoster
from .models import Checkins, CheckinDay, ResortManager, ResortSubscription
import calendar
from django.db.models.functions import ExtractDay
from django.contrib.auth.decorators import login_required
# Create your views here.
# resort_id room_id room_month room_year 'previous'
from datetime import datetime, date, timedelta
from django.utils import timezone
import requests
from requests.auth import HTTPBasicAuth
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import base64
import json
import logging
import os
import re
from django.forms.models import model_to_dict
from django.utils.dateparse import parse_datetime
from django.urls import reverse

logger = logging.getLogger(__name__)

PAYPAL_API_BASE = getattr(settings, 'PAYPAL_API_BASE', 'https://api-m.paypal.com')
PAYPAL_SUBSCRIPTION_PLAN_ID = os.getenv(
    'PAYPAL_SUBSCRIPTION_PLAN_ID',
    getattr(settings, 'PAYPAL_SUBSCRIPTION_PLAN_ID', ''),
)
PAYPAL_SUBSCRIPTION_RETURN_URL = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_RETURN_URL',
    os.getenv('PAYPAL_SUBSCRIPTION_RETURN_URL', 'https://paratara.com/resortManagement/subscription/'),
)
PAYPAL_SUBSCRIPTION_CANCEL_URL = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_CANCEL_URL',
    os.getenv('PAYPAL_SUBSCRIPTION_CANCEL_URL', 'https://paratara.com/resortManagement/subscription/?cancel=1'),
)
PAYPAL_SUBSCRIPTION_BRAND = getattr(
    settings,
    'PAYPAL_SUBSCRIPTION_BRAND_NAME',
    os.getenv('PAYPAL_SUBSCRIPTION_BRAND_NAME', 'Paratara Resort'),
)

def has_active_subscription(resort_id):
    is_subscribed = ResortSubscription.objects.filter(
        resort=resort_id,
        status="ACTIVE"
    ).exists()
    print('Is Subscribed:', is_subscribed)
    return is_subscribed
    
    # if not has_active_subscription(request.user):
    # return redirect("subscribe")

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
        logger.debug('PayPal event missing subscription identifier, skipping: %s', event_type)
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
            logger.info('PayPal event for unknown subscription %s (custom_id=%s)', subscription_id, custom_id)
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
        logger.warning('PayPal webhook received invalid JSON', exc_info=True)
        return JsonResponse({'error': 'invalid payload'}, status=400)

    event_type = payload.get('event_type')
    resource = payload.get('resource', {})
    logger.info('PayPal webhook %s %s', event_type, resource.get('id'))

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
        logger.exception('PayPal subscription initiation failed for resort %s', resort.id)
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
    from imageapp.imageuploader import Upload_and_get_URL
    checkin_id = request.POST.get('checkin_id')
    checkobj = Checkins.objects.get(id=checkin_id)
    checkobj.id_picture= Upload_and_get_URL(request)
    checkobj.save()
    return checkobj.id_picture

def upload_image_ajax(request):
    from imageapp.imageuploader import Upload_and_get_URL
    
    uploadedurl = Upload_and_get_URL(request)
    return JsonResponse({
        "success": True,
        "url": uploadedurl  # assuming model has `image` field
    })    
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
        
        "paypal_client_id": settings.PAYPAL_WEBHOOK_CLIENT,             
        
         
        
    }
    # messages.success(request, "✅ MovedPayment completed and booking saved successfully!")
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
                    user = userPoster.objects.get(userID=request.user.id)
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
 
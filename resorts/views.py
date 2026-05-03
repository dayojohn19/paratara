from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import F
from .models import resortItem, resortPackages, sideImagesURLs, Packages, EventRegistration
from .forms import ResortForm, matterURLform
# Create your views here.
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden, HttpResponse
from django.conf import settings

from home.models import Places_v2
from django.urls import reverse
from webSchedule.utils import getPlacePhoto, upload_to_imgbb
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
import json
import os
from openai import OpenAI



def _is_resort_manager(user, resort: resortItem) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    try:
        # Avoid materializing all managers; do an efficient EXISTS check.
        return resort.adminManager.filter(pk=getattr(user, 'pk', None)).exists()
    except Exception:
        return False


def _is_any_resort_manager(user) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return resortItem.objects.filter(adminManager=user).exists()


def _forbidden_response(request, message: str = 'Managers only'):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': message}, status=403)
    return HttpResponseForbidden(message)


def _resort_view_throttle_key(request, resort_id: int) -> str:
    """Return a stable cache key for throttling 'views' per user/session."""
    try:
        user = getattr(request, 'user', None)
        if getattr(user, 'is_authenticated', False) and getattr(user, 'pk', None) is not None:
            ident = f"u{user.pk}"
        else:
            # Ensure we have a session key for anonymous users.
            sk = getattr(getattr(request, 'session', None), 'session_key', None)
            if not sk and hasattr(request, 'session'):
                request.session.create()
                sk = request.session.session_key
            ident = f"s{sk or 'no-session'}"
    except Exception:
        ident = "unknown"

    return f"resort:view:{resort_id}:{ident}"


def _should_count_resort_view(request, resort_id: int, window_seconds: int = 300) -> bool:
    """True if we should count a view now; False if recently counted."""
    key = _resort_view_throttle_key(request, resort_id)
    if cache.get(key):
        return False
    cache.set(key, True, timeout=window_seconds)
    return True


@login_required
@csrf_exempt
def update_amenity(request, resort_id):
    """Update a single amenity for a resort via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)
    
    resort = get_object_or_404(resortItem, id=resort_id)
    
    # Check if user is manager
    if not _is_resort_manager(request.user, resort):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        amenity = data.get('amenity')
        value = data.get('value')
        
        # List of valid amenity fields (include payment methods toggles)
        valid_amenities = [
            'has_wifi', 'has_pool', 'has_bidet', 'has_parking',
            'has_restaurant', 'has_bar', 'has_spa', 'has_gym',
            'has_beach_access', 'has_air_conditioning', 'has_hot_water',
            'has_breakfast', 'has_laundry', 'pet_friendly',
            'family_friendly', 'has_generator',
            'accepts_gcash', 'accepts_cash', 'accepts_debit_card', 'accepts_credit_card'
        ]
        
        if amenity not in valid_amenities:
            return JsonResponse({'success': False, 'error': 'Invalid amenity'}, status=400)
        
        # Update the amenity
        setattr(resort, amenity, bool(value))
        resort.save()
        
        return JsonResponse({
            'success': True, 
            'amenity': amenity, 
            'value': bool(value)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
def update_contacts(request, resort_id):
    """Update resort contact information via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)
    
    resort = get_object_or_404(resortItem, id=resort_id)
    
    # Check if user is manager
    if not _is_resort_manager(request.user, resort):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        contact_number = data.get('contactNumber', '').strip()
        contact_email = data.get('contactEmail', '').strip()
        whatsapp_number = data.get('whatsappNumber', '').strip()
        open_hours = data.get('open_hours', '').strip()
        website_url = data.get('websiteURL', '').strip()
        
        # Basic validation
        if not contact_number or not contact_email:
            return JsonResponse({
                'success': False, 
                'error': 'Contact number and email are required'
            }, status=400)
        
        # Update the resort
        resort.contactNumber = contact_number
        resort.contactEmail = contact_email
        resort.whatsappNumber = whatsapp_number
        resort.open_hours = open_hours
        resort.websiteURL = website_url
        resort.save()
        
        return JsonResponse({
            'success': True,
            'data': {
                'contactNumber': contact_number,
                'contactEmail': contact_email,
                'whatsappNumber': whatsapp_number,
                'open_hours': open_hours,
                'websiteURL': website_url
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def view_accommodation_guestlist(request, resort_id):
    from resortManagement.models import Checkins
    from .models import Packages

    resort = get_object_or_404(resortItem, id=resort_id)
    if not _is_resort_manager(request.user, resort):
        return redirect('resorts:getResort', resort.name)

    accommodations = (
        Packages.objects.filter(packageName__in=resort.resortAccomodations.all())
        .select_related('packageName')
        .order_by('title')
    )

    selected_room_id = request.GET.get('room')
    try:
        selected_room_id_int = int(selected_room_id) if selected_room_id else None
    except Exception:
        selected_room_id_int = None

    # Always scope guestlist to this resort; optionally filter by selected accommodation.
    guestlists_qs = Checkins.objects.filter(resort_id=resort_id)
    if selected_room_id_int and accommodations.filter(id=selected_room_id_int).exists():
        guestlists_qs = guestlists_qs.filter(room_id=selected_room_id_int)

    guestlists = (
        guestlists_qs.select_related('room', 'checked_in_by', 'checked_in_by__profile', 'resort')
        .order_by('-checkin_date')
    )

    data = {
        'resortObject': resort,
        'managerUser': 'managerUser',
        'guestlists': guestlists,
        'accommodations': accommodations,
        'selected_room_id': selected_room_id_int,
    }
    return render(request, 'resort/accommodation_guestlist.html', data)


def _redirect_back_with_params(request, **params):
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    referer = request.META.get('HTTP_REFERER')
    if not referer:
        # Fallback: resort page if available
        return redirect('/')

    parts = urlsplit(referer)
    qs = dict(parse_qsl(parts.query))
    for k, v in params.items():
        if v is None:
            qs.pop(k, None)
        else:
            qs[k] = str(v)
    redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(qs), parts.fragment))
    return redirect(redirect_url)


def register_event(request, package_id):
    if request.method != 'POST':
        return _redirect_back_with_params(request)

    event_item = get_object_or_404(Packages, id=package_id)
    resort = getattr(getattr(event_item, 'packageName', None), 'ItemOfResort', None)
    if resort is None:
        return _redirect_back_with_params(request, reg_error='1', event_id=package_id)

    full_name = (request.POST.get('full_name') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip()
    notes = (request.POST.get('notes') or '').strip()
    event_date = (request.POST.get('event_date') or '').strip()

    try:
        pax = int(request.POST.get('pax') or 1)
    except Exception:
        pax = 1
    if pax < 1:
        pax = 1

    if not full_name or not email:
        return _redirect_back_with_params(request, reg_error='1', event_id=package_id)

    existing = EventRegistration.objects.filter(event=event_item, email__iexact=email).first()
    if existing:
        existing.full_name = full_name
        existing.phone = phone
        existing.pax = pax
        existing.notes = notes
        existing.resort = resort
        existing.email = email
        existing.event_date = event_date
        existing.save()
        return _redirect_back_with_params(request, reg_exists='1', event_id=package_id)

    EventRegistration.objects.create(
        event=event_item,
        resort=resort,
        full_name=full_name,
        email=email,
        phone=phone,
        pax=pax,
        notes=notes,
        event_date=event_date,
    )
    return _redirect_back_with_params(request, reg_success='1', event_id=package_id)


@login_required
def view_package_registrations(request, package_id):
    package = get_object_or_404(
        Packages.objects.select_related('packageName__ItemOfResort').prefetch_related(
            'registrations',
            'siargaoevents',
            'siargaoevents__registrants',
        ),
        id=package_id,
    )

    resort = getattr(getattr(package, 'packageName', None), 'ItemOfResort', None)
    if resort is None:
        return redirect('/')
    if not _is_resort_manager(request.user, resort):
        return redirect('resorts:getResort', resort.name)


    data = {
        'resortObject': resort,
        'managerUser': 'managerUser',
        'package': package,
        'siargaoevents': package.siargaoevents.all(),
        'registrations': package.registrations.all(),
    }
    return render(request, 'resort/package_registrations.html', data)


def ocr_upload(request):
    """Render the OCR upload page for client-side image OCR."""
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if not _is_any_resort_manager(request.user):
        return _forbidden_response(request, 'Managers only')

    # Ensure CSRF cookie exists for JS fetch() calls on this page.
    try:
        from django.middleware.csrf import get_token
        get_token(request)
    except Exception:
        pass
    try:
        resorts = resortItem.objects.select_related('place').all().order_by('-timestamp')
    except Exception as e:
        print(f"Error fetching resorts: {e}")
        resorts = []
    
    # Get pre-selected resort ID from query parameter
    preselected_resort_id = request.GET.get('resort_id', None)
    
    return render(request, 'resorts/ocr_upload.html', {
        'resorts': resorts,
        'preselected_resort_id': preselected_resort_id
    })


@login_required
def ocr_save_menu(request):
    """Save OCR menu items to database with optional images.
    
    Expects POST FormData with:
        - resort_id: int
        - package_title: str (e.g., "Food Menu")
        - items[0][name]: str
        - items[0][description]: str
        - items[0][price]: int
        - items[0][image]: file (optional)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        resort_id = request.POST.get('resort_id')
        package_title = request.POST.get('package_title', 'Food Menu').strip()
        
        if not resort_id:
            return JsonResponse({'error': 'resort_id required'}, status=400)
        
        # Parse items from FormData format items[0][name], items[1][name], etc.
        items = []
        index = 0
        while True:
            name = request.POST.get(f'items[{index}][name]')
            if name is None:
                break
            
            description = request.POST.get(f'items[{index}][description]', '')
            price = request.POST.get(f'items[{index}][price]', 0)
            image = request.FILES.get(f'items[{index}][image]')
            
            items.append({
                'name': name,
                'description': description,
                'price': int(price) if price else 0,
                'image': image
            })
            index += 1
        
        if not items:
            return JsonResponse({'error': 'No items provided'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': f'Invalid data: {e}'}, status=400)
    
    try:
        resort = resortItem.objects.get(id=resort_id)
    except resortItem.DoesNotExist:
        return JsonResponse({'error': 'Resort not found'}, status=404)

    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')
    
    # Normalize package title to title case for consistency
    package_title_normalized = package_title.title()
    
    # Create or get the resortPackage (Food category) - case insensitive lookup
    existing_package = resortPackages.objects.filter(
        PackageTitle__iexact=package_title_normalized,
        ItemOfResort=resort
    ).first()
    
    if existing_package:
        resort_package = existing_package
        created = False
    else:
        resort_package = resortPackages.objects.create(
            PackageTitle=package_title_normalized,
            ItemOfResort=resort
        )
        created = True
        # Add to resort's food menu if newly created
        resort.resortFood.add(resort_package)
    
    created_items = []
    
    # Create individual menu items (Packages)
    for item_data in items:
        name = item_data.get('name', 'Untitled')
        description = item_data.get('description', '')
        price = item_data.get('price', 0)
        image_file = item_data.get('image')
        
        # Create the menu item
        menu_item = Packages.objects.create(
            packageName=resort_package,
            title=name,
            description=description,
            information='',  # Can be used for additional details
            price=price if price else 0
        )
        
        # Add to subPackages
        resort_package.subPackages.add(menu_item)
        
        # Upload and attach image if provided
        if image_file:
            try:
                image_url = upload_to_imgbb(image_file)
                if image_url:
                    newImageEntry = sideImagesURLs.objects.create(urlField=image_url)
                    menu_item.ImageURL.add(newImageEntry)
                    menu_item.save()
            except Exception as e:
                print(f'Failed to upload image for {name}: {e}')
        
        created_items.append({
            'id': menu_item.id,
            'title': menu_item.title,
            'price': menu_item.price
        })
    
    return JsonResponse({
        'success': True,
        'message': f'Created {len(created_items)} menu items',
        'package_id': resort_package.id,
        'package_title': resort_package.PackageTitle,
        'package_existed': not created,
        'items': created_items
    })


@login_required
def ocr_process_openai(request):
    """Endpoint: accept OCR text (JSON) and send to OpenAI to extract/organize menu items.

    Expects POST JSON: {"text": "...ocr text...", "filename": "optional.jpg"}
    Returns JSON with OpenAI result (attempts to parse returned JSON block).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # Prevent public/anonymous usage of your OpenAI key.
    if not _is_any_resort_manager(request.user):
        return _forbidden_response(request, 'Managers only')
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'Invalid JSON: {e}'}, status=400)

    text = payload.get('text', '')
    print('text: ',text)
    filename = payload.get('filename', '')
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)

    try:
        openai_api_key = settings.GROK_API_KEY
        if not openai_api_key:
            return JsonResponse({'error': 'GROK_API_KEY not set on server'}, status=500)

        client = OpenAI(api_key=openai_api_key, base_url='https://api.x.ai/v1')
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error initializing OpenAI client: {error_details}")
        return JsonResponse({'error': f'Failed to initialize OpenAI: {str(e)}'}, status=500)

    prompt = (
        "You are an expert at parsing restaurant menu data from OCR text.\n\n"
        "CRITICAL RULES - BE AGGRESSIVE:\n"
        "- Extract EVERY possible menu item, even from noisy OCR\n"
        "- If you see ANY capitalized word(s) followed by a number (especially 3-4 digits), treat it as a menu item\n"
        "- Even if there's OCR noise, extract what you can recognize\n"
        "- Each menu item typically has: a title (often in caps), ingredients/description, and a price\n"
        "- Multiple lines in caps may be ONE dish name (e.g., 'PALAWAN CASHEW CREAM\\nTOMATO PASTA (VEGAN)')\n"
        "- Ingredients are usually listed with | separators\n"
        "- DO NOT return empty items array unless the text is completely unintelligible\n\n"
        "OCR ERROR PATTERNS TO FIX:\n"
        "- Letter 'O' is often misread as zero '0' (e.g., '41O' = 410, 'TP 41 O' = 410)\n"
        "- Letter 'l' or 'I' might be digit '1'\n"
        "- 'TP', 'PHP', 'P', '₱' prefixes indicate Philippine Peso - strip these to get the number\n"
        "- Spaces in numbers should be removed (e.g., '4 1 0' = 410, '41 O' = 410)\n"
        "- Numbers at the very end of item text are usually prices\n"
        "- Random symbols like ~, ., ', %, etc. before/after text are OCR noise - ignore them\n\n"
        "EXAMPLES OF WHAT TO EXTRACT:\n"
        "- 'SAVORY\\n480' → {\"name\": \"SAVORY\", \"description\": \"\", \"price\": 480}\n"
        "- 'EGGS BENNY\\n450' → {\"name\": \"EGGS BENNY\", \"description\": \"\", \"price\": 450}\n"
        "- 'A~\\nSAVORY\\n480' → {\"name\": \"SAVORY\", \"description\": \"\", \"price\": 480} (ignore A~)\n\n"
        f"OCR filename: {filename}\n\nOCR TEXT:\n{text}\n\n"
        "Return ONLY a JSON object with:\n"
        "{\n"
        '  "items": [{"name": "Dish Name", "description": "details if any", "price": number_or_null}],\n'
        '  "offers": ["special offers if found"],\n'
        '  "notes": "brief parsing notes"\n'
        "}\n\n"
        "Extract ALL recognizable items. Respond with ONLY the JSON, no other text."
    )

    try:
        resp = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=3000,
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        return JsonResponse({'error': f'OpenAI API error: {str(e)}'}, status=500)

    # Try to extract JSON from the model reply
    import re
    m = re.search(r'(\{.*\}|\[.*\])', reply, re.S)
    if m:
        try:
            parsed = json.loads(m.group(1))
            print('Parsed: ',parsed)
            return JsonResponse({'success': True, 'data': parsed, 'raw': reply})
        except Exception as parse_err:
            print('Reply: ')
            return JsonResponse({'success': False, 'raw': reply, 'parse_error': str(parse_err)})
    else:
        return JsonResponse({'success': False, 'raw': reply, 'message': 'No JSON found in response'})


def showresort(request,placeName):
    print(request.user)
    print('Showing resort')
    if request.user.is_authenticated:
        print('User is authenticated')
        return getResort(request, placeName)
        # return redirect('resorts:getResort', placeName)
    from datetime import date
    today = date.today()
    return render(request, 'resort/modern.html',{'placeName': placeName,'currentMonth':today.month, 'currentYear': today.year})
    return render(request, 'resort/new.html',{'placeName': placeName,'currentMonth':today.month, 'currentYear': today.year})



def uploadResortGalleryImage(request, resortID):
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if request.method == 'POST':
        resort = get_object_or_404(resortItem, id=resortID)
        if not _is_resort_manager(request.user, resort):
            return _forbidden_response(request, 'Managers only')
        imageFiles = request.FILES.getlist('image')
        uploaded_count = 0
        for imageFile in imageFiles:
            image_url = upload_to_imgbb(imageFile)
            if image_url:
                newImageEntry = sideImagesURLs.objects.create(urlField=image_url)
                resort.resortGallery.add(newImageEntry)
                uploaded_count += 1
        if uploaded_count > 0:
            resort.save()
            print(f'{uploaded_count} images uploaded and added to gallery')
    return redirect(request.META['HTTP_REFERER'] + '?success=1')

def deleteGalleryImage(request, imageID):
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if request.method == 'GET':
        image = get_object_or_404(sideImagesURLs, id=imageID)
        # Check if user is authorized (manager or superuser)
        resorts_with_image = resortItem.objects.filter(resortGallery=image)
        if resorts_with_image.exists():
            resort = resorts_with_image.first()
            if _is_resort_manager(request.user, resort):
                image.delete()
                print('Gallery image deleted')
                
                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
            else:
                print('Sorry You are not authorized to delete this image')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Not authorized'})
                return _forbidden_response(request, 'Managers only')
        else:
            # If image is not associated with any resort, allow deletion if superuser
            if request.user.is_superuser:
                image.delete()
                print('Gallery image deleted')
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Image deleted successfully'})
            else:
                return _forbidden_response(request, 'Managers only')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Deletion failed'})
    
    return redirect(request.META.get('HTTP_REFERER', '/'))

def autopopulateResort(request):
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if not request.user.is_superuser:
        return _forbidden_response(request, 'Superuser only')
    from userProfile.models import UserCredentials
    random_resortURL = 'random_resortURL'
    random_resortName = 'random resort name'
    random_resortRealName = 'random resort real name'
    random_resortAddress = 'random resort address'
    random_resortContactNumber = '+639 5685 43805'
    random_resortEmail = 'random_resortemail@gmail.com'
    random_resortHeaderImageURL = 'https:somerandomimage.com/1.png'
    random_latitude = 12.123
    random_longitude = 123.12
    random_int = 3
    random_description = 'random_description'
    print('\n\n Creating Resorts')
    SomeRandomPlaceID = 2


    newresort = resortItem()

    main_domain = request.build_absolute_uri('/')[:-1]
    resortUrl = f'/resorts/{random_resortURL}/'
    newresort.resortQRLink = main_domain+resortUrl

    currentUser = UserCredentials.objects.get(pk=request.user.id)
    newresort.registeredBy = currentUser


    newresort.name = random_resortName
    newresort.RealName = random_resortRealName
    newresort.address = random_resortAddress

    # newresort.place = Places_v2.objects.get(id = SomeRandomPlaceID)
    newresort.place = Places_v2.objects.all()[0]
    print('place nMe: ',newresort.place)
    newresort.contactNumber = random_resortContactNumber
    newresort.contactEmail  = random_resortEmail
    newresort.headerImage = random_resortHeaderImageURL
    newresort.latitude = random_latitude
    newresort.longitude = random_longitude
    newresort.reviews = random_int
    newresort.description = random_description
    newresort.save()
    newresort.adminManager.add(currentUser)
    newresort.resort_ID = newresort.id
    print('Done Creating Resort \n')




def ShareQRcode(request, resortItem):
    from .QRCODE_Resort import createLogo
    from django.utils.text import slugify
    
    # Ensure websiteURL exists, generate if needed
    if not resortItem.websiteURL and resortItem.place:
        place_slug = resortItem.place.slug if resortItem.place.slug else slugify(resortItem.place.placename)
        resort_slug = resortItem.slug if resortItem.slug else slugify(resortItem.name)
        resortItem.websiteURL = f'https://paratara.com/{place_slug}/{resort_slug}'
        resortItem.save()
    
    # Use websiteURL for QR code
    URL_TO_SHARE = resortItem.websiteURL
    print(f'🔗 Generating QR code for: {URL_TO_SHARE}')
    
    return createLogo(
        request, resort_URL=URL_TO_SHARE, userID=request.user.id)
    # GenQRcode = pyqrcode.QRCode(URL_TO_SHARE, error='H')

# request.FILES['mainPhoto']


# Accepting request.FILES['FileName'] or a request
def uploadUphotoTry(request):
    print('Trying to upload Requested Files')
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    from userProfile.GoogleforDrive import Create_Service
    from googleapiclient.http import MediaFileUpload
    import os
    try:
        currentUser = request.user.id
        currentUserName = request.user.username
    except:
        currentUser = 'anonymous'
        currentUserName = 'anonymous'
    file_meta = {'name': str(currentUser)+'__'+currentUserName +
                 '__'+'resort', 'parents': ['1dUDyb2xcg8JFIxNVn-14ttM3v2hpJoj0']}
    initialURL = 'https://drive.google.com/uc?export=view&id='

    if request.method:
        if request.method == 'POST':
            try:
                print('File from POST method')
                objecPhoto = request.FILES['thismatter']    
            except:
                objecPhoto = request.FILES.get('image')

    else:
        objecPhoto = request
    # Upload Photo from Front end
    try:
        Fpath = os.path.splitext(objecPhoto.name)
        print(Fpath, '\n\n')
        maxFsize = 4542880
        # If file is more than 5 MB maxSize for google drive we shrink
        if objecPhoto.size > maxFsize:  # alternate the lessThan sign
            print('\nFile more Than 5mb\n')
            from PIL import Image
            fobj = Image.open(objecPhoto)
            v2resizeQuality = int(maxFsize/objecPhoto.size*100-40)
            EditedPicture = fobj.save(('More_File_uploaded'+Fpath[1]),
                                      optimize=False, quality=v2resizeQuality)
        else:
            EditedPicture = default_storage.save(
                ('Less_File_uploaded'+Fpath[1]), ContentFile(objecPhoto.read()))
    # For Logo Uploading
    except:
        EditedPicture = objecPhoto
    convertedPhoto = MediaFileUpload(EditedPicture)
    GDservice = Create_Service('client_s_API.json', 'drive', 'v3', [
                               'https://www.googleapis.com/auth/drive'])
    uploadedFile = GDservice.files().create(
        body=file_meta, media_body=convertedPhoto, fields='id').execute()
    FileUploadID = uploadedFile.get('id')
    filefullURL = initialURL+FileUploadID
    print('\\n\n\n\n\n returning  Successfully', filefullURL, '\n\n\n')
    return filefullURL


def sampleResort(request):

    # CALENDAR
    import calendar
    from datetime import date
    # cal = calendar
    # cal.weekheader(1)
    hc = calendar.HTMLCalendar(calendar.SUNDAY)
    # hc = hc.cssclasses = ["mon text-bold", "tu", "wed", "thu", "fri", "sat", "sun red"]
    # hc = hc.formatweek(2)
    # hc = calendar.HTMLCalendar(calendar.weekheader(1))
    # hc.weekheader(1)
    today = date.today()
    calendarValues = []
    for i in range(12):
        eachCalendar = hc.formatmonth(int(today.year), int(i+1))
        calendarValues.append({'id': i+1, 'calendar_html': eachCalendar})
    st = hc.formatmonth(int(today.year), int(today.month))

    # st = hc.formatweekday()
    # months = []
    # for i in range(1, 13):
    #     months.append(calendar.month_name[i])
    #  If visitor is resort adminManager
    # data = {
    #     "calendarObject": st,
    #     "resortObject": resort,
    #     "calendarValues": calendarValues,
    #     "currentMonth": int(today.month),
    #     "currentYear": int(today.year),
        
        
    #     # "resort_ID": resort.id,
    #     # "name": resort.name,
    #     # "RealName":resort.RealName,
    #     # "address" : resort.address,
    #     # "contactNumber" : resort.contactNumber,
    #     # "contactEmail" : resort.contactEmail,
    #     # "promotionalVideo" : resort.promotionalVideo,
    #     # "headerImage" : resort.headerImage,
    #     # "latitude" : resort.latitude,
    #     # "longitude" : resort.longitude,
    #     # "reviews" : resort.reviews,
    #     # "description" : resort.description,
    #     # "ActivitiesList":resort.ActivitiesList,
    #     # "AccomodationsList":resort.AccomodationsList,
    #     # "TourList":resort.TourList
    # }    
    data = {
        "calendarObject": st,
        "calendarValues": calendarValues,
        "currentMonth": int(today.month),
        "currentYear": int(today.year),
        "resort_ID": 111,
        "name": 'John Ds',
        "address": 'M/V Zim San Diego',
        "contactNumber": '+639 0931 2312',
        "contactEmail": 'dayo_contactMe@gmail.com',
        "promotionalVideo": 'https://promotionthis.com/video.mp3',
        "headerImage": 'https://img.com/firstimage.png',
        "latitude": 12.323,
        "longitude": 312.312,
        "reviews": 0,
        "description": 'Lorem ipsum dolor sit amet consectetur adipisicing elit. Placeat nihil incidunt laudantium ratione natusPellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vestibulum',
    }
    return render(request, 'resort/resort.html', data)


@login_required
def registerResort(request):
    if request.method == 'POST':
        newFormform = ResortForm(request.POST)
        if newFormform.is_valid():
            resort_instance = newFormform.save(commit=False)
            from userProfile.models import UserCredentials
            currentUser = UserCredentials.objects.get(pk=request.user.id)
            resort_instance.registeredBy = currentUser
            
            # Save first to generate slug and websiteURL
            resort_instance.save()
            newFormform.save_m2m()  # Save many-to-many relationships
            resort_instance.adminManager.add(currentUser)

            # Keep Places_v2.resortItem (M2M) in sync with resortItem.place (FK).
            # Signals attempt this on create, but this explicit add ensures older/edge flows
            # (or missing signal wiring) still populate the place page correctly.
            try:
                if resort_instance.place_id:
                    resort_instance.place.resortItem.add(resort_instance)
            except Exception as e:
                print(f"⚠️ Could not link resort to place M2M: {e}")
            
            # Refresh from database to get the auto-generated websiteURL
            resort_instance.refresh_from_db()
            
            # Ensure websiteURL is generated (fallback if not)
            if not resort_instance.websiteURL:
                from django.utils.text import slugify
                place_slug = resort_instance.place.slug if resort_instance.place.slug else slugify(resort_instance.place.placename)
                resort_slug = resort_instance.slug
                resort_instance.websiteURL = f'/{place_slug}/{resort_slug}/'
                resort_instance.save()
            
            print(f'✅ Resort created with websiteURL: {resort_instance.websiteURL}')
            
            # Creating QR CODE from websiteURL
            try:
                # Generate QR code from the auto-generated websiteURL
                LogoLocalUrl = ShareQRcode(request, resort_instance)
                request.FILES['thismatter'] = LogoLocalUrl
                # Upload QR code image to imgbb and store the image URL
                resort_instance.resortQRLink = upload_to_imgbb(LogoLocalUrl)
                resort_instance.save()
            except Exception as e:
                print(f'QR Code generation error: {e}')
            
            return redirect('resorts:getResort', resort_instance.name)

        else:
            print('NOT VALID')
            data = {"RESORTFORM": newFormform,
                    'message': 'Please Enter all requirements'}
            return render(request, f'resort/resortForm.html', data)
    else:
        data = {
            "RESORTFORM": ResortForm(),
        }  # TOD
        
        return render(request, f'resort/resortForm.html', data)


def matterResort(request, resortID):
    """
    >>> NOTE:
    on HTML 
            <form method="post" action="{{matterURL}}" enctype="multipart/form-data" >   
                {{masterURLform.thismatter}}  # FOR IMAGE FILE TYPE
                {{masterURLform.thismatter2}} # FOR URL TYPE
                <input value="TO_CHANGE_ON_RESORT"  name="whatsmatter" hidden>
            <form>

    >>>  NOTE
    """
    hotResort = resortItem.objects.get(id=resortID)
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if not _is_resort_manager(request.user, hotResort):
        return _forbidden_response(request, 'Managers only')
    if request.method == 'POST':
        matterForm = matterURLform(request.POST)
        if matterForm.is_valid():
            try:
                thismatterValueURL = uploadUphotoTry(request)
            except Exception as e:
                print(e)
                thismatterValueURL = request.POST.get('thismatter2', False)
        else:
            print('Form is not Valid')
        thismatterValueURL = str(thismatterValueURL)    
        print(f'\n URL VALUE: {thismatterValueURL}\n')
        print('---')
        attrTarget = getattr(hotResort, request.POST.get('whatsmatter'))
        print(
            f'\n Attribut Target: {attrTarget} \n ___ Type; {type(attrTarget)}\n')
        if isinstance(attrTarget, str):
            setattr(hotResort, request.POST.get(
                'whatsmatter'), thismatterValueURL)
            hotResort.save()
    return redirect(request.META['HTTP_REFERER'])
    #     if attrTarget is list:
    #         getattr(hotResort, request.POST.get('whatsmatter')).append(request.POST.get('thismatter'))
    #     else:
    #         setattr(hotResort,request.POST.get('whatsmatter'), request.POST.get('thismatter'))
    # return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def getResortInJSON(request, placeName):
    import json
    from django.http import HttpResponse
    resort = resortItem.objects.filter(name=placeName)
    import requests

    import http.client
    # API for Youtube Subtitles Do not delete this
    # https://rapidapi.com
    # https://rapidapi.com/DataFanatic/api/youtube-media-downloader/playground/apiendpoint_41d32934-25d1-41f0-8b52-d7bf0e8549aa
    # conn = http.client.HTTPSConnection(
    #     "youtube-media-downloader.p.rapidapi.com")
    # headers = {
    #     'x-rapidapi-key': "794419cb54mshdd74b298e6621cdp15d7cejsne06dd73160da",
    #     'x-rapidapi-host': "youtube-media-downloader.p.rapidapi.com"
    # }
    # conn.request("GET", "/v2/video/subtitles?format=xml", headers=headers)
    # res = conn.getresponse()
    # data = res.read()
    # print('\n\n THIS IS \n\n')
    # print(data.decode("utf-8"))

    # API FOR API  Do not delete this
    # https://jsonbin.io
    # url = 'https://api.jsonbin.io/v3/b/6707cd48acd3cb34a8948d8f'
    # headers = {
    #     'Content-Type': 'application/json',
    #     'X-Access-Key': '$2a$10$MVp2cChxnr/hiG.LfAgDpeWVjS0aO6x40bslFuwiQL2iEub1deA7a'
    # }
    # data = {"sample": "Hello World"}
    # req = requests.get(url, json=data, headers=headers)
    # print(req.text)

    return HttpResponse(json.dumps([resortdata.serialize() for resortdata in resort], sort_keys=True, indent=1), content_type="application/json")

def getResortwithID(request, resortID):
    resort = resortItem.objects.get(id=resortID)
    return redirect('resorts:getResort', resort.name)

def getResortBySlug(request, place_slug, resort_slug):
    """Handle the auto-generated URL pattern: /<place-slug>/<resort-slug>/"""
    from django.shortcuts import get_object_or_404

    queryset = resortItem.objects.select_related('place').filter(slug=resort_slug)
    if place_slug:
        queryset = queryset.filter(place__slug=place_slug)
    resort = get_object_or_404(queryset)

    # Redirect to the standard resort view
    return getResort(request, resort.name)

@xframe_options_exempt
def getResort(request, placeName):
    # print('\n\n Get Resort : ', request.session.get('resort_id'))
    # request.session['resort_id'] = resort.id

    main_domain = request.build_absolute_uri('/')[:-1]
    resortUrl = f'resorts/asdd/'
    print('Adding ', main_domain+resortUrl)
#
    print('Getting Resort')
    print(request.build_absolute_uri('/')[:-1])
    print(request.build_absolute_uri('/bands/?print=true'))
    print(request.build_absolute_uri())
    print('Getting Resort adding new resort object')
    # try:
    print('Place Name:', placeName)

    # NOTE: combined.html touches many related fields (packages, subpackages, images, registrations).
    # Prefetch here to avoid N+1 queries during template rendering.
    resort_qs = (
        resortItem.objects.select_related('place').prefetch_related(
            'resortGallery',
            'adminManager',
            'resortAccomodations',
            'resortAccomodations__subPackages',
            'resortAccomodations__subPackages__ImageURL',
            'resortActivities',
            'resortActivities__subPackages',
            'resortActivities__subPackages__ImageURL',
            'resortTour',
            'resortTour__subPackages',
            'resortTour__subPackages__ImageURL',
            'resortTour__subPackages__registrations',
            'resortFood',
            'resortFood__subPackages',
            'resortFood__subPackages__ImageURL',
        )
    )
    try:
        if request.session['new_resort_name'] != placeName:
            print('\n New Resort Getting thorugh place Name\n')
        # resort = resortItem.objects.get(id=ResortID)
            resort = get_object_or_404(resort_qs, name=placeName)
            request.session['new_resort_object'] = resort.id
            request.session['new_resort_name'] = resort.name        
        else:
            print('\n Getting Resort through Session \n')
            resortID = request.session.get('new_resort_object')
            resort = get_object_or_404(resort_qs, id=resortID)
    except Exception as e:
        print(e)
        print('\n\n CANNOT GET RESORT THROUGH SESSION, Getting through place Name\n')
        resort = get_object_or_404(resort_qs, name=placeName)
        request.session['new_resort_object'] = resort.id
        request.session['new_resort_name'] = resort.name

    print('Searching for', resort)
    
    # Count views at most once per user/session per window.
    if _should_count_resort_view(request, resort.id, window_seconds=300):
        resortItem.objects.filter(pk=resort.pk).update(reviews=F('reviews') + 1)
        resort.refresh_from_db(fields=['reviews'])
    print('Current reviews count:', resort.reviews)

    # Keep track of current resort in this session.


    # CALENDAR
    import calendar
    from datetime import date
    # cal = calendar
    # cal.weekheader(1)
    hc = calendar.HTMLCalendar(calendar.SUNDAY)
    # hc = hc.cssclasses = ["mon text-bold", "tu", "wed", "thu", "fri", "sat", "sun red"]
    # hc = hc.formatweek(2)
    # hc = calendar.HTMLCalendar(calendar.weekheader(1))
    # hc.weekheader(1)
    today = date.today()
    calendarValues = []
    for i in range(12):
        eachCalendar = hc.formatmonth(int(today.year), int(i+1))
        calendarValues.append({'id': i+1, 'calendar_html': eachCalendar})
    st = hc.formatmonth(int(today.year), int(today.month))
    print('Generated calendar for', today.year, today.month)

    # st = hc.formatweekday()
    # months = []
    # for i in range(1, 13):
    #     months.append(calendar.month_name[i])
    #  If visitor is resort adminManager
    data = {
        "calendarObject": st,
        "resortObject": resort,
        "placeName": placeName,  # Add placeName for modern.html template
        "calendarValues": calendarValues,
        "currentMonth": int(today.month),
        "currentYear": int(today.year),
        
        
        # "resort_ID": resort.id,
        # "name": resort.name,
        # "RealName":resort.RealName,
        # "address" : resort.address,
        # "contactNumber" : resort.contactNumber,
        # "contactEmail" : resort.contactEmail,
        # "promotionalVideo" : resort.promotionalVideo,
        # "headerImage" : resort.headerImage,
        # "latitude" : resort.latitude,
        # "longitude" : resort.longitude,
        # "reviews" : resort.reviews,
        # "description" : resort.description,
        # "ActivitiesList":resort.ActivitiesList,
        # "AccomodationsList":resort.AccomodationsList,
        # "TourList":resort.TourList
    }
    print('Prepared data for rendering resort page')
    if _is_resort_manager(request.user, resort):
        print('User is resort manager, using combined.html template')
        data.update({
            "matterURL": f"/resorts/matterResort/{resort.id}",
            # "places": Places_v2.objects.all(),
            "managerUser": "managerUser",  # TODO put buttons if the manager is logged in
            "masterURLform": matterURLform()
            # {{masterURLform}} # Todo
        })
        print('Added manager-specific data to context')
        # Add buttons
        return render(request, 'resort/combined.html', data)
    else:
        print('User is regular visitor, using modern.html template')
        # Regular users get the modern.html template
        return render(request, 'resort/modern.html', data)

    # except Exception as e:
    #     print(e)
    #     print('\n\n CANNOT GE TRESORT')
    #     data = {
    #         "resort_ID": 111,
    #         "name": 'Place Nmae',
    #         "address": 'M/V Zim San Diego',
    #         "contactNumber": '+639 0931 2312',
    #         "contactEmail": 'dayo_contactMe@gmail.com',
    #         "promotionalVideo": 'https://promotionthis.com/video.mp3',
    #         "headerImage": 'https://img.com/firstimage.png',
    #         "latitude": 12.323,
    #         "longitude": 312.312,
    #         "reviews": 0,
    #         "description": "This is just a sample of website I'm making for the resort management, not a real resort nor owner",
    #     }
        # data = {
        #     "RESORTFORM":ResortForm(),
        #     "resort_ID": '',
        #     "name": '',
        #     "address" : '',
        #     "contactNumber" : '',
        #     "contactEmail" : '',
        #     "promotionalVideo" : '',
        #     "headerImage" : '',
        #     "latitude" : '',
        #     "longitude" : '',
        #     "reviews" : '',
        #     "description" : "This is just a sample of website I'm making for the resort management, not a real resort nor owner",
        # }
    # return render(request, f'resort/{placeName}/{str(ResortID)}.html', data)
    request.resortObject = resort
    # return render(request, f'resort/resort.html', data)
    # Note: render call is now inside the if/else block above


@login_required
def createResortPackage(request, resortID):
    resort = get_object_or_404(resortItem, id=resortID)
    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')

    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        package_type = request.POST.get('packageType')

        if title and package_type:

            if package_type == 'accomodation':
                existing = resort.resortAccomodations.filter(PackageTitle__iexact=title).first()
                pkg = existing or resortPackages.objects.create(PackageTitle=title, ItemOfResort=resort)
                resort.resortAccomodations.add(pkg)
            elif package_type == 'activity':
                existing = resort.resortActivities.filter(PackageTitle__iexact=title).first()
                pkg = existing or resortPackages.objects.create(PackageTitle=title, ItemOfResort=resort)
                resort.resortActivities.add(pkg)
            elif package_type == 'tour':
                existing = resort.resortTour.filter(PackageTitle__iexact=title).first()
                pkg = existing or resortPackages.objects.create(PackageTitle=title, ItemOfResort=resort)
                resort.resortTour.add(pkg)

                return redirect('resorts:getResort', resort.name)
    return redirect(request.META['HTTP_REFERER'])

# TODO


def removePackages(request, packageID):
    print('\n\n\n\n DONE DONE \n\n', packageID, request.method)
    pass


@login_required
def removeResortPackage(request, resortPackageID):
    ResortPack = resortPackages.objects.get(id=resortPackageID)
    # Capture context for cleanup
    resort = ResortPack.ItemOfResort

    if resort is None:
        return _forbidden_response(request, 'Resort not found')
    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')

    place = getattr(resort, 'place', None)
    slug_or_name = getattr(resort, 'slug', None) or getattr(resort, 'name', '') if resort else ''
    host_link = f"/resort/{slug_or_name}/" if slug_or_name else ''
    # Collect subpackage titles before deleting
    subpacks = list(ResortPack.subPackages.all())
    sub_titles = [sub.title for sub in subpacks]
    # Delete all subpackages first to ensure cleanup (signals will handle events/images)
    for sub in subpacks:
        sub.delete()
    ResortPack.delete()

    # Additional safety: remove any remaining events tied to these subpackage titles
    try:
        from home.models import SiargaoEventSchedule
        qs = SiargaoEventSchedule.objects.filter(scheduleTypeAndMode="Resort Promotion")
        if sub_titles:
            qs = qs.filter(scheduleTitle__in=sub_titles)
        if host_link:
            qs = qs.filter(host_link=host_link)
        if place:
            qs = qs.filter(place=place)
        qs.delete()
    except Exception as e:
        print(f"⚠️ Error during event cleanup for package {ResortPack.id}: {e}")

    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Package deleted successfully'})
    
    return redirect(request.META['HTTP_REFERER'])


@login_required
def removeResortSubPackage(request, resortSubPackageID):
    subPack = Packages.objects.get(id=resortSubPackageID)

    resort = getattr(getattr(subPack, 'packageName', None), 'ItemOfResort', None)
    if resort is None:
        return _forbidden_response(request, 'Resort not found')
    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')

    subPack.delete()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Item deleted successfully'})
    
    return redirect(request.META['HTTP_REFERER'])


@login_required
def editPackageItem(request, itemId):
    """Generic edit function for menu items, accommodations, activities, and promotions"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        item = Packages.objects.get(id=itemId)
        
        # Check permissions
        resort = getattr(getattr(item, 'packageName', None), 'ItemOfResort', None)
        if resort is None:
            return JsonResponse({'error': 'Resort not found'}, status=404)
        if not _is_resort_manager(request.user, resort):
            return JsonResponse({'error': 'Managers only'}, status=403)
 # Handle FormData (with files) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData with potential file uploads
            item.title = request.POST.get('title', item.title)
            item.description = request.POST.get('description', item.description)
            item.price = request.POST.get('price', item.price)
            if 'information' in request.POST:
                item.information = request.POST.get('information')
            if 'expires_at' in request.POST:
                expires_at_str = request.POST.get('expires_at')
                if expires_at_str:
                    from datetime import datetime
                    try:
                        item.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                else:
                    item.expires_at = None
            

            
            # Handle image uploads
            images = request.FILES.getlist('images')
            if images:
                for image_file in images:
                    try:
                        # Upload to imgbb
                        image_url = upload_to_imgbb(image_file)
                        if image_url:
                            img_obj = sideImagesURLs.objects.create(urlField=image_url)
                            item.ImageURL.add(img_obj)
                    except Exception as e:
                        print(f'Error uploading image: {e}')

        else:
            # JSON data (backward compatibility)
            import json
            data = json.loads(request.body)
            item.title = data.get('title', item.title)
            item.description = data.get('description', item.description)
            item.price = data.get('price', item.price)
            if 'information' in data:
                item.information = data.get('information')
            if 'expires_at' in data:
                expires_at_str = data.get('expires_at')
                if expires_at_str:
                    from datetime import datetime
                    try:
                        item.expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                else:
                    item.expires_at = None
            
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Item updated successfully',
            'item': {
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'price': str(item.price),
                'information': getattr(item, 'information', ''),
                'expires_at': str(item.expires_at) if hasattr(item, 'expires_at') and item.expires_at else ''
            }
        })
        
    except Packages.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:

        return JsonResponse({'error': str(e)}, status=500)
        #         else:
        #             item.expires_at = None
        
        # item.save()
        
        # return JsonResponse({
        #     'success': True,
        #     'message': 'Item updated successfully',
        #     'item': {
        #         'id': item.id,
        #         'title': item.title,
        #         'description': item.description,
        #         'price': str(item.price),
        #         'information': getattr(item, 'information', ''),
        #         'expires_at': str(item.expires_at) if hasattr(item, 'expires_at') and item.expires_at else ''
        #     }
        # })
        
    # except Packages.DoesNotExist:
    #     return JsonResponse({'error': 'Item not found'}, status=404)
    # except Exception as e:
    #     return JsonResponse({'error': str(e)}, status=500)


@login_required
def deletePackageImage(request, imageId):
    """Delete an image from a package item"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        image = sideImagesURLs.objects.get(id=imageId)
        
        # Check permissions - find any package that uses this image
        packages = Packages.objects.filter(ImageURL=image)
        if packages.exists():
            package = packages.first()
            resort = getattr(getattr(package, 'packageName', None), 'ItemOfResort', None)
            if resort and not _is_resort_manager(request.user, resort):
                return JsonResponse({'error': 'Managers only'}, status=403)
        
        image.delete()
        return JsonResponse({'success': True, 'message': 'Image deleted'})
        
    except sideImagesURLs.DoesNotExist:
        return JsonResponse({'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def togglePackageAvailability(request, itemId):
    """Toggle availability of a Packages item (menu item / activity / accommodation / promo)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        item = Packages.objects.get(id=itemId)

        resort = getattr(getattr(item, 'packageName', None), 'ItemOfResort', None)
        if resort is None:
            return JsonResponse({'error': 'Resort not found'}, status=404)
        if not _is_resort_manager(request.user, resort):
            return JsonResponse({'error': 'Managers only'}, status=403)

        is_available = None

        content_type = request.content_type or ''
        if 'application/json' in content_type:
            import json
            data = json.loads(request.body or '{}')
            if 'is_available' in data:
                is_available = bool(data.get('is_available'))
        else:
            if 'is_available' in request.POST:
                val = (request.POST.get('is_available') or '').strip().lower()
                is_available = val in {'1', 'true', 'yes', 'on'}

        if is_available is None:
            item.is_available = not bool(getattr(item, 'is_available', True))
        else:
            item.is_available = is_available

        item.save(update_fields=['is_available'])

        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'is_available': item.is_available,
        })

    except Packages.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# def createPackages(request,resortPackageID):


@login_required
def createPackages(request):
    # return data
    if request.method == 'POST':
        package_id = (request.POST.get('packageID') or '').strip()
        package_title = (request.POST.get('package_title') or '').strip()
        package_type = (request.POST.get('packageType') or '').strip()
        resort_id = (request.POST.get('resort_id') or '').strip()

        PackageOfResort = None

        resort = None
        if package_id:
            PackageOfResort = resortPackages.objects.get(id=package_id)
            resort = getattr(PackageOfResort, 'ItemOfResort', None)
        else:
            # Allow creating/choosing package by title (mirrors OCR menu behavior)
            if not (resort_id and package_title and package_type):
                return redirect(request.META['HTTP_REFERER'])

            resort = resortItem.objects.get(id=resort_id)
            package_title_normalized = package_title.title()

            if package_type == 'accomodation':
                existing = resort.resortAccomodations.filter(PackageTitle__iexact=package_title_normalized).first()
                PackageOfResort = existing or resortPackages.objects.create(
                    PackageTitle=package_title_normalized,
                    ItemOfResort=resort,
                )
                resort.resortAccomodations.add(PackageOfResort)
            elif package_type == 'activity':
                existing = resort.resortActivities.filter(PackageTitle__iexact=package_title_normalized).first()
                PackageOfResort = existing or resortPackages.objects.create(
                    PackageTitle=package_title_normalized,
                    ItemOfResort=resort,
                )
                resort.resortActivities.add(PackageOfResort)
            elif package_type == 'tour':
                existing = resort.resortTour.filter(PackageTitle__iexact=package_title_normalized).first()
                PackageOfResort = existing or resortPackages.objects.create(
                    PackageTitle=package_title_normalized,
                    ItemOfResort=resort,
                )
                resort.resortTour.add(PackageOfResort)
            elif package_type == 'food':
                existing = resort.resortFood.filter(PackageTitle__iexact=package_title_normalized).first()
                PackageOfResort = existing or resortPackages.objects.create(
                    PackageTitle=package_title_normalized,
                    ItemOfResort=resort,
                )
                resort.resortFood.add(PackageOfResort)
            else:
                return redirect(request.META['HTTP_REFERER'])

        if resort is None:
            return _forbidden_response(request, 'Resort not found')
        if not _is_resort_manager(request.user, resort):
            return _forbidden_response(request, 'Managers only')

        from django.utils.dateparse import parse_datetime, parse_date
        from django.utils import timezone
        expires_input = request.POST.get('expires_at')
        expires_dt = None
        if expires_input:
            # Try parsing as full datetime first
            dt = parse_datetime(expires_input)
            if dt is None:
                # Fallback: parse a date and assume end of day local time
                d = parse_date(expires_input)
                if d is not None:
                    dt = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.max.time()))
            if dt is not None:
                expires_dt = dt
        newPackage = Packages(
            packageName=PackageOfResort,
            title=request.POST['title'],
            description=request.POST['description'],
            information=request.POST['information'],
            price=request.POST['price'],
            website=PackageOfResort.ItemOfResort.websiteURL,
            expires_at=expires_dt
        )
        # Mark to skip auto event creation in signal
        newPackage._skip_event_creation = True
        # newPackage.packageName = PackageOfResort
        newPackage.save()
        PackageOfResort.subPackages.add(newPackage)
        PackageOfResort.save()
        
        # Handle image file uploads to Cloudinary BEFORE triggering event creation
        if 'images' in request.FILES:
            try:
                from userProfile.cloudinary_uploader import uploadtoCloudinary
                for image_file in request.FILES.getlist('images'):
                    # Create a safe public_id by replacing spaces and special chars
                    safe_filename = "".join(c for c in image_file.name if c.isalnum() or c in "._-").rstrip()
                    public_id = f"accommodation_{newPackage.id}_{newPackage.title.replace(' ', '_')}_{safe_filename}"
                    imageURL = uploadtoCloudinary(request, image_file, public_id)
                    
                    newImage = sideImagesURLs(urlField=imageURL)
                    newImage.save()
                    newPackage.ImageURL.add(newImage)
                newPackage.save()  # Save after adding images
                
                # Now that images are added, manually trigger event creation
                from resorts.signals import _create_events_for_subpackage
                _create_events_for_subpackage(newPackage)
            except Exception as e:
                print(f"Error uploading images to Cloudinary: {e}")
                # Still create events even if image upload fails
                from resorts.signals import _create_events_for_subpackage
                _create_events_for_subpackage(newPackage)
        else:
            # No image files - create events immediately
            from resorts.signals import _create_events_for_subpackage
            _create_events_for_subpackage(newPackage)
        
        # PackageOfResort.Packages.add(neww22213123222222221132222Package)
        try:
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
            referer = request.META.get('HTTP_REFERER', '/')
            parts = urlsplit(referer)
            qs = dict(parse_qsl(parts.query))
            qs['success'] = '1'

            # Tag which section saved, so we only clear the right form in the UI
            success_type = (request.POST.get('packageType') or '').strip()
            if not success_type:
                try:
                    resort = getattr(PackageOfResort, 'ItemOfResort', None)
                    if resort is not None:
                        if resort.resortAccomodations.filter(id=PackageOfResort.id).exists():
                            success_type = 'accomodation'
                        elif resort.resortActivities.filter(id=PackageOfResort.id).exists():
                            success_type = 'activity'
                        elif resort.resortTour.filter(id=PackageOfResort.id).exists():
                            success_type = 'tour'
                        elif resort.resortFood.filter(id=PackageOfResort.id).exists():
                            success_type = 'food'
                except Exception:
                    success_type = ''
            if success_type:
                qs['success_type'] = success_type

            redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(qs), parts.fragment))
            return redirect(redirect_url)
        except Exception:
            return redirect(request.META.get('HTTP_REFERER', '/') + '?success=1')
        # return redirect('resorts:getResort' , 'palawan',resortID )


def createSubPackageImage(request):
    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if request.method == 'POST':
        print('\n\n\n\n DONE DONE \n\n', request.POST, request.FILES)
        try:
            # Use Cloudinary uploader for images
            from userProfile.cloudinary_uploader import uploadtoCloudinary
            file_obj = request.FILES.get("image")
            # Build a safe public_id using subID and filename
            raw_name = getattr(file_obj, 'name', 'upload')
            safe_filename = "".join(c for c in raw_name if c.isalnum() or c in "._-").rstrip()
            sub_id = request.POST.get('subID') or 'unknown'
            public_id = f"subpackage_{sub_id}_{safe_filename}"
            image_url = uploadtoCloudinary(request, file_obj, public_id)
            print("\n\n IMAGE URL: ", image_url)
            ImagePosted = image_url
            
        except Exception as e:
            print(e)
            ImagePosted = request.POST['imageURL']
        newImage = sideImagesURLs(urlField=ImagePosted)
        newImage.save()
        subPackage = Packages.objects.get(id=request.POST['subID'])

        resort = getattr(getattr(subPackage, 'packageName', None), 'ItemOfResort', None)
        if resort is None:
            return _forbidden_response(request, 'Resort not found')
        if not _is_resort_manager(request.user, resort):
            return _forbidden_response(request, 'Managers only')

        subPackage.ImageURL.add(newImage)
        subPackage.save()
        return redirect(request.META['HTTP_REFERER'])


def putPlace(request):
    print('\n\n PRINTING ', request.POST['placeID'], type(
        request.POST['placeID']))
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return _forbidden_response(request, 'Login required')
        if request.POST['other'] != '':
            place = Places_v2.objects.get_or_create(
                placename=request.POST['other'])[0]
            place.save() 
            place.placeID = place.id
            place.save()
        else:
            # place = Places_v2.objects.get(pk=request.POST['placeID'])
            place = Places_v2.objects.get_or_create(placename=request.POST['placeID'])[0]
        resort = resortItem.objects.get(pk=request.POST['resortID'])

        if not _is_resort_manager(request.user, resort):
            return _forbidden_response(request, 'Managers only')

        resort.place = place
        place.resortItem.add(resort)
        # place.placePhoto = getPlacePhoto(request, d['name'])

        place.placePhoto = getPlacePhoto(request, request.POST['other'])
        place.save()
        resort.save()
        return redirect(request.META['HTTP_REFERER'])


# SMS Testing Views
def test_sms(request):
    """Test SMS functionality with Semaphore API"""
    from webSchedule.utils import send_semaphore_sms

    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if not request.user.is_superuser:
        return _forbidden_response(request, 'Superuser only')
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        message = request.POST.get('message', 'Test SMS from Paratara!')
        
        if phone_number:
            result = send_semaphore_sms(phone_number, message)
            return JsonResponse({
                'success': True,
                'result': result,
                'message': f'SMS sent to {phone_number}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Phone number required'
            })
    
    return render(request, 'resorts/test_sms.html')


def send_resort_sms_view(request, resort_id):
    """Send SMS to a specific resort"""
    from webSchedule.utils import send_resort_sms

    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    
    resort = get_object_or_404(resortItem, id=resort_id)

    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')
    
    if request.method == 'POST':
        message = request.POST.get('message', f'Hello from Paratara! Inquiry about {resort.RealName}')
        result = send_resort_sms(resort, message)
        
        return JsonResponse({
            'success': True,
            'result': result,
            'resort': resort.RealName,
            'phone': resort.contactNumber
        })
    
    return JsonResponse({'error': 'POST required'})


# Twilio SMS Testing Views
def test_sms_twilio(request):
    """Test SMS functionality with Twilio API"""
    from webSchedule.utils import send_twilio_sms

    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    if not request.user.is_superuser:
        return _forbidden_response(request, 'Superuser only')
    
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        message = request.POST.get('message', 'Test SMS from Paratara!')
        
        if phone_number:
            result = send_twilio_sms(phone_number, message)
            return JsonResponse({
                'success': True,
                'result': result,
                'message': f'SMS sent to {phone_number}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Phone number required'
            })
    
    return render(request, 'resorts/test_sms.html')


def send_resort_sms_twilio_view(request, resort_id):
    """Send SMS to a specific resort using Twilio"""
    from webSchedule.utils import send_resort_sms_twilio

    if not request.user.is_authenticated:
        return _forbidden_response(request, 'Login required')
    
    resort = get_object_or_404(resortItem, id=resort_id)

    if not _is_resort_manager(request.user, resort):
        return _forbidden_response(request, 'Managers only')
    
    if request.method == 'POST':
        message = request.POST.get('message', f'Hello from Paratara! Inquiry about {resort.RealName}')
        result = send_resort_sms_twilio(resort, message)
        
        return JsonResponse({
            'success': True,
            'result': result,
            'resort': resort.RealName,
            'phone': resort.contactNumber
        })
    
    return JsonResponse({'error': 'POST required'})

from .models import InactiveResortItem
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@login_required
def reactivate_resort_view(request):
    """
    Reactivate a resort from InactiveResortItem to resortItem via POST.
    POST data: id (InactiveResortItem id)
    Returns JSON with result.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    if not request.user.is_superuser:
        return _forbidden_response(request, 'Superuser only')
    try:
        resort_id = int(request.POST.get('id'))
        inactive = InactiveResortItem.objects.get(id=resort_id)
    except (TypeError, ValueError, InactiveResortItem.DoesNotExist):
        return JsonResponse({'error': 'Invalid or missing id'}, status=400)

    from .models import resortItem
    # Create new resortItem
    active = resortItem.objects.create(
        resortQRLink=inactive.resortQRLink,
        websiteURL=inactive.websiteURL,
        resort_ID=inactive.resort_ID,
        name=inactive.name,
        RealName=inactive.RealName,
        address=inactive.address,
        place=inactive.place,
        contactNumber=inactive.contactNumber,
        contactEmail=inactive.contactEmail,
        whatsappNumber=inactive.whatsappNumber,
        open_hours=getattr(inactive, 'open_hours', '') or '',
        promotionalVideo=inactive.promotionalVideo,
        virtualpicture=inactive.virtualpicture,
        headerImage=inactive.headerImage,
        latitude=inactive.latitude,
        longitude=inactive.longitude,
        reviews=inactive.reviews,
        description=inactive.description,
        province=inactive.province,
        slug=inactive.slug,
        last_visited=inactive.last_visited,
    )
    active.save()
    active.resortGallery.set(inactive.resortGallery.all())
    active.resortAccomodations.set(inactive.resortAccomodations.all())
    active.resortSchedules.set(inactive.resortSchedules.all())
    active.adminManager.set(inactive.adminManager.all())
    if inactive.registeredBy:
        active.registeredBy = inactive.registeredBy
    active.resortActivities.set(inactive.resortActivities.all())
    active.resortTour.set(inactive.resortTour.all())
    active.resortFood.set(inactive.resortFood.all())
    active.save()
    inactive.delete()
    return JsonResponse({'success': True, 'reactivated': active.RealName, 'id': active.id})

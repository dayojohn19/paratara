
from apis.gdrive_upload import delete_gdrive_file_by_id
import json
import string
import random
from django.shortcuts import render, redirect
from django.http import HttpResponse
# Create your views here.
from django.urls import reverse
from rest_framework.decorators import api_view
# from rest_framework.response import Response
import json
from pprint import pprint
from .models import Collection,Visitor
from django.http import HttpResponse
from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, random
from django.utils.text import slugify
from PIL import ImageOps
import requests, io
import os, io, requests

from datetime import datetime

# Cloudinary (optional) — used for uploading generated images
try:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name="dg6xfou1t",
        api_key="875272749645643",
        api_secret="1KRVTKh6DiluDJB2SIovyFpizd0",
        secure=True,
    )
except Exception:
    cloudinary = None

from django.core import signing
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.db.models import Count  

@csrf_exempt
def list_a4_collages(request):
    """Return a JSON list of all A4 collage image URLs in image_cards/a4_collages."""
    if request.method == 'GET':
        import os
        from django.conf import settings
        a4_dir = os.path.join(settings.MEDIA_ROOT, 'image_cards', 'a4_collages')
        if not os.path.exists(a4_dir):
            return JsonResponse({'images': []})
        files = [f for f in os.listdir(a4_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        # Build URLs using MEDIA_URL
        urls = [settings.MEDIA_URL.rstrip('/') + '/image_cards/a4_collages/' + f for f in files]
        return JsonResponse({'images': urls})
    return JsonResponse({'error': 'Invalid request method.'}, status=405)

def get_map(request, placeName):
    # TODO GET OR CREATE THAT HTML ok?
     from home.models import Places_v2
     print('\n\n Getting Map for Place Name: ', placeName, '\n\n')
     place = Places_v2.objects.get(slug=slugify(placeName))
     try:
         tourist_spots = place.tourist_spots.exclude(coords__isnull=True).annotate(visit_count=Count('visit')).all()
         if tourist_spots:
             # Calculate center as average of tourist spots coords
             lats = []
             lngs = []
             for spot in tourist_spots:
                 if spot.coords:
                     if isinstance(spot.coords, list):
                         if spot.coords[0] is not None and spot.coords[1] is not None:
                             lats.append(spot.coords[0])
                             lngs.append(spot.coords[1])
                     elif isinstance(spot.coords, dict):
                         # Accept multiple key variants: 'lat'/'lng' or 'latitude'/'longitude'
                         lat = spot.coords.get('lat') if spot.coords.get('lat') is not None else spot.coords.get('latitude')
                         lng = spot.coords.get('lng') if spot.coords.get('lng') is not None else spot.coords.get('longitude')
                         if lat is not None and lng is not None:
                             lats.append(lat)
                             lngs.append(lng)
             if lats:
                center = [sum(lats)/len(lats), sum(lngs)/len(lngs)]
             else:
                center = [9.756545906356644, 126.11749390487918]
         else:
             center = [9.756545906356644, 126.11749390487918]
     except Places_v2.DoesNotExist:
         tourist_spots = []
         center = [9.756545906356644, 126.11749390487918]
     stormglass_api_key = os.getenv('STORMGLASS_API_KEY', '')
     return render(
         request,

         f'garden/map/{place.slug}.html',
         {
             'tourist_spots': tourist_spots,
             'placeName': placeName,
             'center': center,
             'stormglass_api_key': stormglass_api_key,
         },
     )

# Security salt
QR_SALT = "only-from-qr-v1"
def qr_entry(request, code):
    """
    Entry point when the QR code is scanned.
    Generates a signed short-lived token, then redirects
    to the real page with that token.
    """
    payload = {
        "code": code,
        "ts": timezone.now().isoformat()
    }
    token = signing.dumps(payload, salt=QR_SALT)
    # return redirect(f"{reverse('garden:secret_page')}?token={token}")
    return redirect(f"{reverse('garden:secret_page')}?token={token}&collectionStr={code}")

def secret_page(request):
    """
    Actual page to protect.
    Accessible only with a valid token from the QR redirect.
    """
    token = request.GET.get("token")
    if not token:
        return HttpResponseForbidden("🚫 Access denied — QR code required.")

    try:
        data = signing.loads(token, salt=QR_SALT, max_age=120)  # 2 minutes validity
    except signing.BadSignature:
        return HttpResponseForbidden("🚫 Invalid QR token.")
    except signing.SignatureExpired:
        return HttpResponseForbidden("⌛ QR token expired. Please rescan.")

    # Passed validation — render your real page
    # collectionStr = request.GET.get("collectionStr")
    # return render(request, 'garden/index.html', {'collectionStr': collectionStr})
    # return render(request, "garden/secret_page.html", {
    #     "code": data["code"]
    #     })

    return render(request, "garden/index.html", {
        'collectionStr': data["code"]
        })
    


def index(request, collectionStr):
    return render(request, 'garden/index.html', {'collectionStr': collectionStr})

def collection_list_api(request):
    data = json.loads(request.body)
    user = data['username']
    userID = data['userID']
    print(f"user: {user}")
    print(f"userID: {userID}")

    visitorUser = Visitor.objects.get(visitorName=user, visitorID=userID)
    # collections = Collection.objects.filter(collectionCollector=visitorUser)
    collections = Collection.objects.all()
    data = [col.serialize() for col in collections]
    return JsonResponse(data, safe=False)


@api_view(['GET', 'POST','PUT'])
@csrf_exempt
def lookPlace(request, tokenStr=None,collectionStr=None):

    data = {}
    if request.body:
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, TypeError):
            data = {}

    user = data.get('username')
    userID = data.get('userID')
    visitorUser = Visitor.objects.get_or_create(visitorName=user, visitorID=userID)[0]
    print(f"user: {user}")
    print(f"userID: {userID}")    
    bodyCollectionStr = data.get('collectionStr', None)
    collection_key = bodyCollectionStr or collectionStr
    print(f"Collection: {collection_key}")  
    
    if collection_key is not None:
        try:
            collectionUser = Collection.objects.get(collectionUniqueID=collection_key)
        except Collection.DoesNotExist:
            return HttpResponse(
                json.dumps({"error": f"we cannot find Collection '{collection_key}' not found."}),
                content_type="application/json",
                status=404
            )
    else:
        scan_result = data.get('scan_result')
        if not scan_result:
            return HttpResponse(
                json.dumps({"error": "collectionStr or scan_result is required."}),
                content_type="application/json",
                status=400
            )
        result = scan_result.replace('"', '').split(',')
        collectionUser = Collection.objects.get(collectionUniqueID=result[2])

    if not user or not userID:
        serializedData = collectionUser.serialize()
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

    if collectionUser.collectionIsCollected == True:
        collectionUser.tobecollected = True
        serializedData = collectionUser.serialize()
        return HttpResponse(json.dumps(serializedData), content_type="application/json")
    collectionUser.collectionCollector = visitorUser
    collectionUser.collectionIsCollected = True
    collectionUser.save()
    visitorUser.visitorCollections.add(collectionUser)    
    # serializedData = collect_and_cleanup_collection(collectionUser, visitorUser)
    serializedData = collectionUser.serialize()
    return HttpResponse(json.dumps(serializedData), content_type="application/json")

def collect_and_cleanup_collection(collectionUser, visitorUser):

    """
    Handles marking a collection as collected, deleting associated Cloudinary and Google Drive images,
    updating the collection's local file and picture, and saving changes. Returns serialized data.
    """
    print(f"[collect_and_cleanup_collection] Set collectionCollector: {visitorUser}")
    collectionUser.collectionCollector = visitorUser
    collectionUser.collectionIsCollected = True
    print("[collect_and_cleanup_collection] Marked collection as collected.")
    # Delete Cloudinary image using localfile as public_id, then set localfile to placePicture
    # localfile_id = getattr(collectionUser, 'collectionLocalFile', None)
    # print(f"[collect_and_cleanup_collection] Attempting to delete Cloudinary image with id or url: {localfile_id}")
    # public_id = None
    # if localfile_id and cloudinary:
    #     # If it's a URL, extract the public_id
    #     if localfile_id.startswith('http') or localfile_id.startswith('https'):
    #         import re
    #         # Extract after '/upload/' and remove extension
    #         match = re.search(r'/upload/(?:v\d+/)?([^\.]+)', localfile_id)
    #         if match:
    #             public_id = match.group(1)
    #             print(f"[collect_and_cleanup_collection] Extracted public_id from URL: {public_id}")
    #         else:
    #             print(f"[collect_and_cleanup_collection] Could not extract public_id from URL: {localfile_id}")
    #     else:
    #         public_id = localfile_id
    #     if public_id:
    #         try:
    #             result = cloudinary.uploader.destroy(public_id, invalidate=True)
    #             print(f"[collect_and_cleanup_collection] Cloudinary delete result: {result}")

    #             # Set localfile to the collectionPlace's placePicture
    #             place_picture = getattr(collectionUser.collectionPlace, 'placePicture', None)
    #             print(f"[collect_and_cleanup_collection] Setting collectionLocalFile and collectionPicture to placePicture: {place_picture}")
    #             if place_picture:
    #                 collectionUser.collectionLocalFile = place_picture
    #                 collectionUser.collectionPicture = place_picture
    #                 print(f"[collect_and_cleanup_collection] Updated collectionLocalFile and collectionPicture to: {place_picture}")

    #         except Exception as e:
    #             print(f"[collect_and_cleanup_collection] Failed to delete Cloudinary image with public_id {public_id}: {e}")
    #     else:
    #         print(f"[collect_and_cleanup_collection] No valid public_id found for Cloudinary deletion.")






    # Attempt to delete the Google Drive image if URL is present
    gdrive_url = getattr(collectionUser, 'collectionGoogleDriveURL', None)
    print(f"[collect_and_cleanup_collection] Checking for Google Drive file to delete: {gdrive_url}")
    if gdrive_url and 'id=' in gdrive_url:
        # Extract file ID from URL (format: ...id=FILEID)
        import re
        match = re.search(r'id=([\w-]+)', gdrive_url)
        if match:
            file_id = match.group(1)
            print(f"[collect_and_cleanup_collection] Deleting Google Drive file with id: {file_id}")
            # Try to get the file name from Drive before deleting
            try:
                from apis import gdrive_upload
                print(f"[collect_and_cleanup_collection] Connecting to Google Drive service...")
                service = gdrive_upload._get_service()
                print(f"[collect_and_cleanup_collection] Fetching file metadata for file_id: {file_id}")
                file_metadata = service.files().get(fileId=file_id, fields='name').execute()
                file_name = file_metadata.get('name', '')
                print(f"[collect_and_cleanup_collection] Google Drive file name: {file_name}")
                # Remove extension for base name
                base_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
                print(f"[collect_and_cleanup_collection] Base name for QR/MASTER search: {base_name}")
                # Prepare QR and MASTER file names
                qr_name = f"{base_name}-QR.png"
                master_name = f"{base_name}-MASTER.png"
                print(f"[collect_and_cleanup_collection] Looking for QR file: {qr_name}")
                print(f"[collect_and_cleanup_collection] Looking for MASTER file: {master_name}")
                # Find QR and MASTER folders
                root_id = os.getenv('GDRIVE_QR_FOLDER_ID') or gdrive_upload._get_or_create_folder(service, 'QRCards')
                print(f"[collect_and_cleanup_collection] Using root folder id: {root_id}")
                qr_folder = gdrive_upload._get_or_create_folder(service, 'QR', root_id)
                print(f"[collect_and_cleanup_collection] Using QR folder id: {qr_folder}")
                master_folder = gdrive_upload._get_or_create_folder(service, 'Masters', root_id)
                print(f"[collect_and_cleanup_collection] Using Masters folder id: {master_folder}")
                # Search for QR file in QR folder
                qr_query = f"name='{qr_name}' and '{qr_folder}' in parents and trashed=false"
                print(f"[collect_and_cleanup_collection] Searching for QR file with query: {qr_query}")
                qr_files = service.files().list(q=qr_query, fields='files(id)').execute().get('files', [])
                print(f"[collect_and_cleanup_collection] Found {len(qr_files)} QR file(s) to delete.")
                for f in qr_files:
                    print(f"[collect_and_cleanup_collection] Deleting QR file: {qr_name} ({f['id']})")
                    gdrive_upload.delete_gdrive_file_by_id(f['id'])
                # Search for MASTER file in Masters folder (and subfolders)
                master_query = f"name='{master_name}' and trashed=false"
                print(f"[collect_and_cleanup_collection] Searching for MASTER file with query: {master_query}")
                master_files = service.files().list(q=master_query, fields='files(id, parents)').execute().get('files', [])
                print(f"[collect_and_cleanup_collection] Found {len(master_files)} MASTER file(s) to delete.")
                for f in master_files:
                    # Optionally, check if parent is under Masters folder
                    print(f"[collect_and_cleanup_collection] Deleting MASTER file: {master_name} ({f['id']})")
                    gdrive_upload.delete_gdrive_file_by_id(f['id'])
            except Exception as e:
                print(f"[collect_and_cleanup_collection] Error checking/deleting QR/MASTER files: {e}")
            print(f"[collect_and_cleanup_collection] Deleting original file_id: {file_id}")
            delete_gdrive_file_by_id(file_id)
    print("[collect_and_cleanup_collection] Saving collectionUser and updating visitor collections.")
    collectionUser.save()
    visitorUser.visitorCollections.add(collectionUser)
    serializedData = collectionUser.serialize()
    print("[collect_and_cleanup_collection] Returning serialized data.")
    return serializedData





# All place Fetching
# @api_view(['PUT'])
def showAllPlaces(request):
    from .models import PlaceProfile
    from django.core import serializers

    placeList = PlaceProfile.objects.all()
    serialized_data = serializers.serialize('json', placeList, fields=('id', 'placeName'))
    # data = {"placedata":{"placedatalist":serialized_data}}
    data = {"placedata": {"placedatalist": json.loads(serialized_data)}}
    # return HttpResponse(json.dumps(placeList), content_type="application/json")
    return HttpResponse(json.dumps(data), content_type="application/json")
    # return HttpResponse(data, content_type="application/json")
    # return render(request, 'garden/places.html', {'places': placeList})

# all resorts in the specified place
def placeResorts(request, placeID=None): # accept data['placeID']
    from .models import PlaceProfile
    from .models import resortItem
    data = json.loads(request.body)
    if placeID is None:
        placeItem = data['placeID']
    else:
        placeItem = placeID
    placeToSearch = PlaceProfile.objects.get(id=placeItem)
    placeList = resortItem.objects.filter(place=placeToSearch)
    return HttpResponse(json.dumps(placeList), content_type="application/json")




def viewCollection(request):
    from .models import Collection  
    collectionList = Collection.objects.all()
    
    # collectionList = Collection.objects.filter(collectionIsCollected=True)
    # collectionList = Collection.objects.filter(collectionIsCollected=False)
    # print('Collection LISTS? /////////\n\n\n\n',collectionList)
    # collectionList = Collection.objects.filter(collectionIsCollected__in=[False])
    return render(request, 'garden/qr_images.html', {'collections': collectionList})


@api_view(['PUT'])
def viewPlaces(request):
    

    result = {

        'data': 'result data'
    }

    return HttpResponse(json.dumps(result), content_type="application/json")


@api_view(['PUT'])
@csrf_exempt
def visitorModel(request):
    # TODO
    print('Triggered')
    if request.method == 'PUT':
        import json
        from .models import Visitor
        from django.http import HttpResponse

        from pprint import pprint
        data = json.loads(request.body)
        visit = Visitor.objects.get_or_create(
            visitorName=data['username'], visitorID=data['userID'])[0]
        serializedData = visit.serialize()
        
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

        return HttpResponse(json.dumps(data), content_type="application/json")

    return 'It is verified'
    if request.method == 'POST':
        data = json.loads(request.body)
        visitorID = data.get('visitorID')
        visitorName = data.get('visitorName')
        # Check if Visitor has already same name
        if Visitor.objects.get(visitorName=data.get('visitorName'), visitorID=data.get('visitorID')) == None:
            # Create New Visitor Object
            visitor = Visitor.objects.create(visitorName=data.get(
                'visitorName'), visitorID=data.get('visitorID'))

    return HttpResponse(json.dumps(visitor), content_type="application/json")

def registerAllImage(request):
    from apis.upload_imbb import get_uploaded_image_urls
    from .forms import ProvinceForm, CollectionForm, PlaceProfileForm, VisitorForm

    cform = CollectionForm(request.POST)

    if cform.is_valid():
        customTitlerequest = request.POST.get('collectioncustomTitle')
        files = request.FILES.getlist('images')

        if not files:
            return render(
                request,
                'garden/registration.html',
                {
                    'ProvinceForm': ProvinceForm(),
                    'CollectionForm': CollectionForm(),
                    'PlaceProfileForm': PlaceProfileForm(),
                    'VisitorForm': VisitorForm(),
                    'message': 'Please upload at least one image.'
                }
            )

        # Step 1: upload all submitted files and get remote URLs
        image_urls = get_uploaded_image_urls(files)

        if not image_urls:
            return render(
                request,
                'garden/registration.html',
                {
                    'ProvinceForm': ProvinceForm(),
                    'CollectionForm': CollectionForm(),
                    'PlaceProfileForm': PlaceProfileForm(),
                    'VisitorForm': VisitorForm(),
                    'message': 'No image was uploaded successfully.'
                }
            )

        # Step 2: create or get the CollectionGroup
        from .models import CollectionGroup
        # Use the inputted collection name as the group name
        group_name = request.POST.get('collectionName') or request.POST.get('collectionGroupName') or customTitlerequest or 'Default Group'
        collection_group, _ = CollectionGroup.objects.get_or_create(name=group_name)

        # Step 3: create one collection per image and add to group
        for idx, img_url in enumerate(image_urls):
            collection_form = CollectionForm(request.POST)
            collection = collection_form.save(commit=False)
            collection.collectionUniqueID = UniqueGenerator()
            collection.collectionPicture = img_url
            # fallback if needed
            if not collection.collectionPicture:
                collection.collectionPicture = collection.collectionPlace.placePicture
            collection.save()
            # Ensure ManyToMany fields from the form (e.g. touristSpot) are persisted
            collection_form.save_m2m()
            # Add collection to group
            collection_group.collections.add(collection)
            # generate QR code for this collection
            CreateQRCode(
                request, 
                collection, 
                'https://www.upload-apk.com/jGKFBqod1LMjQry',
                customTitle=customTitlerequest
            )

        # After all collections are created, fetch all collections and their fields
        # Only fetch collections in the current group
        all_collections = collection_group.collections.all()
        # Prepare a list of dicts with all fields for each collection
        collections_data = []
        for col in all_collections:
            # Use model_to_dict if available, else manually extract fields
            try:
                from django.forms.models import model_to_dict
                col_dict = model_to_dict(col)
            except Exception:
                col_dict = {field.name: getattr(col, field.name) for field in col._meta.fields}
            collections_data.append(col_dict)

        return render(request, 'garden/qr_images.html', {'collections': all_collections, 'collections_data': collections_data})

    return render(
        request,
        'garden/registration.html',
        {
            'ProvinceForm': ProvinceForm(),
            'CollectionForm': CollectionForm(),
            'PlaceProfileForm': PlaceProfileForm(),
            'VisitorForm': VisitorForm(),
            'message': 'Collection form is invalid.'
        }
    )

        
    # for i in range(int(request.POST.get('collectionCount'))):

    #     collection = CollectionForm(request.POST)
    #     collection = collection.save()

    #     collection.collectionUniqueID = UniqueGenerator()

    #     # assign image i from image_urls
    #     if i < len(image_urls):
    #         collection.collectionPicture = image_urls[i]
    #     else:
    #         collection.collectionPicture = collection.collectionPlace.placePicture   # last option fallback

    #     collection.save()

    #     CreateQRCode(request, collection, 'https://www.upload-apk.com/jGKFBqod1LMjQry', customTitle=customTitlerequest)


def registrationPage(request):
    from django.http import HttpResponseRedirect
    # from time import sleep
    from .forms import ProvinceForm, CollectionForm, PlaceProfileForm,VisitorForm

    # Always define forms for rendering
    pform = ProvinceForm()
    ppform = PlaceProfileForm()
    vform = VisitorForm()
    cform = CollectionForm()

    message = None
    if request.method == 'POST':
        print("[registrationPage] POST received")
        form_type = request.POST.get('form_type')
        print(f"[registrationPage] form_type: {form_type}")
        if form_type == 'province':
            pform = ProvinceForm(request.POST)
            print(f"[registrationPage] ProvinceForm data: {request.POST}")
            if pform.is_valid():
                print("[registrationPage] ProvinceForm is valid")
                from .models import Province
                isExisting = Province.objects.filter(provinceName=pform.instance.provinceName).exists()
                print(f"[registrationPage] Province exists: {isExisting}")
                if not isExisting:
                    pform.save()
                    print("[registrationPage] Province saved")
                    return HttpResponseRedirect(reverse("garden:registrationpage"))
                else:
                    message = f"Province '{pform.instance.provinceName}' already exists. Try a new name."
                    print(f"[registrationPage] {message}")
            else:
                message = f"Province form error: {pform.errors.as_text()}"
                print(f"[registrationPage] {message}")
        elif form_type == 'place':
            ppform = PlaceProfileForm(request.POST, request.FILES)
            print(f"[registrationPage] PlaceProfileForm data: {request.POST}, FILES: {request.FILES}")
            if ppform.is_valid():
                print("[registrationPage] PlaceProfileForm is valid")
                from .models import PlaceProfile
                isExisting = PlaceProfile.objects.filter(placeName=ppform.instance.placeName).exists()
                print(f"[registrationPage] PlaceProfile exists: {isExisting}")
                if not isExisting:
                    # Upload image to Cloudinary if provided
                    if 'placePicture' in request.FILES:
                        image_file = request.FILES['placePicture']
                        public_id = f"place_{ppform.instance.placeName.replace(' ', '_')}"
                        folder_name = ppform.instance.placeName.replace(' ', '_')
                        try:
                            print("[registrationPage] Uploading to Cloudinary (direct)...")
                            result = cloudinary.uploader.upload(
                                image_file,
                                public_id=public_id,
                                folder=folder_name,
                                overwrite=True
                            )
                            cloudinary_url = result.get('secure_url')
                            ppform.instance.placePicture = cloudinary_url
                            print(f"[registrationPage] Cloudinary upload success: {cloudinary_url}")
                        except Exception as e:
                            message = f"Error uploading to Cloudinary: {e}"
                            print(f"[registrationPage] {message}")
                            return render(request, 'garden/registration.html', {
                                'ProvinceForm': pform,
                                'CollectionForm': cform,
                                'PlaceProfileForm': ppform,
                                'VisitorForm': vform,
                                'message': message
                            })
                    ppform.save()
                    print("[registrationPage] PlaceProfile saved")
                    return HttpResponseRedirect(reverse("garden:registrationpage"))
                else:
                    message = f"Place '{ppform.instance.placeName}' already exists. Try a new name."
                    print(f"[registrationPage] {message}")
            else:
                message = f"Place form error: {ppform.errors.as_text()}"
                print(f"[registrationPage] {message}")
        elif form_type == 'visitor':
            vform = VisitorForm(request.POST)
            print(f"[registrationPage] VisitorForm data: {request.POST}")
            if vform.is_valid():
                print("[registrationPage] VisitorForm is valid")
                from .models import Visitor
                isExisting = Visitor.objects.filter(
                    visitorName=vform.instance.visitorName).exists()
                print(f"[registrationPage] Visitor exists: {isExisting}")
                if not isExisting:
                    vform.save()
                    print("[registrationPage] Visitor saved")
                    return HttpResponseRedirect(reverse("garden:registrationpage"))
                else:
                    message = f"Visitor '{vform.instance.visitorName}' already exists. Try a new name."
                    print(f"[registrationPage] {message}")
            else:
                message = f"Visitor form error: {vform.errors.as_text()}"
                print(f"[registrationPage] {message}")
        # Note: Collection form is handled by a different URL/action

        forms = {
            'ProvinceForm': pform,
            'CollectionForm': cform,
            'PlaceProfileForm': ppform,
            'VisitorForm': vform,
            'message': message
        }
        print(f"[registrationPage] Rendering form with message: {message}")
        return render(request, 'garden/registration.html', forms)
    # Always render forms, with possibly bound forms after POST
    # NOTE: To ensure form_type is present, add this to your HTML form:
    # <input type="hidden" name="form_type" value="province"> (or "place" or "visitor")
    # Example for province form:
    # <form method="post">{% csrf_token %}
    #   <input type="hidden" name="form_type" value="province">
    #   ...fields...
    # </form>
    forms = {
        'ProvinceForm': pform,
        'CollectionForm': cform,
        'PlaceProfileForm': ppform,
        'VisitorForm': vform,
        'message': message
    }
    print("[registrationPage] GET or initial render")
    return render(request, 'garden/registration.html', forms)


@csrf_exempt
def upload_images(request):
    print('uploading images...')
    """Handle multipart image uploads, save to IMGBB (using existing helper), and create Memory entries."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # grab files
    files = request.FILES.getlist('images')
    if not files:
        return JsonResponse({'error': 'No files uploaded'}, status=400)

    image_field = request.POST.get('imageField', '')
    username = request.POST.get('username')
    userID = request.POST.get('userID')
    collectionUniqueID = request.POST.get('collectionUniqueID')
    print(f"image_field: {image_field}")
    print(f"username: {username}")
    print(f"userID: {userID}")
    print(f"collectionUniqueID: {collectionUniqueID}")

    if not username or not userID:
        return JsonResponse({'error': 'username and userID required'}, status=400)

    try:
        visitor = Visitor.objects.get(visitorName=username, visitorID=userID)
    except Visitor.DoesNotExist:
        return JsonResponse({'error': 'Visitor not found'}, status=404)

    # use existing helper
    from webSchedule.utils import upload_to_imgbb

    saved = []
    for f in files:
        try:
            url = upload_to_imgbb(f)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

        # create Memory
        from .models import Memory, Collection
        mem = Memory.objects.create(memoryPicture=url, memoryAbout=image_field, memoryVisitor=visitor)
        # attach memory to collection if provided
        if collectionUniqueID:
            try:
                collection = Collection.objects.get(collectionUniqueID=collectionUniqueID)
                collection.collectionMemory.add(mem)
            except Collection.DoesNotExist:
                pass

        saved.append({'id': mem.id, 'url': url, 'about': mem.memoryAbout})

    return JsonResponse({'saved': saved}, status=201)




def UniqueGenerator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# header_img = create_wordart(collectionObj.collectionName)
# header_img.thumbnail((int(placeImage.width * 0.8), 200))
# header_x = (placeImage.width - header_img.width) // 2
# placeImage.paste(header_img, (header_x, 20), header_img)  # transparency preserved
# Creating Collection Cards almost done

def random_color():
    """Generate a random hex color."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def gradient_text(draw, text, font, position, size, colors,direction="horizontal"):
    # gradient_text(draw, text, font, (text_x, text_y), (text_w, text_h), ("#00FFFF", "#FF00FF"))
    text_w, text_h = size

    # --- Create smooth gradient without NumPy ---
    gradient_flat = []
    rand_scale = random.randint(0, 255)
    if direction == "horizontal":
        for y in range(text_h):
            for x in range(text_w):
                val = x / (text_w - 1) if text_w > 1 else 0
                fill_val = int(val * rand_scale)
                gradient_flat.append(fill_val)
    else:  # vertical
        for y in range(text_h):
            val = y / (text_h - 1) if text_h > 1 else 0
            for x in range(text_w):
                fill_val = int(val * rand_scale)
                gradient_flat.append(fill_val)

    # Convert to grayscale image
    gradient_img = Image.new("L", (text_w, text_h))
    gradient_img.putdata(gradient_flat)

    # Colorize the grayscale gradient → RGB gradient

    # colors = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    colors = (random_color(), random_color())
    colored_gradient = ImageOps.colorize(gradient_img, colors[0], colors[1])

    # Create text mask (white text on black)
    mask = Image.new("L", (text_w, text_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.text((0, 0), text, font=font, fill=255)

    return colored_gradient, mask
def get_random_font(font_dir="garden/assets/fonts", font_size=90):
    # Recursively list all .ttf and .otf files in folder and subfolders
    fonts = []
    for root, _, files in os.walk(font_dir):
        for file_name in files:
            if file_name.lower().endswith((".ttf", ".otf")):
                fonts.append(os.path.join(root, file_name))
    if not fonts:
        raise Exception("❌ No .ttf or .otf fonts found in the folder.")
    
    # Pick one random font
    font_path = random.choice(fonts)
    font_file = os.path.basename(font_path)

    print(f"🎨 Using font: {font_file}")
    return ImageFont.truetype(font_path, font_size)


def get_random_font_path(font_dir="garden/assets/fonts"):
    fonts = []
    for root, _, files in os.walk(font_dir):
        for file_name in files:
            if file_name.lower().endswith((".ttf", ".otf")):
                fonts.append(os.path.join(root, file_name))
    if not fonts:
        raise Exception("❌ No .ttf or .otf fonts found in the folder.")
    return random.choice(fonts)


def load_font_with_fallback(font_path, font_size):
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return ImageFont.truetype(
            'garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf',
            font_size,
        )

def create_wordart(
    text: str,
    width=800,
    height=600,
    text_outline_color=(0, 0, 0, 255),
    font_size=90,
):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_text_width = int(width * 0.92)
    max_text_height = int(height * 0.90)
    min_font_size = 18
    preferred_font_size = max(min_font_size, int(font_size))
    max_font_size = max(preferred_font_size, int(font_size * 1.7))

    wrapped_lines = [text or ""]
    font_path = get_random_font_path()

    def fits(font_size):
        test_font = load_font_with_fallback(font_path, font_size)
        test_lines = wrap_text_by_width(draw, text or "", test_font, max_text_width)
        test_wrapped = "\n".join(test_lines)
        test_spacing = max(6, int(font_size * 0.20))
        test_bbox = draw.multiline_textbbox((0, 0), test_wrapped, font=test_font, spacing=test_spacing)
        test_w = test_bbox[2] - test_bbox[0]
        test_h = test_bbox[3] - test_bbox[1]
        return test_w <= max_text_width and test_h <= max_text_height, test_font, test_lines, test_spacing

    chosen_font_size = min_font_size
    font = load_font_with_fallback(font_path, chosen_font_size)
    line_spacing = max(6, int(chosen_font_size * 0.20))

    low, high = min_font_size, max_font_size
    best = None
    while low <= high:
        mid = (low + high) // 2
        ok, test_font, test_lines, test_spacing = fits(mid)
        if ok:
            best = (mid, test_font, test_lines, test_spacing)
            low = mid + 1
        else:
            high = mid - 1

    if best is not None:
        chosen_font_size, font, wrapped_lines, line_spacing = best
    else:
        # Emergency fallback for extreme cases
        for fallback_size in range(min_font_size, 9, -2):
            ok, test_font, test_lines, test_spacing = fits(fallback_size)
            if ok:
                chosen_font_size, font, wrapped_lines, line_spacing = (
                    fallback_size,
                    test_font,
                    test_lines,
                    test_spacing,
                )
                break

    wrapped_text = "\n".join(wrapped_lines)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=line_spacing)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = max(0, (width - text_w) // 2)
    text_y = max(0, (height - text_h) // 2)


    # --- Outline ---
    outline = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(outline)
    # for dx in range(-2, 3):
    #     for dy in range(-2, 3):
    #         odraw.text((text_x + dx, text_y + dy), text, font=font, fill=(text_outline_color))
    fill = tuple(random.randint(0, 255) for _ in range(3)) + (255,)
    # outline_thickness = 5
    outline_thickness = random.randint(1, 5)
    # for dx in range(-3, 4):
    for dx in range(-outline_thickness, outline_thickness + 1):
        # for dy in range(-3, 4):
        for dy in range(-outline_thickness, outline_thickness + 1):
            odraw.multiline_text(
                (text_x + dx, text_y + dy),
                wrapped_text,
                font=font,
                fill=fill,
                spacing=line_spacing,
                align="center",
            )
    img = Image.alpha_composite(img, outline)

    # --- Main text ---
    draw = ImageDraw.Draw(img)
    draw.multiline_text(
        (text_x + 2, text_y + 2),
        wrapped_text,
        font=font,
        fill=(0, 0, 0, 160),
        spacing=line_spacing,
        align="center",
    )
    draw.multiline_text(
        (text_x, text_y),
        wrapped_text,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=line_spacing,
        align="center",
    )

    return img


def wrap_text_by_width(draw, text, font, max_width):
    if not text:
        return [""]

    all_lines = []
    paragraphs = str(text).splitlines() or [""]

    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            all_lines.append("")
            continue

        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            candidate_w = draw.textbbox((0, 0), candidate, font=font)[2]
            if candidate_w <= max_width:
                current = candidate
                continue

            if current:
                all_lines.append(current)
                current = ""

            # Split very long words that exceed max width.
            if draw.textbbox((0, 0), word, font=font)[2] > max_width:
                chunk = ""
                for ch in word:
                    chunk_try = chunk + ch
                    chunk_w = draw.textbbox((0, 0), chunk_try, font=font)[2]
                    if chunk_w <= max_width or not chunk:
                        chunk = chunk_try
                    else:
                        all_lines.append(chunk)
                        chunk = ch
                current = chunk
            else:
                current = word

        if current:
            all_lines.append(current)

    return all_lines or [""]

def CreateQRCode(request, collectionObj, appDownloadLink, customTitle=""):
    # TODO Add an argument for Theme and File Location of the Head Title
    """
    # TODO Head title Image get from 
    # https://www.textstudio.com/logo/vaporwave-text-effect-2183
    save as .png then put value on CollectionObject.collectionImageIndicator
    """
    # TODO Create a QR code that will direct to downloading app
    # TODO all above
    # Notes: Image Dimension should be 1000 × 669
    import qrcode
    from PIL import Image, ImageFont, ImageDraw, ImageEnhance
    from PIL import ImageDraw, ImageFont, ImageFilter
    import os
    import requests
    from io import BytesIO
    import json
    # read more here
    # https://auth0.com/blog/image-processing-in-python-with-pillow/#Resizing-Images
    # Generate a high-res master for printing, but upload a smaller version to save storage.
    OUTPUT_MAX_PX = 2000
    UPLOAD_MAX_PX = 900

    # Build QR with a smaller quiet-zone (border). Note: making this too small can hurt scan reliability.
    qr_builder = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,  # default is 4; 2 is ~50% smaller
    )
    qr_builder.add_data(f'https://paratara.com/garden/home/{collectionObj.collectionUniqueID}')
    qr_builder.make(fit=True)
    qrImage = qr_builder.make_image(fill_color="black", back_color="white")
    response = requests.get(collectionObj.collectionPicture)
    placeImage = Image.open(BytesIO(response.content))
    placeImage = ImageOps.exif_transpose(placeImage).convert("RGBA")
    # RESIZE (keep aspect) — generate a larger base image for better print quality.
    placeImage.thumbnail((OUTPUT_MAX_PX, OUTPUT_MAX_PX), Image.Resampling.LANCZOS)

    # Scale UI elements relative to the historical 800px design.
    scale = max(0.5, min(placeImage.width, placeImage.height) / 800.0)
    # qr_toSize = int(placeImage.height/2.5)
    # qr_toSize = int(placeImage.width/2.5)
    if placeImage.width > placeImage.height:
        qr_toSize = int(placeImage.height / 2.75)
    else:
        qr_toSize = int(placeImage.width / 2.75)

    # Make the QR 10% smaller
    qr_toSize = max(1, int(qr_toSize * 0.90))
    # Resize QR with NEAREST to keep edges crisp (avoid blur from anti-aliasing).
    qrImage = qrImage.convert("RGBA")
    qrImage = qrImage.resize((qr_toSize, qr_toSize), resample=Image.Resampling.NEAREST)
    # Enhancing the Image
    placeImage = ImageEnhance.Sharpness(placeImage)
    placeImage = placeImage.enhance(1.5)
    # adding that margin
    margin = ImageDraw.Draw(placeImage)
    w, h = 220, 190

    shape = [(0, 0), (placeImage.width, placeImage.height)]

    # Finish adding margin
    # Adding Texts
    # Subtitle/body text: use a clean/modern readable font.
    # Fallback to the previous font if this file is missing.
    try:
        subtitle_font = get_random_font(font_size=max(13, int(18 * scale)))
    except Exception:
        subtitle_font = ImageFont.truetype(
            'garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf',
            max(12, int(17 * scale)),
        )
    subtitle_canvas = ImageDraw.Draw(placeImage)
    
    # End Adding Texts
    # To Convert To Pil Image
    # Save QR image in memory (uploaded to Drive later)
    qr_stream = BytesIO()
    qrImage.save(qr_stream, format='PNG')
    qr_stream.seek(0)
    # qrImage.crop((40, 40, 40, 40))  # NOTE: crop would need a new bbox and assignment
    # placeImage.crop(box)
    # Add stronger edge margin around QR and place it on the opposite side.
    qr_padding = max(16, int(24 * scale))
    qr_position = (
        qr_padding,
        (placeImage.height - qrImage.height - qr_padding),
    )
    placeImage.paste(qrImage, qr_position) 
    #  Logo
    gardenLogo = Image.open('garden/assets/gardenlogo.png').convert("RGBA")
    garden_logo_size = int(qr_toSize/2)
    gardenLogo.thumbnail((garden_logo_size, garden_logo_size))
    gardenLogoHeight = placeImage.height - (qrImage.height+(gardenLogo.height+10))
    gardenLogoWidth = placeImage.width-80
    # Apple and android Logo
    appleLogo = Image.open('garden/assets/apple_logo.png').convert("RGBA")
    androidLogo = Image.open('garden/assets/android_logo.png').convert("RGBA")

    icon_logos = int(gardenLogo.height/3)
    androidLogo.thumbnail((icon_logos, icon_logos))
    appleLogo.thumbnail((icon_logos, icon_logos))

    # LOGO HERE
    # placeImage.paste(gardenLogo, (gardenLogoWidth + 15, gardenLogoHeight), gardenLogo)
    # placeImage.paste(appleLogo, (gardenLogoWidth - (gardenLogo.width + 5),gardenLogoHeight + icon_logos+10), appleLogo)
    # placeImage.paste(androidLogo, (gardenLogoWidth -(gardenLogo.width - 15), gardenLogoHeight + icon_logos+10), androidLogo)

    subtitle_canvas = ImageDraw.Draw(placeImage)
    try:
        downloadFont = get_random_font(font_size=max(10, int(13 * scale)))
    except Exception:
        downloadFont = ImageFont.truetype(
            'garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf',
            max(10, int(13 * scale)),
        )
    # subtitle_canvas.text((gardenLogoWidth - (gardenLogo.width - 44), gardenLogoHeight - 10), text='     Download\nGarden to Scan',fill=new_color, font=downloadFont, anchor='mm')
    # subtitle_canvas.text((gardenLogoWidth - (gardenLogo.width - 17), gardenLogoHeight + 20), text='     Download\nGarden to Scan',fill=new_color, font=downloadFont, anchor='mm')

    # End Logo

    # TITLE PAGE
    # ART GENERATOR for Title
    # Create a Word Art then save on the location
    # response = requests.get(collectionObj.collectionImageIndicator)
    # titleArt = Image.open(BytesIO(response.content))
    # # titleArt = Image.open(
    # #     f'garden/assets/titleImage/{collectionObj.collectionImageIndicator}.png')
    # title_art_size = int(placeImage.width/2)
    # titleArt.thumbnail((title_art_size, title_art_size))
    # titleArt = create_wordart(collectionObj.collectionPlace.placeName + '\n' + collectionObj.collectionPlace.placeProvince)
    customTitle
    if customTitle != "":
        title_text = customTitle.replace("\\n", "\n")
    else:
        title_text = f"{collectionObj.collectionPlace.placeName}\n{collectionObj.collectionPlace.placeProvince}"

    # Add extra vertical padding to avoid clipping
    wordart_height = max(240, int(placeImage.height * 0.30))
    # Add extra horizontal padding to prevent clipping from outlines/effects
    base_title_width = int(placeImage.width * 0.9)
    horizontal_padding = int(base_title_width * 0.15)  # 15% extra padding
    max_title_width = base_title_width - 2 * horizontal_padding
    font_path = get_random_font_path()
    font_size = int(max(60, int(90 * scale)) * 0.95)
    min_font_size = 18
    temp_img = Image.new("RGBA", (max_title_width, 500), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    while font_size >= min_font_size:
        temp_font = load_font_with_fallback(font_path, font_size)
        wrapped_lines = wrap_text_by_width(temp_draw, title_text, temp_font, max_title_width)
        wrapped_text = "\n".join(wrapped_lines)
        line_spacing = max(6, int(font_size * 0.20))
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=temp_font, spacing=line_spacing)
        text_w = bbox[2] - bbox[0]
        if text_w <= max_title_width:
            break
        font_size -= 2
    text_h = bbox[3] - bbox[1]
    padded_height = int(text_h * 1.9)
    padded_height = max(padded_height, 80)
    # Create the wordart image with extra horizontal padding
    wordart_width = max_title_width + 2 * horizontal_padding
    titleArt = create_wordart(
        title_text,
        width=wordart_width,
        height=padded_height,
        font_size=font_size,
    )
    # Center the wordart on the main image
    title_art_width_position = int(placeImage.width / 2) - int(titleArt.width / 2)
    top_margin = max(20, int(placeImage.height * 0.025))
    placeImage.paste(titleArt, (title_art_width_position, top_margin), titleArt)
    if collectionObj.collectionTheme == None:
        # new_color = get_dominant_color(placeImage)
        new_color = get_contrast_color(placeImage)
    else :
        new_color = collectionObj.collectionTheme

    COLOR_MAP = {
        "black": "#000000",
        "gold": "#FFD700",
        "champagne": "#F7E7CE",
        "emerald": "#50C878",
        "sapphire": "#0F52BA",
        "ruby": "#E0115F",
        "rose-gold": "#B76E79",
        "platinum": "#E5E4E2",
        "pearl": "#FDEEF4",
        "bronze": "#CD7F32",
    }

    # Preserve hex colors (e.g. "#FFFFFF", "#FFD700") and only map named themes.
    if isinstance(new_color, str):
        theme_key = new_color.strip().lower()
        if theme_key in COLOR_MAP:
            new_color = COLOR_MAP[theme_key]
        elif theme_key.startswith("#"):
            new_color = theme_key
        else:
            new_color = "#000000"
    border_w = max(6, int(10 * scale))
    margin.rectangle(shape, fill=None, outline=new_color, width=border_w)

    # Keep text simple: no description and no text background box.
    text_secondary = "#FFFFFF"

    footer_text = f"{collectionObj.collectionPlace.placeName} {collectionObj.collectionPlace.placeProvince.provinceName}".strip()
    footer_x = placeImage.width - int(placeImage.width * 0.025)  # small right margin
    # Move these labels higher from the bottom and keep clear of the border
    small_margin_bottm = placeImage.height - border_w - max(15, int(35 * scale))

    subtitle_canvas.text(
        (footer_x, small_margin_bottm),
        text=footer_text,
        fill=text_secondary,
        font=subtitle_font,
        anchor='rs',  # right, baseline
        stroke_width=max(1, int(2 * scale)),
        stroke_fill="#000000",
    )
    # Removed Collection Name
#     subtitle_canvas.text(
#     (small_margin_left, small_margin_bottm + max(22, int(30 * scale))),
#     text=collectionObj.collectionName,
#     fill=new_color,
#     font=subtitle_font,
#     anchor='ls'  # left, baseline
# )

    # savedImage = placeImage.save()
    # savedImage.geth
    """
    ///////       ////
   ///    //    //  //
   ///    //   //  //
   ///    //   //  //
   ///   //    //  //
   //////       ///
    # Download new fonts here
    # https://www.fontspace.com/collection
    # garden/assets/fonts
    from os import listdir
    import random
    xpath = 'garden/assets/fonts/'
    titleFonts = []
    x = listdir(xpath)
    for xx in x:
        print('----')
        for xxx in listdir(xpath+xx):
            if len(xxx) > 12:
                titleFonts.append(xpath+'/'+xx+'/'+xxx)
    title_canvas = ImageDraw.Draw(placeImage)
    title_canvas_text = collectionObj.collectionPlace.placeName
    title_canvas_font = ImageFont.truetype(
        titleFonts[random.randint(0, len(titleFonts))-1], 100, encoding='unic', layout_engine='Layout')
    title_canvas.text((placeImage.width/2, 110), text=title_canvas_text,
                      fill=collectionObj.collectionTheme, font=title_canvas_font, anchor='mm')
    # END TITLE PAGE
    """
 

    # Build high-res master in memory (for print, 300 DPI)
    master_stream = BytesIO()
    placeImage.save(master_stream, format='PNG', dpi=(300, 300))
    master_stream.seek(0)

    # Build web-optimised image in memory
    upload_img = placeImage.copy()
    upload_img.thumbnail((UPLOAD_MAX_PX, UPLOAD_MAX_PX), Image.Resampling.LANCZOS)
    web_stream = BytesIO()
    upload_img.save(web_stream, format='PNG', optimize=True, compress_level=9)
    web_stream.seek(0)

    # Save under Django MEDIA_ROOT/image_cards/
    from django.conf import settings
    media_base = os.path.join(settings.MEDIA_ROOT, 'image_cards')
    qr_dir = os.path.join(media_base, 'qr')
    web_dir = os.path.join(media_base, 'web')
    master_dir = os.path.join(media_base, 'master')
    os.makedirs(qr_dir, exist_ok=True)
    os.makedirs(web_dir, exist_ok=True)
    os.makedirs(master_dir, exist_ok=True)

    name_slug = f"{collectionObj.collectionName}-{collectionObj.collectionUniqueID}"
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    print(f"[CreateQRCode] Saving images for collection: {name_slug} at {timestamp}")


    # Save only master image
    master_filename = f"{name_slug}-master.png"
    master_path = os.path.join(master_dir, master_filename)
    print(f"[CreateQRCode] Saving master image to: {master_path}")
    placeImage.save(master_path, format='PNG', dpi=(300, 300))

    # Set the collection's Google Drive URL to the relative media path (for Django)
    rel_master_path = os.path.relpath(master_path, settings.MEDIA_ROOT)
    print(f"[CreateQRCode] Setting collectionGoogleDriveURL to: {rel_master_path}")
    collectionObj.collectionGoogleDriveURL = rel_master_path
    # Always set collectionLocalFile to the uploaded Cloudinary image (collectionPicture)
    print(f"[CreateQRCode] Setting collectionLocalFile to collectionPicture: {collectionObj.collectionPicture}")
    collectionObj.collectionLocalFile = collectionObj.collectionPicture

    collectionObj.save()
    # collectionPicture = models.URLField(null=True, blank=True)


def get_dominant_color(pil_img):
    import PIL.ImageOps
    from PIL import Image
    img = pil_img.copy()
    img = img.convert("RGBA")
    img = img.resize((1, 1), resample=0)
    r, g, b, a = img.split()
    rgb_image = Image.merge('RGB', (r, g, b))
    inverted_image = PIL.ImageOps.invert(rgb_image)
    r2, g2, b2 = inverted_image.split()
    final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
    contranst_color = final_transparent_image.getpixel((0, 0))
    hex_value = "#{:02x}{:02x}{:02x}".format(*contranst_color[:3])
    return f'{hex_value}'
def get_contrast_color(pil_img, vivid=False):
    """Return a high-contrast color (black or white, or vivid opposite) from an image."""
    # Resize to 1x1 to get average color
    img = pil_img.convert("RGB").resize((1, 1))
    r, g, b = img.getpixel((0, 0))
    # Calculate luminance (perceived brightness)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    if vivid:
        # Generate opposite vivid color
        inv_r, inv_g, inv_b = 255 - r, 255 - g, 255 - b
        return "#{:02x}{:02x}{:02x}".format(inv_r, inv_g, inv_b)
    else:
        # Return black or white for max contrast
        return "#000000" if luminance > 0.5 else "#FFFFFF"

@csrf_exempt
def check_visitor(request):
    if request.method == 'PUT':
        data = json.loads(request.body)
        username = data.get('username')
        if not username:
            return JsonResponse({'error': 'Username required'}, status=400)
        exists = Visitor.objects.filter(visitorName=username).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def generate_a4_collage(request):
    if request.method == 'POST':
        try:
            import os
            from django.conf import settings
            from garden.a4_collage_util import create_a4_collage_from_master_images
            file_path = create_a4_collage_from_master_images()
            if file_path:
                # file_path is expected to be relative to MEDIA_ROOT or absolute
                # Get filename only
                filename = os.path.basename(file_path)
                url = settings.MEDIA_URL.rstrip('/') + '/image_cards/a4_collages/' + filename
                return JsonResponse({'success': True, 'file_path': url})
            else:
                return JsonResponse({'success': False, 'error': 'No images found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

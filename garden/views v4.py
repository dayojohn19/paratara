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
from PIL import ImageFont

# Cloudinary (optional) — used for uploading generated images
try:
    import cloudinary
    import cloudinary.uploader
except Exception:
    cloudinary = None

from django.core import signing
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.db.models import Count  

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
        serializedData = collectionUser.serialize()
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

    visitorUser = Visitor.objects.get_or_create(visitorName=user, visitorID=userID)[0]
    collectionUser.collectionCollector = visitorUser
    collectionUser.collectionIsCollected = True
    collectionUser.save()
    visitorUser.visitorCollections.add(collectionUser)
    serializedData = collectionUser.serialize()
    return HttpResponse(json.dumps(serializedData), content_type="application/json")





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
    # collectionList = Collection.objects.all()
    # collectionList = Collection.objects.filter(collectionIsCollected=True)
    # collectionList = Collection.objects.filter(collectionIsCollected=False)
    # print('Collection LISTS? /////////\n\n\n\n',collectionList)
    collectionList = Collection.objects.filter(collectionIsCollected__in=[False])
    return render(request, 'garden/qr_images.html', {'collection_items': collectionList})


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
    from apis.upload_imbb import get_all_image_urls
    from .forms import CollectionForm

    cform = CollectionForm(request.POST)
    if cform.is_valid():
        customTitlerequest = request.POST.get('collectioncustomTitle')

        # Step 1: upload all images and get their URLs
        image_urls = get_all_image_urls()

        # Step 2: create one collection per image
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

            # generate QR code for this collection
            CreateQRCode(
                request, 
                collection, 
                'https://www.upload-apk.com/jGKFBqod1LMjQry',
                customTitle=customTitlerequest
            )

        from .models import Collection
        return render(request, 'garden/qr_images.html', {'collections': Collection.objects.all()})

        
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
    if request.method == 'POST':

        pform = ProvinceForm(request.POST)
        if pform.is_valid():
            from .models import Province
            isExisting = Province.objects.filter(provinceName=pform.instance.provinceName).exists()
            if not isExisting:
                pform.save()
                return HttpResponseRedirect(reverse("garden:registrationpage"))

        cform = CollectionForm(request.POST)
        # print('\n Checking Picture: ', cform.cleaned_data['collectionPicture'])
        if cform.is_valid():
            
            customTitlerequest = request.POST.get('collectioncustomTitle')
            for i in range(int(request.POST.get('collectionCount'))):
                collection = CollectionForm(request.POST)
                collection = collection.save()
                collection.collectionUniqueID = UniqueGenerator()
                if collection.collectionPicture == None:
                    collection.collectionPicture = collection.collectionPlace.placePicture
                print('\n\n\n gettingLink https://1.png Collection Picture: ',collection.collectionPicture,'\n\n')
                collection.save()
                # download link
                CreateQRCode(request, collection, 'https://www.upload-apk.com/jGKFBqod1LMjQry', customTitle = customTitlerequest)
                # CreateQRCode(request, collection, 'https://play.google.com/store/apps/details?id=com.garden.app# ')

                    # request, collection, 'https://dayojohn19.github.io/appDownloadLink.html# ')

            from .models import Collection
            return render(request, 'garden/qr_images.html', {'collections': Collection.objects.all()})
            # TODO change https/text.com to real link qr to download the app
        # return HttpResponseRedirect(reverse("garden:registrationpage"))

        ppform = PlaceProfileForm(request.POST)
        print('isppformValid')
        if ppform.is_valid():
            print(' ppformValid')
            from .models import PlaceProfile
            isExisting = PlaceProfile.objects.filter(placeName=ppform.instance.placeName).exists()
            if not isExisting:
                # ppform.instance.placeObject = ppform.instance.placeObject
                ppform.save()
                return HttpResponseRedirect(reverse("garden:registrationpage"))

        vform = VisitorForm(request.POST)
        if vform.is_valid():
            from .models import Visitor
            isExisting = Visitor.objects.filter(
                visitorName=vform.instance.visitorName).exists()



        pform = ProvinceForm(request.POST)
        print('isPformValid')
        if pform.is_valid():
            print("pformValid")
            from .models import Province
            isExisting = Province.objects.filter(
                provinceName=pform.instance.provinceName).exists()
            if not isExisting:
                pform.save()
                return HttpResponseRedirect(reverse("garden:registrationpage"))

        cform = CollectionForm(request.POST)
        # print('\n Checking Picture: ', cform.cleaned_data['collectionPicture'])
        print('Checking',cform.is_valid())
        if cform.is_valid():
            print("VALID")
            
            customTitlerequest = request.POST.get('collectioncustomTitle')
            for i in range(int(request.POST.get('collectionCount'))):
                print(f'\n\n\n Creating Number: \n          {i}\n\n\n --------------------------')
                collection = CollectionForm(request.POST)
                collection = collection.save()
                collection.collectionUniqueID = UniqueGenerator()
                if collection.collectionPicture == None:
                    collection.collectionPicture = collection.collectionPlace.placePicture
                print('\n\n\n gettingLink https://1.png Collection Picture: ',collection.collectionPicture,'\n\n')
                collection.save()
                # download link
                CreateQRCode(request, collection, 'https://www.upload-apk.com/jGKFBqod1LMjQry', customTitle = customTitlerequest)
                # CreateQRCode(request, collection, 'https://play.google.com/store/apps/details?id=com.garden.app# ')

                    # request, collection, 'https://dayojohn19.github.io/appDownloadLink.html# ')

            from .models import Collection
            return render(request, 'garden/qr_images.html', {'collections': Collection.objects.all()})
            # TODO change https/text.com to real link qr to download the app
        # return HttpResponseRedirect(reverse("garden:registrationpage"))

        ppform = PlaceProfileForm(request.POST)
        print('isppformValid')
        if ppform.is_valid():
            print(' ppformValid')
            from .models import PlaceProfile
            isExisting = PlaceProfile.objects.filter(placeName=ppform.instance.placeName).exists()
            if not isExisting:
                # ppform.instance.placeObject = ppform.instance.placeObject
                ppform.save()
                return HttpResponseRedirect(reverse("garden:registrationpage"))

        vform = VisitorForm(request.POST)
        if vform.is_valid():
            from .models import Visitor
            isExisting = Visitor.objects.filter(
                visitorName=vform.instance.visitorName).exists()
            if not isExisting:
                vform.save()
                return HttpResponseRedirect(reverse("garden:registrationpage"))

        forms = {
            'ProvinceForm': pform,
            'CollectionForm': cform,
            'PlaceProfileForm': ppform,
            'VisitorForm': vform,
            'message': 'Existing try new'
        }
        return render(request, 'garden/registration.html', forms)
    if request.method == 'GET':     
        # from garden.forms import ProvinceForm, CollectionForm, PlaceProfileForm, VisitorForm, QRCodeForm
        from garden.forms import ProvinceForm, CollectionForm, PlaceProfileForm, VisitorForm
        forms = {
            'ProvinceForm': ProvinceForm(),
            'CollectionForm': CollectionForm(),
            'PlaceProfileForm': PlaceProfileForm(),
            'VisitorForm': VisitorForm(),
            # 'QRCodeForm': QRCodeForm

        }
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
    # List all .ttf and .otf files in the folder
    fonts = [f for f in os.listdir(font_dir) if f.lower().endswith((".ttf", ".otf"))]
    if not fonts:
        raise Exception("❌ No .ttf or .otf fonts found in the folder.")
    
    # Pick one random font
    font_file = random.choice(fonts)
    font_path = os.path.join(font_dir, font_file)

    print(f"🎨 Using font: {font_file}")
    return ImageFont.truetype(font_path, font_size)

def create_wordart(
    text: str,
    width=800,
    height=600,
    text_outline_color=(0, 0, 0, 255),
    font_size=90,
):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_random_font(font_size=font_size)

    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    # text_x = (width - text_w) // 2 *0.9
    text_x = int((width - text_w) * 0.9 / 2)
    # text_y = (height - text_h) // 2
    text_y = 0


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
            odraw.text((text_x + dx, text_y + dy), text, font=font, fill=fill)            
    img = Image.alpha_composite(img, outline)

    # --- Main text ---
    draw = ImageDraw.Draw(img)
    # white text background
    fill = tuple(random.randint(0, 255) for _ in range(3)) + (255,)
    draw.text((text_x, text_y), text, font=font, fill=fill)

    depth = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(depth)
    for offset in range(10):  # depth layers
        d.text((text_x + offset, text_y + offset), text, font=font, fill=(20, 20, 20, 80))
    img = Image.alpha_composite(depth, img)


    gradient, mask = gradient_text(draw, text, font, (text_x, text_y), (text_w, text_h), ("#00FFFF", "#FF00FF"))
    img.paste(gradient, (text_x, text_y), mask)

    return img

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
        subtitle_font = ImageFont.truetype(
            'garden/assets/fonts/AutourOne-Regular.ttf',
            max(13, int(18 * scale)),
        )
    except Exception:
        subtitle_font = ImageFont.truetype(
            'garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf',
            max(12, int(17 * scale)),
        )
    subtitle_canvas = ImageDraw.Draw(placeImage)
    subtitle_canvas_text = collectionObj.collectionDescription
    subtitle_heigt = placeImage.height - (qrImage.height/2)
    for index, letter in enumerate(subtitle_canvas_text):
        # Put Space in every N letter of word
        if index % 35 == 0 and index > 1:
            finding = index
            try:
                while letter != ' ':
                    letter = subtitle_canvas_text[finding]
                    finding += 1
                subtitle_heigt -= 20
                subtitle_canvas_text = subtitle_canvas_text[0:finding] + '\n'+subtitle_canvas_text[finding:]
            except IndexError:
                print('Index Error: ', finding, ' is not in the text')
                break
    
    # End Adding Texts
    # To Convert To Pil Image
    qrImage.save(f"image_cards/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}-QR.png")
    # qrImage.crop((40, 40, 40, 40))  # NOTE: crop would need a new bbox and assignment
    # placeImage.crop(box)
    # Reduce QR placement padding by ~50%
    qr_padding = max(6, int(10 * scale))  # was effectively ~20px; now ~10px (scale-aware)
    qr_position = (
        (placeImage.width - qrImage.width - qr_padding),
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
    titleArt = create_wordart(
        title_text,
        width=int(placeImage.width * 0.9),
        height=max(200, int(placeImage.height * 0.25)),
        font_size=max(60, int(90 * scale)),
    )
    title_art_width_position = int(placeImage.width/2) - int(titleArt.width/2)
    placeImage.paste(titleArt, (title_art_width_position, 15), titleArt, )
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
    subtitle_canvas.text(((int(placeImage.width*0.10)), subtitle_heigt), text=subtitle_canvas_text, fill=new_color, font=subtitle_font, anchor='ls')
    small_margin_left = int(placeImage.width * 0.025)  # small left margin
    # Move these labels higher from the bottom and keep clear of the border
    small_margin_bottm = placeImage.height - border_w - max(15, int(35 * scale))

    subtitle_canvas.text(
    (small_margin_left, small_margin_bottm),
    text=collectionObj.collectionPlace.placeName + ' ' + collectionObj.collectionPlace.placeProvince.provinceName,
    fill=new_color,
    font=subtitle_font,
    anchor='ls'  # left, baseline
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
 

    # Save a high-res master (for print)
    master_path = f"image_cards/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}-MASTER.png"
    placeImage.save(master_path, dpi=(300, 300))

    # Save a smaller optimized file for upload/storage
    upload_path = f"image_cards/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}.png"
    upload_img = placeImage.copy()
    upload_img.thumbnail((UPLOAD_MAX_PX, UPLOAD_MAX_PX), Image.Resampling.LANCZOS)
    upload_img.save(upload_path, optimize=True, compress_level=9)
    print('\n\nUPLOADING TO CLOUDINARY: .....')
    try:
        if cloudinary is None:
            raise RuntimeError('cloudinary package not available; install cloudinary and configure credentials')

        result = cloudinary.uploader.upload(upload_path)
        collectionObj.collectionLocalFile = result.get('secure_url') or result.get('url')
        print('uploaded to Cloudinary with URL:', collectionObj.collectionLocalFile, '\n\n\n')
    except Exception as e:
        # Log the error, fall back to local file path so processing can continue
        print('Cloudinary upload failed:', str(e))
        collectionObj.collectionLocalFile = request.build_absolute_uri(upload_path)
        print('Falling back to local file:', collectionObj.collectionLocalFile)

    # print('Deleting Saved Files......')
    # import os
    # path = 'image_cards/'
    # for f in os.listdir(path):
    #     print('Deleting: ',f)
    #     os.remove(path+f)
    # print('Files Deleted\n\n')


    collectionObj.save()
    # collectionPicture = models.URLField(null=True, blank=True)


def get_dominant_color(pil_img):
    import PIL.ImageOps
    from PIL import Image
    import webcolors
    img = pil_img.copy()
    img = img.convert("RGBA")
    img = img.resize((1, 1), resample=0)
    r, g, b, a = img.split()
    rgb_image = Image.merge('RGB', (r, g, b))
    inverted_image = PIL.ImageOps.invert(rgb_image)
    r2, g2, b2 = inverted_image.split()
    final_transparent_image = Image.merge('RGBA', (r2, g2, b2, a))
    contranst_color = final_transparent_image.getpixel((0, 0))
    hex_value = webcolors.rgb_to_hex(contranst_color[:3])
    return f'{hex_value}'
def get_contrast_color(pil_img, vivid=False):
    """Return a high-contrast color (black or white, or vivid opposite) from an image."""
    # Resize to 1x1 to get average color
    img = pil_img.convert("RGB").resize((1, 1))
    r, g, b = img.getpixel((0, 0))
    import webcolors
    # Calculate luminance (perceived brightness)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    if vivid:
        # Generate opposite vivid color
        inv_r, inv_g, inv_b = 255 - r, 255 - g, 255 - b
        return webcolors.rgb_to_hex((inv_r, inv_g, inv_b))
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

pass

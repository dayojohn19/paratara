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
import numpy as np
import os, random
from PIL import ImageOps
import requests, io
import os, io, requests
from PIL import ImageFont


from django.core import signing
from django.utils import timezone
from django.http import HttpResponseForbidden

def get_map(request, placeName):
     print('finding html')

     return render(request, f"garden/map/{placeName}.html")

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

    visitorUser = Visitor.objects.get(visitorName=user, visitorID=userID)
    # collections = Collection.objects.filter(collectionCollector=visitorUser)
    collections = Collection.objects.all()
    data = [col.serialize() for col in collections]
    return JsonResponse(data, safe=False)



@api_view(['PUT'])
@csrf_exempt
def lookPlace(request, tokenStr=None,collectionStr=None):
    print('Looking Place')

    data = json.loads(request.body)
    print('\n we Got Data: ', data, '\n\n')
    user = data['username']
    userID = data['userID']
    collectionStr = data.get('collectionStr', None)
    print('\n Collection STR: ', collectionStr, '\n\n')
    
    if collectionStr is not None:
        try:
            collectionUser = Collection.objects.get(collectionUniqueID=collectionStr)
        except Collection.DoesNotExist:
            print('Not existing')
            return HttpResponse(
                json.dumps({"error": f"we cannot find Collection '{collectionStr}' not found."}),
                content_type="application/json",
                status=404
            )
    else:
        result = data['scan_result'].replace('"', '').split(',')
        collectionUser = Collection.objects.get(collectionUniqueID=result[2])

    if collectionUser.collectionIsCollected == True:
        serializedData = collectionUser.serialize()
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

    visitorUser = Visitor.objects.get(visitorName=user, visitorID=userID)
    collectionUser.collectionCollector = visitorUser
    collectionUser.collectionIsCollected = True
    collectionUser.save()
    visitorUser.visitorCollections.add(collectionUser)
    print('\n\n Done Saving all \n\n')
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
    print('DATA: ', data)
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
        print('We got Data from the Device: ', data)
        visit = Visitor.objects.get_or_create(
            visitorName=data['username'], visitorID=data['userID'])[0]
        print('Got Visitor: ', visit)
        serializedData = visit.serialize()
        pprint(serializedData)
        
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

        print('App send tihis: ', data['username'], data['userID'])
        return HttpResponse(json.dumps(data), content_type="application/json")

    return 'It is verified'
    if request.method == 'POST':
        print('\n Creating new Visitor')
        data = json.loads(request.body)
        visitorID = data.get('visitorID')
        visitorName = data.get('visitorName')
        # Check if Visitor has already same name
        if Visitor.objects.get(visitorName=data.get('visitorName'), visitorID=data.get('visitorID')) == None:
            # Create New Visitor Object
            visitor = Visitor.objects.create(visitorName=data.get(
                'visitorName'), visitorID=data.get('visitorID'))

    return HttpResponse(json.dumps(visitor), content_type="application/json")


def registrationPage(request):
    from django.http import HttpResponseRedirect
    # from time import sleep
    from .forms import ProvinceForm, CollectionForm, PlaceProfileForm,VisitorForm
    if request.method == 'POST':
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
            'ProvinceForm': ProvinceForm,
            'CollectionForm': CollectionForm,
            'PlaceProfileForm': PlaceProfileForm,
            'VisitorForm': VisitorForm,
            # 'QRCodeForm': QRCodeForm

        }
        return render(request, 'garden/registration.html', forms)


def UniqueGenerator(size=5, chars=string.ascii_uppercase + string.digits):
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

    # --- Create smooth gradient using NumPy ---
    if direction == "horizontal":
        gradient = np.tile(np.linspace(0, 1, text_w), (text_h, 1))
    else:  # vertical
        gradient = np.tile(np.linspace(0, 1, text_h), (text_w, 1)).T

    # Convert to grayscale image
    fill = gradient * random.randint(0, 255) 
    gradient_img = Image.fromarray(np.uint8(fill), mode="L")

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

def create_wordart(text: str, width=800, height=600,text_outline_color = (0,0,0,255)):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = get_random_font()

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
    import numpy as np
    import os
    import requests
    from io import BytesIO
    import json
    # read more here
    # https://auth0.com/blog/image-processing-in-python-with-pillow/#Resizing-Images
    qrImage = qrcode.make(f'https://paratara.com/garden/home/{collectionObj.collectionUniqueID}')
    response = requests.get(collectionObj.collectionPicture)
    placeImage = Image.open(BytesIO(response.content))
    # RESIZE
    placeImage.thumbnail((800, 800))
    # qr_toSize = int(placeImage.height/2.5)
    # qr_toSize = int(placeImage.width/2.5)
    if placeImage.width > placeImage.height:
        qr_toSize = int(placeImage.height / 2.75)
    else:
        qr_toSize = int(placeImage.width / 2.75)    
    qrImage.thumbnail((qr_toSize, qr_toSize))
    # Enhancing the Image
    placeImage = ImageEnhance.Sharpness(placeImage)
    placeImage = placeImage.enhance(1.5)
    # adding that margin
    margin = ImageDraw.Draw(placeImage)
    w, h = 220, 190

    shape = [(0, 0), (placeImage.width, placeImage.height)]

    # Finish adding margin
    # Adding Texts
    #  Adding Texts
    subtitle_font = ImageFont.truetype('garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf', 17)
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
    qrImage.save(f"garden/assets/collection/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}-QR.png")
    # qrImage.save("my_qr.png")
    qrImage = qrImage.get_image()
    qrImage.crop((40, 40, 40, 40))
    # placeImage.crop(box)
    qr_position = (
        (placeImage.width - qrImage.width - 20),
        (placeImage.height - qrImage.height - 20)
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
    downloadFont = ImageFont.truetype('garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf', 13)
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
    titleArt = create_wordart(title_text)    
    title_art_width_position = int(placeImage.width/2) - int(titleArt.width/2)
    placeImage.paste(titleArt, (title_art_width_position, 15), titleArt, )
    if collectionObj.collectionTheme == None:
        # new_color = get_dominant_color(placeImage)
        new_color = get_contrast_color(placeImage)
    else :
        new_color = collectionObj.collectionTheme
    margin.rectangle(shape, fill=None,outline=new_color, width=10)
    subtitle_canvas.text(((int(placeImage.width*0.10)), subtitle_heigt), text=subtitle_canvas_text, fill=new_color, font=subtitle_font, anchor='ls')
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


    placeImage.save(f"garden/assets/collection/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}.png")
    from garden.GoogleInitService import filesUpload
    print('\n\nSAVING TO GOOOGLE DRIVE: .....')
    fileURL = filesUpload(request, [f'garden/assets/collection/{collectionObj.collectionName}-{collectionObj.collectionUniqueID}.png'])
    collectionObj.collectionLocalFile = f'https://lh3.google.com/u/0/d/{fileURL[0]}'
    print('saved to Google Drive With Link: ','https://lh3.google.com/u/0/d/',  fileURL, '\n\n\n')

    # print('Deleting Saved Files......')
    # import os
    # path = 'garden/assets/collection/'
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

    # Calculate luminance (perceived brightness)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    if vivid:
        # Generate opposite vivid color
        inv_r, inv_g, inv_b = 255 - r, 255 - g, 255 - b
        return webcolors.rgb_to_hex((inv_r, inv_g, inv_b))
    else:
        # Return black or white for max contrast
        return "#000000" if luminance > 0.5 else "#FFFFFF"

pass

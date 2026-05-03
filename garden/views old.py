import json
import string
import random
from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
from django.urls import reverse
from rest_framework.decorators import api_view
# from rest_framework.response import Response

# from django.views.decorators.csrf import csrf_exempt
# from django.core import serializers

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
def lookPlace(request):
    import json
    from pprint import pprint
    from .models import Collection,Visitor
    from django.http import HttpResponse
    data = json.loads(request.body)
    print('\n we Got Data: ', data, '\n\n')
    user = data['username']
    userID = data['userID']
    result = data['scan_result'].replace('"', '').split(',')
    collectionUser = Collection.objects.get(collectionUniqueID=result[2])
    # visitProvince = collectionUser.collectionPlace.placeProvince
    # print('Got the Province: ',visitProvince,'\n\n')

    visitorUser = Visitor.objects.get(visitorName=user, visitorID=userID)
    # visitProvince.provinceVisitor.add(visitorUser)
    if collectionUser.collectionIsCollected == True:
        print('Already Collected')
        # if collectionUser in visitorUser.visitorCollections.all():
        serializedData = collectionUser.serialize()
        return HttpResponse(json.dumps(serializedData), content_type="application/json")

    collectionUser.collectionCollector = visitorUser
    collectionUser.collectionIsCollected = True
    collectionUser.save()
    visitorUser.visitorCollections.add(collectionUser)
    print('\n\n Done Saving all \n\n')
    serializedData = collectionUser.serialize()
    return HttpResponse(json.dumps(serializedData), content_type="application/json")
    newVisitor = Visitor.objects.get(visitorName=data.get(
        'visitorName'), visitorID=data.get('visitorID'))
    collectionObject = Collection.objects.get(
        collectionUniqueID=data.self.cleaned_data['collectionUniqueID'])

    collectionObject.collectionIsCollected = True
    collectionObject.collectionCollector = newVisitor
    collectionObject.collectionPlace.placeVisitor.add(newVisitor)
    collectionObject.save()

    newVisitor.visitorCollections.add(collectionObject)
    newVisitor.save()
    # print(fetchApiService['apiServiceValue'])
    # uniqueidtolook = request.body
    # place = PlaceProfiles.objects.get(placeUniqueID=request.user.id)
    return HttpResponse(json.dumps('[Place Unique ID]'), content_type="application/json")


@api_view(['PUT'])
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
                CreateQRCode(request, collection, 'https://www.upload-apk.com/jGKFBqod1LMjQry')
                # CreateQRCode(request, collection, 'https://play.google.com/store/apps/details?id=com.garden.app# ')

                    # request, collection, 'https://dayojohn19.github.io/appDownloadLink.html# ')
# def seeAllImages(request):
#     allCollections = Collection.models.all()
            # return HttpResponseRedirect(reverse("garden:collections"))
            from .models import Collection
            return render(request, 'garden/qr_images.html', {'collections': Collection.objects.all()})
            # return render(request, 'garden/qr_images.html', {'collections': Collection.objects.filter(collectionIsCollected__in=[False])})

            # RawForm = cform
            # collectionCount = request.POST.get('collectionCount')
            # collectionSaved = RawForm.save()
            # sleep(2)
            # print('Is there Picture background: ',collectionSaved.collectionPicture ,'\n\n')
            # if collectionSaved.collectionPicture == None:
            #     collectionSaved.collectionPicture = collectionSaved.collectionPlace.placePicture
            #     # collectionSaved = cform.save()
            #     sleep(2)
            #     print('Collection: Picture ', collectionSaved.collectionPicture)
            # collectionSaved.collectionUniqueID = UniqueGenerator()
            # collectionSaved.save()

            # for i in range(int(collectionCount)):
            #     another = cform
            #     eachCollection = another.save()
            #     if eachCollection.collectionPicture == None:
            #             eachCollection.collectionPicture = eachCollection.collectionPlace.placePicture
            #             # collectionSaved = cform.save()
            #             sleep(2)
            #             print('Collection: Picture ', collectionSaved.collectionPicture)
            #     eachCollection.collectionUniqueID = UniqueGenerator()
            #     eachCollection.save()
            #     print('NEW :D ----------------',eachCollection.id)
            #     # additionalList.append(eachCollection)
            #     print('Saving...: ', eachCollection.collectionUniqueID)
            #     CreateQRCode(request, eachCollection, 'https/again.com')
            #     print(f'Saving N instance: {i+1}/{collectionCount}')
            #     print('Saved Successfully')
            #     print(f'Creating QR Code : {eachCollection.collectionUniqueID}')
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


# Creating Collection Cards almost done
def CreateQRCode(request, collectionObj, appDownloadLink):
    # TODO Add an argument for Theme and File Location of the Head Title
    """
    # TODO Head title Image get from 
    # https://www.textstudio.com/logo/vaporwave-text-effect-2183
    save as .png then put value on CollectionObject.collectionImageIndicator
    """
    # appDownloadLink = 'https://thesite.com '
    # collectionObj = Collection.objects.get(collectionName='John Collection')
    # TODO Create a QR code that will direct to downloading app
    # TODO all above
    # Notes: Image Dimension should be 1000 × 669
    import qrcode
    from PIL import Image, ImageFont, ImageDraw, ImageEnhance
    import requests
    from io import BytesIO
    import json
    # read more here
    # https://auth0.com/blog/image-processing-in-python-with-pillow/#Resizing-Images
    # QR CODE Create in JSON the data that will be shown on the qrcode
    qrImage = qrcode.make(
        f'{appDownloadLink} ,{json.dumps(collectionObj.forQRValues())}')
    # fetching the collection Picture URL from internet
    response = requests.get(collectionObj.collectionPicture)
    placeImage = Image.open(BytesIO(response.content))
    # RESIZE
    placeImage.thumbnail((1000, 1000))
    # qr_toSize = int(placeImage.height/4)
    # qr_toSize = int(placeImage.height/2)
    qr_toSize = int(placeImage.height/2.5)
    qrImage.thumbnail((qr_toSize, qr_toSize))
    # Enhancing the Image
    placeImage = ImageEnhance.Sharpness(placeImage)
    placeImage = placeImage.enhance(1.5)
    # adding that margin
    margin = ImageDraw.Draw(placeImage)
    w, h = 220, 190
    # shape = [(10, 10), (placeImage.width-10, placeImage.height-10)]
    shape = [(0, 0), (placeImage.width, placeImage.height)]
    if collectionObj.collectionTheme == None:
        new_color = get_dominant_color(placeImage)
    else :
        new_color = collectionObj.collectionTheme
    margin.rectangle(shape, fill=None,
                     outline=new_color, width=10)
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
    subtitle_canvas.text(((int(placeImage.width*0.10)), subtitle_heigt), text=subtitle_canvas_text, fill=new_color, font=subtitle_font, anchor='ls')
    # End Adding Texts
    # To Convert To Pil Image
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
    placeImage.paste(androidLogo, (gardenLogoWidth -(gardenLogo.width - 15), gardenLogoHeight + icon_logos+10), androidLogo)

    subtitle_canvas = ImageDraw.Draw(placeImage)
    downloadFont = ImageFont.truetype('garden/assets/fonts/helvetica-255/helvetica-rounded-bold-5871d05ead8de.otf', 13)
    # subtitle_canvas.text((gardenLogoWidth - (gardenLogo.width - 44), gardenLogoHeight - 10), text='     Download\nGarden to Scan',fill=new_color, font=downloadFont, anchor='mm')
    # subtitle_canvas.text((gardenLogoWidth - (gardenLogo.width - 17), gardenLogoHeight + 20), text='     Download\nGarden to Scan',fill=new_color, font=downloadFont, anchor='mm')

    # End Logo

    # TITLE PAGE
    # ART GENERATOR for Title
    # Create a Word Art then save on the location
    response = requests.get(collectionObj.collectionImageIndicator)
    titleArt = Image.open(BytesIO(response.content))
    # titleArt = Image.open(
    #     f'garden/assets/titleImage/{collectionObj.collectionImageIndicator}.png')
    title_art_size = int(placeImage.width/2)
    titleArt.thumbnail((title_art_size, title_art_size))
    title_art_width_position = int(placeImage.width/2) - int(titleArt.width/2)
    placeImage.paste(titleArt, (title_art_width_position, 15), titleArt, )
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


pass

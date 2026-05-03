# https://dayotreep.herokuapp.com/ | https://git.heroku.com/dayotreep.git
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import HttpResponse
from django.shortcuts import redirect
from home.models import allSchedules, Places_v2
from django.shortcuts import render
from django.http import JsonResponse 
from django.views.generic import ListView, DetailView
from .models import allSchedules, Places_v2, SchedTypeAndMode
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
from userProfile.models import userPoster
from openai import OpenAI
from django.conf import settings
from .models import PlaceDiscussion
from django.http import JsonResponse
import json
client = OpenAI(api_key=settings.OPENAI_API_KEY)
import string
# Paymongo Payment
from requests.auth import HTTPBasicAuth
SECRET_KEY = "sk_live_qEeenZi789JGFsBXYMHSbAKe"
auth = HTTPBasicAuth(SECRET_KEY, '')
import requests
# end paymongo
import time




from django.contrib.postgres.search import TrigramSimilarity



def getSiargaoEvents(request):
    from . import scraperSiargao
    # scraperSiargao.SiargaoScrapper()
    from .models import SiargaoEventSchedule
    place = Places_v2.objects.get(placename="Siargao")
    # Path to your CSV
    import csv
    csv_file_path = "siargao_events.csv"
    with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extract data
            title = row.get("Title", "").strip()
            link = row.get("Link", "").strip()
            background = row.get("Background", "").replace('url("', '').replace('")', '').strip()
            thumbnail = row.get("Thumbnail", "").strip()
            marker = row.get("Marker", "").strip()
            location_text = row.get("Location", "").strip()
            date_text = row.get("Date", "").strip()
            host_name = row.get("Host Name", "").strip() or "Anonymous"
            host_link = row.get("Host Link", "").strip()
            locations_json = row.get("Locations JSON", "[]").strip()
            
            try:
                locations = json.loads(locations_json)
            except json.JSONDecodeError:
                locations = []

            # Parse date
            try:
                event_datetime = datetime.strptime(date_text.split(" - ")[0].strip(), "%B %d, %Y %I:%M %p")
                dateN, monthN, yearN = event_datetime.day, event_datetime.month, event_datetime.year
            except:
                dateN, monthN, yearN = datetime.now().day, datetime.now().month, datetime.now().year

            event_obj, created = SiargaoEventSchedule.objects.get_or_create(
                scheduleTitle=title,  # field to check uniqueness
                defaults={
                    'posterName': host_name,
                    'exactDate': date_text,
                    'posterURL': host_link,
                    'scheduleWebsite': link,
                    'backgroundURL': background,
                    'thumbnailURL': thumbnail,
                    'markerURL': marker,
                    'schedulePlace': location_text,
                    'dateN': dateN,
                    'monthN': monthN,
                    'yearN': yearN,
                    'otherDetails': json.dumps(locations)
                }
            )
            place.eventSchedules.add(event_obj)

            print(f"Saved: {title}")

def searchplace(request):
    pass
    # query = request.GET.get("q")
    # results = []
    # if query:
    #     results = Places_v2.objects.annotate(
    #         similarity=TrigramSimilarity('placename', query)
    #     ).filter(similarity__gt=0.3).order_by('-similarity')
    # return render(request, "search.html", {"results": results})


    # from django.http import JsonResponse
    # import json
    # query = request.GET.get('q', '')
    # if query:
    #     places = Places_v2.objects.filter(placename__icontains=query).values()
    #     results = list(places)
    # else:
    #     results = []
    # return JsonResponse({'results': results})


def paypal_html(request):
    from django.conf import settings
    return render(request, "home/paypal_payment.html", {
        # "paypal_client_id": "YOUR_SANDBOX_CLIENT_ID",
        "paypal_client_id": settings.PAYPAL_CLIENT_ID
    })    


@csrf_exempt
def paypal_webhook(request):
    if request.method == "POST":
        payload = json.loads(request.body)

        event_type = payload.get("event_type")
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            order_id = payload["resource"]["id"]
            payer_email = payload["resource"]["payer"]["email_address"]
            amount = payload["resource"]["amount"]["value"]

            # ✅ Save into your DB (example: mark Blog as paid)
            print(f"✅ Payment {order_id} received: {amount} from {payer_email}")

        return JsonResponse({"status": "ok"})





def htmltest(request):
    return render(request, 'home/test.html')
    # return render(request, 'home/htmltest.html')
# Create your views here.
def autopopulate(request):
    from django.conf import settings
    import json
    import os
    import json
    import random
    from userProfile.models import userPoster
    import random

    first_names = ["Anna", "Jake", "Liam", "Sofia", "Noah", "Ella", "Mia", "Ethan", "Grace", "Leo"]
    last_names = ["Taylor", "Smith", "Rivera", "Lopez", "Brown", "Garcia", "Martin", "Lee", "Davis", "Young"]

    def generate_human_usernames():
        first = random.choice(first_names)
        last = random.choice(last_names)
        style = random.choice([
            f"{first}{last}",
            f"{first}.{last}",
            f"{first}_{last}",
            f"{first}{last[0]}",
            f"{first}{random.randint(1, 99)}",   # e.g. Jake45
            f"{first}{last}{random.choice(['', '01', '22', '99'])}"  # e.g. MiaLee22
        ])
        return style.lower()
    def generate_random_meetplace():
        return random.choice(data)["name"]

    try:
        poster = userPoster.objects.get(userID=request.user.id)
    except:
        poster = userPoster.objects.create(
            userID=request.user.id, name=request.user.username, contact=request.user.email)


    print('\nMaking Cities')
    json_path = os.path.join(settings.BASE_DIR, 'data', 'cities.json')
    print('\nJSON PATH', json_path)
    with open(json_path, 'r') as f:
        data = json.load(f)
    target_provinces = {"MM", "BTG", "QUE"}
    data = [item for item in data if item["province"] in target_provinces]
    for d in data:
        try:
            checkedMunicipality = Places_v2.objects.get(placename = d['name'])
            print(d['name'],' Already Has')
        except:
            checkedMunicipality = Places_v2.objects.create(placename = d['name'])
            
            checkedMunicipality.placePhoto = getPlacePhoto(request, d['name'])
            
            checkedMunicipality.save()
            checkedMunicipality.placeID = checkedMunicipality.id
            checkedMunicipality.save()
            print('Saved ',d['name'])
        try:
            import re
            from resorts.models import resortItem as resort
            for r in resort.objects.all():
                if re.search(r.province, checkedMunicipality.placename, re.IGNORECASE):
                    checkedMunicipality.resortItem.add(r)
                    print('resort found',checkedMunicipality)
            print('try',end='')
        except:
            print('.',end='')


        detailsContact = '+639765514253'
        # additionalDetails = 'Looking for Shared'
        additionalDetails = ''
        otherDetails = 'Looking for pasahero'
        scheduleWebsite = 'https://treep.today'
        scheduleWebsite = ''


        for eachDate in range(random.randint(7, 14)):
            randomUsername = generate_human_usernames()
            meetPlace = generate_random_meetplace()            
            print(eachDate)
            # addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, poster=poster, posterID=request.user.id, posterName=request.user.username, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(1, 3), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', scheduleTypeAndMode=TheTravelType, additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
            addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, posterID=request.user.id, posterName=randomUsername, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(7, 9), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
            addedRandomSchedule.save()
            addedRandomSchedule.scheduleID = addedRandomSchedule.id
            addedRandomSchedule.save()

            checkedMunicipality.placesSchedules.add(addedRandomSchedule)
            checkedMunicipality.save()

        try:
            poster.posts.add(addedRandomSchedule)
            poster.reputations += 2
            poster.save()
        except:
            pass

        print('\n   Done Creating Dates for: ', checkedMunicipality, '\n\n\n')        

        
    print('\nEnd Making Cities\n\n')

    

    print('\n\nStarting ...\n\n')

    print('\n Getting User')

    # random.randint(283, 351)


    print('     Creating Travel Dates: ')
    

    # return HttpResponse("Done Creating Random Schedules")
    return redirect('home:home')
# def addSchedulesAndPlaces(request):
#     print('\n\nStarting ...\n\n')
#     import json
#     import random
#     from userProfile.models import userPoster
#     print('\n Getting User')
#     try:
#         poster = userPoster.objects.get(userID=request.user.id)
#     except:
#         poster = userPoster.objects.create(
#             userID=request.user.id, name=request.user.username, contact=request.user.email)

#     # random.randint(283, 351)
#     f = open('cebumunicipal.json')
#     data = json.load(f)
#     print('\n\n Looking for Municipalities: ...')
#     print('\n Found: ', len(data["CEBU"]
#           ["municipality_list"]), ' Municipalities\n\n')
#     for eachMunicipality in data["CEBU"]["municipality_list"]:
#         eachMunicipality = " ".join([eachMunicipality.capitalize(), 'Cebu'])
#         print('\n       Creating Schedule for:   ', eachMunicipality, '\n')
#         # First Check Municipality
#         try:
#             checkedMunicipality = Places_v2.objects.get(
#                 placename__iexact=eachMunicipality)
#         except:
#             checkedMunicipality = Places_v2.objects.create(
#                 placename=eachMunicipality)

#         checkedMunicipality.save()
#         checkedMunicipality.placeID = checkedMunicipality.id

#         print('     Creating Travel Dates: ')

#         try:
#             TheTravelType = SchedTypeAndMode.objects.get_or_create(modeName='carpool')[
#                 0]
#         except:
#             TheTravelType = SchedTypeAndMode.objects.filter(modeName='carpool')[
#                 0]
#         # Make Random
        
#         import random

#         first_names = ["Anna", "Jake", "Liam", "Sofia", "Noah", "Ella", "Mia", "Ethan", "Grace", "Leo"]
#         last_names = ["Taylor", "Smith", "Rivera", "Lopez", "Brown", "Garcia", "Martin", "Lee", "Davis", "Young"]

#         def generate_human_usernames():
#             first = random.choice(first_names)
#             last = random.choice(last_names)
#             style = random.choice([
#                 f"{first}{last}",
#                 f"{first}.{last}",
#                 f"{first}_{last}",
#                 f"{first}{last[0]}",
#                 f"{first}{random.randint(1, 99)}",   # e.g. Jake45
#                 f"{first}{last}{random.choice(['', '01', '22', '99'])}"  # e.g. MiaLee22
#             ])
#             return style.lower()

#         randomUsername = generate_human_usernames()
#         meetPlace = 'Near Munisipyo'
#         detailsContact = '+639765514253'
#         # additionalDetails = 'Looking for Shared'
#         additionalDetails = ''
#         otherDetails = 'Looking for pasahero'
#         scheduleWebsite = 'https://treep.today'
#         scheduleWebsite = ''


#         for eachDate in range(random.randint(7, 14)):
#             print(eachDate)
#             # addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, poster=poster, posterID=request.user.id, posterName=request.user.username, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(1, 3), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', scheduleTypeAndMode=TheTravelType, additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
#             addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, posterID=request.user.id, posterName=randomUsername, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(7, 9), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
#             addedRandomSchedule.save()
#             addedRandomSchedule.scheduleID = addedRandomSchedule.id
#             addedRandomSchedule.save()

#             checkedMunicipality.placesSchedules.add(addedRandomSchedule)
#             checkedMunicipality.save()

#         try:
#             poster.posts.add(addedRandomSchedule)
#             poster.reputations += 2
#             poster.save()
#         except:
#             pass

#         print('\n   Done Creating Dates for: ', checkedMunicipality, '\n\n\n')
#     return HttpResponse("Done Creating Random Schedules")

def addSchedulesAndPlaces(request):
    pass
def addReviewstoSchedules(request):
    import random

    ScheduleObjectLists = allSchedules.objects.all()
    for i in ScheduleObjectLists:
        i.reviewCount = random.randint(3, 16)
        i.save()

    PlaceObjectLists = Places_v2.objects.all()
    for i in PlaceObjectLists:
        i.__dict__.update(reviewCount=random.randint(3, 12))
        i.save()

    return HttpResponse("Done Creating Reviews")



class RecipesListView(ListView):
    model = allSchedules
    template_name = "home/schedule_list.html"


class RecipesDetailView(DetailView):
    model = allSchedules
    template_name = "home/schedule_detail.html"


class ResortsDetailView(DetailView):
    from resorts.models import resortItem
    model = resortItem
    template_name = "home/resort_list.html"

class ResortsDetailView(DetailView):
    from resorts.models import resortItem
    model = resortItem
    template_name = "home/resort_detail.html"

# def ads(request):


def googleadsense(request):
    # from django.http import HttpResponse
    print('Viewing ads\n\n')
# def readfile(request):
    # openit = open("D86D3E0B01797CC0A936E2472CF4FB91.txt", 'r')
    # openit = open("4575618483167828.txt", 'r')
    # return HttpResponse('google.com, pub-4575618483167828, DIRECT, f08c47fec0942fa0')
    return HttpResponse('google.com, pub-4843007524416588, DIRECT, f08c47fec0942fa0')
    # hhhhh = openit.read()
    # print('Viewing ads')
    # return HttpResponse(hhhhh)
    # return render(request, 'home/ads.txt')
def calendar_html(request):
    return render(request, 'home/place_calendar.html')
@xframe_options_exempt
def carpool(request, message=False):
    request.session.setdefault('how_many_visits', 0)
    request.session['how_many_visits'] += 1
    buttons = {
        # 'allDestinations': Places_v2.objects.all(),
        'message': message
    }
    return render(request, 'home/index.html', buttons)


def carpoolJOSN(request):
    # objectRecords = schedule.comments.values()
    placeJSONED = Places_v2.objects.all().values()
    return JsonResponse({"PlacesList": list(placeJSONED)})

@xframe_options_exempt
def home(request, message=False):
    
    request.session.setdefault('how_many_visits', 0)
    request.session['how_many_visits'] += 1
    buttons = {
        'allDestinations': Places_v2.objects.all(),
        'message': message
    }
    return render(request, 'home/index.html', buttons)    

# def home(request):
#     from SinglePage.views import SinglePageHome
#     return SinglePageHome(request)



def viewAllForms(request):
    return render(request, 'home/form.html')


def refreshSchedules_v2(request):
    from . import ImageGetSearch
    from datetime import date
    import time
    today = date.today()
    currentYear = int(today.year)
    currentDate = int(today.day)
    currentMonth = int(today.month)
    everySchedules = allSchedules.objects.all()
    allPlace = Places_v2.objects.all()
    for schedule in everySchedules:

        if schedule.yearN < currentYear:
            schedule.delete()
            break
        if (schedule.yearN == currentYear):
            if (schedule.monthN < currentMonth):
                schedule.delete()
                # continue
            # elif(schedule.monthN == currentMonth):
            #     if (schedule.dateN < currentDate):
            #         schedule.delete()
            elif (schedule.monthN < currentMonth):
                # if (schedule.dateN < currentDate):
                schedule.delete()
                # continue
        if (schedule.monthN == currentMonth):
            if (schedule.dateN < currentDate):
                schedule.delete()
    for eachPlace in allPlace:
        # time.sleep(2)
        if int(eachPlace.placesSchedules.count()) <= 0:
            if int(eachPlace.resortItem.count() <= 0):
                eachPlace.delete()
        elif eachPlace.placePhoto == '':
            newPhoto = ImageGetSearch.get_google_img(str(eachPlace.placename))
            eachPlace.placePhoto = newPhoto
            eachPlace.save()
            # time.sleep(2)
    return redirect('home:home')


def placeCalendarJSON_v2(request, id):
    place = Places_v2.objects.get(pk=id)

    placetoCheck = place
    placetoCheck.reviewCount += 1
    placetoCheck.save()    
    from django.core import serializers
    scheduleList = allSchedules.objects.filter(
        schedulePlace=id).order_by('dateN')
    data = serializers.serialize('json', scheduleList, indent=2,
                                 use_natural_foreign_keys=False, use_natural_primary_keys=True)
    schedule_list = json.loads(data)
    resort_data = serializers.serialize(
        'json',
        place.resortList.all(),
        use_natural_foreign_keys=False,
        use_natural_primary_keys=True
    )     
    event_data = serializers.serialize(
        'json',
        place.eventList.all(),
        use_natural_foreign_keys=False,
        use_natural_primary_keys=True

    )
    event_list = json.loads(event_data)
    response_data = {
        'placeSchedule': schedule_list,
        'placeName': place.placename,
        'placeResorts': resort_data,
        'placeEvents':event_list
    }    
    return HttpResponse(json.dumps(response_data, indent=2), content_type="application/json")
    # return HttpResponse(data, content_type="application/json")

from webSchedule.utils import getPlacePhoto

@csrf_exempt
def viaje_v2(request):
    if not request.user.is_authenticated:
        return redirect('userProfile:profile')
    if request.method == 'POST':
        print(request.POST)
        place = request.POST.get('placenameschedule')
        try:
            newPlace = Places_v2.objects.get(placename__iexact=place)
        except:
            # if failed to save add placeID=1
            place = ' '.join([f.capitalize() for f in place.split(' ')])
            newPlace = Places_v2.objects.create(placename=place)
            try:
                import re
                from resorts.models import resortItem as resort
                for r in resort.objects.all():
                    if re.search(r.province, newPlace.placename, re.IGNORECASE):
                        newPlace.resortItem.add(r)
            except:
                pass
            # End Adding Resort
            # getPlacePhoto(request, place)
            newPlace.placePhoto = getPlacePhoto(request, place)
            newPlace.save()
            newPlace.placeID = newPlace.id
            newPlace.save()
            # Finding / Adding Resort

        allMeetDate = request.POST.getlist('meetDate')
        print("\n\n ALL MEET DATE: ", type(allMeetDate))
        for i in allMeetDate:
            print('EACH DATE: ', i, type(i))

        from userProfile.models import userPoster
        try:
            poster = userPoster.objects.get(userID=request.user.id)
        except:
            poster = userPoster.objects.create(
                userID=request.user.id, name=request.user.username, contact=request.user.email)
        for eachDate in allMeetDate:

            newSchedule = allSchedules()
            newSchedule.posterVerified = poster.verified
            newSchedule.posterReputation = poster.reputations
            departureDate = eachDate
            departureDate = departureDate.split('-')
            try:
                newSchedule.posterName = request.user.username
                newSchedule.posterID = request.user.id
                newSchedule.poster = poster
                if poster.photo:
                    newSchedule.posterImageURL = poster.photo
                poster.posts.add(newSchedule)

            except:
                pass
            # meet_date_str = request.POST.get('meetDate')
            
            dt = datetime.fromisoformat(eachDate)

            newSchedule.yearN = dt.year
            newSchedule.monthN = dt.month
            newSchedule.dateN = dt.day
            # newSchedule.meetTime = str(dt.time())  
            newSchedule.meetTime = dt.strftime("%I:%M %p")          
            # print("DATE AND TIME: ", dt, type(dt), dt.time()    )
            # newSchedule.meetTime = departureDate['time']
            # newSchedule.dateN = departureDate[2]
            # newSchedule.monthN = departureDate[1]
            # newSchedule.yearN = departureDate[0]
            newSchedule.meetPlace = request.POST.get('meetPlace').title()

            if request.POST.get('scheduleCost'):
                newSchedule.scheduleCost = request.POST.get('scheduleCost')
            if request.POST.get('theDetails'):
                newSchedule.otherDetails = request.POST.get('theDetails')
            if request.POST.get('instagramUsername'):
                newSchedule.posterInstagram = request.POST.get(
                    'instagramUsername') 
            # try:
            #     newSchedule.detailsContact = request.user.email
            # except:
            newSchedule.detailsContact = request.POST.get('detailsContact')
            newSchedule.schedulePlace = newPlace
            if request.POST.get('MakerOrLooker'):
                newSchedule.MakerOrLooker = request.POST.get('MakerOrLooker')
            # if request.POST.get('meetTime') != '':
            #     newSchedule.meetTime = request.POST.get('meetTime')
            if request.POST.get('additionalDetails'):
                newSchedule.additionalDetails = request.POST.get(
                    'additionalDetails')
            try:
                newSchedule.scheduleWebsite = request.POST.get(
                    'scheduleWebsite')
            except:
                pass
            newSchedule.scheduleTravelType = request.POST.get(
                'scheduleTravelType')  # RIDE BIKE options
            newSchedule.save()
            # try:
            #     theType = SchedTypeAndMode.objects.get_or_create(
            #         modeName=newSchedule.scheduleTravelType)[0]
            # except: 
            #     theType = SchedTypeAndMode.objects.filter(
            #         modeName=newSchedule.scheduleTravelType)[0]
            # theType.scheduleObject.add(newSchedule)  # adding to types and mode
            # theType.save()
            newSchedule.scheduleTypeAndMode = request.POST.get('scheduleTypeAndMode')
            newSchedule.scheduleID = newSchedule.id
            # newSchedule.scheduleTypeAndMode = theType
            newSchedule.save()
            newPlace.placesSchedules.add(newSchedule)
            try:
                poster.posts.add(newSchedule)
                poster.reputations += 2
                poster.save()
            except:
                pass

        from datetime import date
        today = date.today()
        return redirect('home:place', newPlace.id, int(today.month), int(today.year))


def destinations_v2(request):
    from datetime import date
    today = date.today()
    currentYear = int(today.year)
    items = {
        'allDestinations': Places_v2.objects.all(),
        'currentMonth': int(today.month),
        'currentYear': int(today.year)
    }
    if request.method == 'POST':
        place = request.POST.get('place')
        if place == '':
            return redirect('home:destinations')
        # if failed to save add placeID=0
        currentMonth = int(today.month)
        newPlace = Places_v2.objects.create(placename=place)
        newPlace.placePhoto = getPlacePhoto(request, place)
        newPlace.save()
        newPlace.placeID = newPlace.id
        newPlace.save()
        return redirect('home:place', newPlace.id, currentMonth, currentYear)
    return render(request, 'home/destination.html', items)

def checkPlace_v2(request, placename=None, slug=None):
    print('Checking Place v2              ---------- ', placename, slug)
    if slug:
        place = get_object_or_404(Places_v2, slug=slug)
    elif placename:
        place = get_object_or_404(Places_v2, placename=placename)    
# def checkPlace_v2(request, placename):
    import calendar
    from datetime import date
    today = date.today()
    todayMonth = int(today.month)
    todayYear = int(today.year)
    try:

        placetoCheck = place
        placetoCheck.reviewCount += 1
        placetoCheck.save()
    except:
        return carpool(request, placename)
        # return redirect('home:home',message='Empty')
    return redirect('home:place', placetoCheck.id, todayMonth, todayYear)


# def place_v2(request, id, currentMonth, currentYear):
def place_url(request, placenameURL=None):
    from datetime import date
    today = date.today()

    cp = Places_v2.objects.get(slug=placenameURL)
    return place_v2(request, placenameURL=placenameURL, id=cp.id, currentMonth=int(today.month),currentYear=int(today.year))

def place_v2(request, placenameURL=None ,id=None, currentMonth=1, currentYear=1):
    import calendar
    from datetime import date
    thisMonth = calendar.HTMLCalendar(calendar.SUNDAY)
    today = date.today()
    todaysMonth = int(today.month)
    currentDate = int(today.day)
    if (currentMonth >= 13):
        currentMonth = 1
        currentYear += 1
    elif (currentMonth <= 0):
        currentMonth = 12
        currentYear -= 1
    showCalendar = thisMonth.formatmonth(currentYear, currentMonth)
    context = {
        'todaysMonth': todaysMonth,
        'calendar': showCalendar,
        'placeid': id,
        'currentMonth': currentMonth,
        'currentDate': currentDate,
        'nextMonth': currentMonth+1,
        'previousMonth': int(currentMonth)-1,
        'currentYear': currentYear,
    }
    return render(request, 'home/place.html', context)
    # did not made the new schedule form ,, Make it from a new functino
# MAKE FUNCTION FOR NEW SCHEDULE FROM THE FORM


def addScheduleReview(request, scheduleID):
    try:
        toAddReview = allSchedules.objects.get(scheduleID=scheduleID)
        toAddReview.reviewCount += 1
        toAddReview.save()
        return HttpResponse('Added', content_type="application/json")
    except:
        return HttpResponse('Failed', content_type="application/json")


@csrf_exempt
def Comment(request, postID):
    from .models import Comment
    schedule = allSchedules.objects.get(scheduleID=postID)
    from django.http import JsonResponse
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        userName = request.user.username
        if not request.user.username:
            userName = 'Anonymous'
        commentObject = Comment.objects.create(senderID=request.user.id, sender=request.user, message=data.get(
            'message'), messanger=userName, schedule=schedule)
        schedule.comment.add(commentObject)
        schedule.save()
    elif request.method == 'GET':
        # RETURN SCHEDULE COMMENTS
        # from django.core import serializers
        # data = serializers.serialize('json', schedule.comments)
        objectRecords = schedule.comments.values()
        return JsonResponse({"commentList": list(objectRecords)})




@csrf_exempt
def discussion_new(request, placeID):
    try:
        place = Places_v2.objects.get(placeID=placeID)
    except Places_v2.DoesNotExist:
        return JsonResponse({"error": "Place not found"}, status=404)

    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "Message is empty"}, status=400)

        # Get or create user
        if request.user.is_authenticated:
            user, created = userPoster.objects.get_or_create(
                userID=request.user.id,
                defaults={"name": request.user.username, "contact": request.user.email}
            )
        else:
            user = None

        # Save user discussion
        discuss = PlaceDiscussion.objects.create(
            discuss=message,
            discusser=user,
            place=place,
            discusserName=request.user.username if user else "Anonymous"
        )
        place.discussion.add(discuss)

        # OpenAI response based on place name
        prompt = f"""
You are a travel assistant specialized in the place: {place.name}.
A user asked: "{message}"
Respond concisely (max 150 words) and informatively.
"""

        try:
            ai_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            ai_message = ai_response.choices[0].message.content.strip()

            # Save AI response as discussion
            ai_discuss = PlaceDiscussion.objects.create(
                discuss=ai_message,
                discusserName="AI Bot",
                place=place
            )
            place.discussion.add(ai_discuss)

        except Exception as e:
            ai_message = f"Error getting AI response: {str(e)}"

        # Return all discussions (latest first)
        objectRecords = place.discussions.order_by('-id').values()
        return JsonResponse({"response": list(objectRecords)})

    elif request.method == "GET":
        objectRecords = place.discussions.order_by('-id').values()
        return JsonResponse({"response": list(objectRecords)})

@csrf_exempt
def discussion(request, placeID):

    client = OpenAI(api_key=settings.OPENAI_API_KEY)    
    
    data = json.loads(request.body)
    place = Places_v2.objects.get(placeID=placeID)

    if data.get('message') != '':
        if request.method == 'POST':
            
            # try:
            try:
                try:
                    user = userPoster.objects.get(userID=request.user.id)
                except:
                    user = userPoster.objects.create(
                        userID=request.user.id, name=request.user.username, contact=request.user.email)
                discuss = PlaceDiscussion.objects.create(discuss=data.get(
                    'message'), discusser=user, place=place, discusserName=request.user.username)
            except:
                discuss = PlaceDiscussion.objects.create( 
                    discuss=data.get('message'), place=place)
            place.discussion.add(discuss)

            # placeObject = Places_v2.objects.get(placeID=placeID)
            # objectRecords = place.discussions.order_by('-id').values()
            def is_question_ai(message):
                prompt = f"is '{message}' a question?respond'yes'or'no'"
                print('AI Question Check Prompt:', prompt)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=3
                )
                answer = response.choices[0].message.content.strip().lower().rstrip(string.punctuation)
                print('AI Question Check Answer:', answer)
                print('AI Question Check Answer:', answer.lower()=="yes")
                return answer.lower() == "yes"            

            if is_question_ai(data.get('message')): 
                prompt = f"""
        You are a travel assistant specialized in the place: {place.placename}.
        A user asked: "{data.get('message')}"
        Respond concisely (max 40 words) and informatively.
        """          
                try:
                    ai_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=300
                    )
                    ai_message = ai_response.choices[0].message.content.strip()

                    # Save AI response as discussion
                    ai_discuss = PlaceDiscussion.objects.create(
                        discuss=ai_message,
                        discusserName="Siargao Assistant",
                        place=place
                    )
                    place.discussion.add(ai_discuss)

                except Exception as e:
                    ai_message = f"Error getting AI response: {str(e)}"
            
            objectRecords = place.discussions.order_by('-id').values()[:5]
            return JsonResponse({"response": list(objectRecords)})
            # return JsonResponse({"response": list(discuss.values())})
        # return JsonResponse({"response":discuss.values()})
        # except:

        #     return JsonResponse({"response":'Please Register'})
    # elif request.method == 'GET':
    # from django.core import serializers
        # data = serializers.serialize('json', schedule.comments)
    # placeObject = Places_v2.objects.get(placeID=placeID)
    # objectRecords = placeObject.discussions.values()
    # objectRecords = place.discussions.values()[:5]
    objectRecords = place.discussions.order_by('-id').values()[:5]
 
    return JsonResponse({"response": list(objectRecords)})
 

@csrf_exempt
def resortDB(request, resortID):  # not Used
    from django.http import JsonResponse
    from django.http import HttpResponse
    from .models import ResortMessages
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('guestMessage')
        contact = data.get('guestContact')
        webID = data.get('webID')
        # data = ResortMessages.objects.create(resortID=resortID,guestMessage=message,guestContact=contact)
        data = ResortMessages()
        data.resortID = resortID
        data.guestMessage = message
        data.guestContact = contact
        data.save()
        return

        # return HttpResponse(data, content_type="application/json")
        # return JsonResponse({"response": data},safe=False)
    elif request.method == 'GET':
        data = ResortMessages.objects.values()
        return JsonResponse({"messages": list(data)})

        # return JsonResponse({"response": f'RESPONSE DONE {resortID}'},safe=False)
    # return HttpResponse(f"Requested Path: ")
    # return HttpResponse('data', content_type="application/json")


def rooms(request):
    return render(request, 'rooms/rooms.html')


def exploreResort(request, id):
    return render(request, 'rooms/rooms.html')


def bad_request(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def permission_denied(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def page_not_found(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def server_error(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def scrappePage(request):
    from . import StandOnRunner as scraper
    # from StandOnRunner import testStandOn
    data = 'Put request method to PUT'
    # if request.method=='PUT':
    datas = scraper.testStandOn()

    variables = {
        'datas': datas
    }

    return render(request, 'home/ScrappingPage.html', variables)


def surfFacebookPostDirectly(request):
    from . import StandOnRunner as scraper
    scraper().surfData()

    return render(request, 'home/ScrappingPage.html')



# def scrape_siargao_events(request):
#     import requests
#     from bs4 import BeautifulSoup
#     from django.http import JsonResponse    
#     url = "https://siargaovibes.com/wp-admin/admin-ajax.php"

#     payload = {
#         "action": "get_listings",
#         "listing_type": "event",
#         "page": 1,
#         "per_page": 20,
#         "orderby": "rand",
#     }

#     headers = {
#         "User-Agent": "Mozilla/5.0",
#         "X-Requested-With": "XMLHttpRequest",
#         "Referer": "https://siargaovibes.com/explore/?type=event",
#     }

#     r = requests.post(url, data=payload, headers=headers, timeout=15)

#     # DEBUG – uncomment once
#     # print(r.text[:1000])

#     soup = BeautifulSoup(r.text, "html.parser")
#     print("STATUS:", r.status_code)
#     print("TEXT LENGTH:", len(r.text))
#     print("RAW RESPONSE:")
#     print(r.text[:1000])
#     results = []

#     # NOTE: grid-item EXISTS HERE
#     for item in soup.select(".grid-item"):
#         title = item.select_one(".listing-preview-title")
#         link = item.select_one("a[href]")

#         results.append({
#             "title": title.get_text(strip=True) if title else None,
#             "url": link["href"] if link else None,
#         })

#     return JsonResponse({
#         "count": len(results),
#         "results": results,
#     })
from django.http import HttpResponse
from django.shortcuts import redirect
from home.models import allSchedules, Places_v2
from django.shortcuts import render
from django.http import JsonResponse

from .models import allSchedules, Places_v2
from django.views.decorators.csrf import csrf_exempt
# Create your views here.


carContext = {
    'appName': 'Tara',
    'allButton': [
        {'page': "/app_car/",
         'link': 'Home'},
        {'page': '/app_car/destination',
         'link': 'Plan to Go'},
        {'page': '/app_car/departure',
         'link': 'Destination'},
    ],
    # for faster Loading Input Destinations Here
}


def home(request):

    buttons = {
        'allDestinations': Places_v2.objects.all()

    }
    return render(request, 'home/index.html', buttons)


def viewAllForms(request):
    return render(request, 'home/form.html')


def news(request):
    import requests

    assortedNews = requests.get(
        'https://newsapi.org/v2/top-headlines?country=ph&apiKey=b3f57b413e2942cc94bd6609ed38a52f').json()
    businessNews = requests.get(
        'https://newsapi.org/v2/top-headlines?country=ph&category=business&apiKey=b3f57b413e2942cc94bd6609ed38a52f').json()
    techNews = requests.get(
        'https://newsapi.org/v2/top-headlines?country=ph&category=technology&apiKey=b3f57b413e2942cc94bd6609ed38a52f').json()

    variables = {
        'assortedNews': assortedNews['articles'],
        'businessNews': businessNews['articles'],
        'techNews': techNews['articles']
    }
    return render(request, 'home/news.html', variables)


def refreshSchedules_v2(request):
    from datetime import date
    today = date.today()
    currentYear = int(today.year)
    currentDate = int(today.day)
    currentMonth = int(today.month)
    everySchedules = allSchedules.objects.all()
    allPlace = Places_v2.objects.all()
    for schedule in everySchedules:
        if schedule.yearN < currentYear:
            schedule.delete()
        if (schedule.yearN == currentYear):
            if (schedule.monthN < currentMonth):
                schedule.delete()
            elif(schedule.monthN == currentMonth):
                if (schedule.dateN < currentDate):
                    schedule.delete()
    for eachPlace in allPlace:
        if int(eachPlace.placesSchedules.count()) <= 0:
            eachPlace.delete()
    return redirect('home:home')


def placeCalendarJSON_v2(request, id):
    from django.core import serializers
    scheduleList = allSchedules.objects.filter(
        schedulePlace=id).order_by('dateN')
    data = serializers.serialize('json', scheduleList)
    return HttpResponse(data, content_type="application/json")


@csrf_exempt
def viaje_v2(request):
    if request.method == 'POST':
        place = request.POST.get('place')
        try:
            newPlace = Places_v2.objects.get(placename=place)
        except:
            # if failed to save add placeID=1
            newPlace = Places_v2.objects.create(placename=place)
            newPlace.save()
            newPlace.placeID = newPlace.id
            newPlace.save()
        allMeetDate = request.POST.getlist('meetDate')

        for eachDate in allMeetDate:
            newSchedule = allSchedules()
            departureDate = eachDate
            departureDate = departureDate.split('-')
            try:
                from userProfile.models import userPoster
                try:
                    poster = userPoster.objects.get(userID=request.user.id)
                except:
                    poster = userPoster.objects.create(
                        userID=request.user.id, name=request.user.username, contact=request.user.email)
                newSchedule.posterName = request.user.username
                newSchedule.poster = poster
            except:
                pass

            newSchedule.dateN = departureDate[2]
            newSchedule.monthN = departureDate[1]
            newSchedule.yearN = departureDate[0]
            newSchedule.meetPlace = request.POST.get('meetPlace')
            if request.POST.get('scheduleTypeAndMode'):
                newSchedule.scheduleTypeAndMode = request.POST.get(
                    'scheduleTypeAndMode')
            if request.POST.get('scheduleCost'):
                newSchedule.scheduleCost = request.POST.get('scheduleCost')
            if request.POST.get('theDetails'):
                newSchedule.otherDetails = request.POST.get('theDetails')
            if request.POST.get('instagramUsername'):
                newSchedule.posterInstagram = request.POST.get(
                    'instagramUsername')
            newSchedule.detailsContact = request.POST.get('detailsContact')
            newSchedule.scheduleTravelType = request.POST.get(
                'scheduleTravelType')  # RIDE BIKE options
            newSchedule.schedulePlace = newPlace
            if request.POST.get('MakerOrLooker'):
                newSchedule.MakerOrLooker = request.POST.get('MakerOrLooker')
            if request.POST.get('meetTime') is not '':
                newSchedule.meetTime = request.POST.get('meetTime')
            if request.POST.get('additionalDetails'):
                newSchedule.additionalDetails = request.POST.get(
                    'additionalDetails')
            try:
                newSchedule.scheduleWebsite = request.POST.get(
                    'scheduleWebsite')
            except:
                pass

            newSchedule.save()
            newSchedule.scheduleID = newSchedule.id
            newSchedule.save()
            newPlace.placesSchedules.add(newSchedule)
            try:
                poster.posts.add(newSchedule)
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
        newPlace = Places_v2.objects.create(placename=place)
        newPlace.save()
        newPlace.placeID = newPlace.id
        newPlace.save()
        return redirect('home:place', newPlace.id, currentMonth, currentYear)
    return render(request, 'home/destination.html', items)


def checkPlace_v2(request, placename):
    import calendar
    from datetime import date
    today = date.today()
    todayMonth = int(today.month)
    todayYear = int(today.year)
    try:
        placetoCheck = Places_v2.objects.get(placename=placename)
        placetoCheck.reviewCount += 1
        placetoCheck.save()
    except:
        return redirect('home:home')
    return redirect('home:place', placetoCheck.id, todayMonth, todayYear)


def place_v2(request, id, currentMonth, currentYear):
    import calendar
    from datetime import date
    thisMonth = calendar.HTMLCalendar(calendar.SUNDAY)
    today = date.today()
    todaysMonth = int(today.month)
    currentDate = int(today.day)
    if (currentMonth >= 13):
        currentMonth = 1
        currentYear += 1
    elif(currentMonth <= 0):
        currentMonth = 12
        currentYear -= 1
    showCalendar = thisMonth.formatmonth(currentYear, currentMonth)
    place = Places_v2.objects.get(pk=id)
    # PUT THIS ON HTML new from newEventForm and newScheduleForm

    context = {
        'todaysMonth': todaysMonth,
        'calendar': showCalendar,
        'place': place,
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
        commentObject = Comment.objects.create(message=data.get(
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
def discussion(request, placeID):
    from .models import PlaceDiscussion
    from django.http import JsonResponse
    import json
    data = json.loads(request.body)
    place = Places_v2.objects.get(placeID=placeID)
    print('\n\n ', data.get('message'), '\n\n')
    if data.get('message') is not '':
        if request.method == 'POST':
            from userProfile.models import userPoster
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
            print('\n\n DONE')
            placeObject = Places_v2.objects.get(placeID=placeID)
            objectRecords = placeObject.discussions.order_by('-id').values()
            return JsonResponse({"response": list(objectRecords)})
            # return JsonResponse({"response": list(discuss.values())})
        # return JsonResponse({"response":discuss.values()})
        # except:
        #     print('\n\n FAILED')
        #     return JsonResponse({"response":'Please Register'})
    # elif request.method == 'GET':
    # from django.core import serializers
        # data = serializers.serialize('json', schedule.comments)
    placeObject = Places_v2.objects.get(placeID=placeID)
    objectRecords = placeObject.discussions.values()

    return JsonResponse({"response": list(objectRecords)})


@csrf_exempt
def resortDB(request, resortID):  # not Used
    print('REQUESTED')
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
        # print('\n SENDING POST REQUEST \n')
        # return HttpResponse(data, content_type="application/json")
        # return JsonResponse({"response": data},safe=False)
    elif request.method == 'GET':
        data = ResortMessages.objects.values()
        return JsonResponse({"messages": list(data)})

        # print('\n\n GET request \n\n')
        # return JsonResponse({"response": f'RESPONSE DONE {resortID}'},safe=False)
    # return HttpResponse(f"Requested Path: ")
    # return HttpResponse('data', content_type="application/json")




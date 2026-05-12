from django.shortcuts import render
import json
from django.http import HttpResponse
# # Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PaymentSerializer,ScheduleSerializer,BloggerSerializer,BlogsSerializer,StoreproductsSerializer
from .models import Payments,Transaction, Blogger, Blogs, EmailSubscribers, Storeproducts
from home.models import allSchedules
from userProfile.models import userPoster
from django.shortcuts import redirect
from .forms import BlogsForm,BloggerForm, EmailSubscriberForm
from userProfile.forms import ImageForm
from userProfile.models import userPoster
from django.http import JsonResponse
from django.utils.text import slugify
from calendar import HTMLCalendar
from datetime import date
import secrets
from django.views.decorators.http import require_http_methods
from django.conf import settings
from openai import OpenAI

# API endpoint to get all resorts and their activities for a given place
from resorts.models import resortItem
from home.models import Places_v2
from rest_framework.decorators import api_view
from rest_framework.response import Response














@api_view(['GET'])
def getPlaceSchedule(request, placename):
    # Try to resolve place by slug first, then by numeric id
    place = Places_v2.objects.filter(slug=slugify(placename)).first()
    if not place:
        try:
            # allow calling with numeric id string
            place = Places_v2.objects.get(id=int(placename))
        except Exception:
            return Response({'error': 'Place not found'}, status=404)
    # Get all resorts linked to this place (via FK or M2M)
    # Return all schedules that belong to this place
    scheduleList = allSchedules.objects.filter(schedulePlace=place).order_by('dateN')
    # Import serializer locally to avoid ordering/import issues
    try:
        from .serializers import allSchedulesSerializer
    except Exception:
        from .serializers import allSchedulesSerializer
    serializer = allSchedulesSerializer(scheduleList, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def getPlaceActivities(request, place_id):
    try:
        place = Places_v2.objects.get(id=place_id)
    except Places_v2.DoesNotExist:
        return Response({'error': 'Place not found'}, status=404)
    # Get all resorts linked to this place (via FK or M2M)
    resorts = resortItem.objects.filter(place=place)
    # Optionally, merge with place.resortItem.all() if you use M2M as well
    result = []
    for resort in resorts:
        # Use the serialize method, but only keep relevant fields for activities
        data = {
            'id': resort.id,
            'name': resort.name,
            'RealName': resort.RealName,
                'websiteURL': getattr(resort, 'websiteURL', None),
                'ActivitiesList': []
        }
        for activity in resort.ActivitiesList:
            activity_data = {
                'PackageTitle': getattr(activity, 'PackageTitle', ''),
                'subPackagesList': []
            }
            if hasattr(activity, 'subPackagesList'):
                for sub in activity.subPackagesList:
                    print('subpackage:', sub.ImageURL.first())
                    activity_data['subPackagesList'].append({
                        'title': getattr(sub, 'title', ''),
                        'price': getattr(sub, 'price', None),
                        'imageURL': sub.ImageURL.first().urlField if sub.ImageURL.exists() else ''
                    })
            data['ActivitiesList'].append(activity_data)
        result.append(data)
    return Response(result)


@api_view(['GET'])
def getPlaceAccommodations(request, place_id):
    try:
        place = Places_v2.objects.get(id=place_id)
    except Places_v2.DoesNotExist:
        return Response({'error': 'Place not found'}, status=404)
    resorts = resortItem.objects.filter(place=place)
    result = []
    for resort in resorts:
        data = {
            'id': resort.id,
            'name': resort.name,
            'RealName': resort.RealName,
            'websiteURL': getattr(resort, 'websiteURL', None),
            'AccommodationsList': []
        }
        for acc in resort.AccomodationsList:
            acc_data = {
                'PackageTitle': getattr(acc, 'PackageTitle', ''),
                'subPackagesList': []
            }
            if hasattr(acc, 'subPackagesList'):
                for sub in acc.subPackagesList:
                    acc_data['subPackagesList'].append({
                        'title': getattr(sub, 'title', ''),
                        'price': getattr(sub, 'price', None),
                        'imageURL': sub.ImageURL.first().urlField if sub.ImageURL.exists() else ''
                    })
            data['AccommodationsList'].append(acc_data)
        result.append(data)
    return Response(result)

@api_view(['GET'])
def apiEvents(request, placename):
    from home.models import Places_v2
    pi = Places_v2.objects.get(slug=slugify(placename))
    serializer = ScheduleSerializer(pi.eventSchedules.all(), many=True)
    return Response(serializer.data)


@api_view(['GET'])
def getPlaceBlogs(request, placename):
    from home.models import Places_v2
    pi = Places_v2.objects.get(slug=slugify(placename))
    serializer = BlogsSerializer(pi.blogs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getPlaceCollections(request, placename):
    from home.models import Places_v2
    from garden.models import CollectionGroup
    pi = Places_v2.objects.get(slug=slugify(placename))
    groups = CollectionGroup.objects.filter(primaryCollections__collectionPlaceDirect=pi).distinct()
    data = [g.serialize() for g in groups]
    return Response(data)



def get_calendar_view(request):
    # Get month and year from query parameters, default to today
    today = date.today()
    
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except (ValueError, TypeError):
        month = today.month
        year = today.year
    
    # Validate month and year
    if not (1 <= month <= 12):
        month = today.month
    if not (1900 <= year <= 2100):
        year = today.year
    
    hc = HTMLCalendar()
    st = hc.formatmonth(year, month)
    return JsonResponse({
        "year": year,
        "month": month,
        "calendarObject": st,
    })



@api_view(['GET'])
# def getResortItem(request, resortID):
def getResortItem(request, resortName):
    from resorts.models import resortItem
    try:
        resort = resortItem.objects.get(name=resortName)
        # resort = resortItem.objects.get(name=placeName)
        print("Found Resort:", resort.description)  # backend debug
        return Response(resort.serialize())         # DRF ensures application/json
    except resortItem.DoesNotExist:
        return Response({'error': 'Resort not found'}, status=404)
    # return Response(json.dumps(resort.serialize()))
    # return Response(resort.serialize()
                    # print(Response(resort.serialize()))






# CONVERTING FROM GOOGLE MAPS return [Lat,Long]
def ConvertCoordinates(XYCoord):
    NewCoord = XYCoord.replace('° ','')
    NewCoord = NewCoord.split(', ')

    for i in range(len(NewCoord)):
        Lat= NewCoord[i]
        if Lat.find('S') >=1:
            NewLat = Lat[:Lat.find('S')]
            NewLat = float(NewLat) *-1
            NewCoord[i] = NewLat

        elif Lat.find('N') >=1:
            NewLat = Lat[:Lat.find('N')]
            NewLat = float(NewLat) 
            NewCoord[i] = NewLat
        elif Lat.find('W') >=1:
            NewLat = Lat[:Lat.find('W')]
            NewLat = float(NewLat) *-1
            NewCoord[i] = NewLat
        
        elif Lat.find('E') >=1:
            NewLat = Lat[:Lat.find('E')]
            NewLat = float(NewLat) 
            NewCoord[i] = NewLat

    return NewCoord

def NewblogUser(request,message=None):
    if request.method == 'POST':
        if request.POST.get('blog') == 'blogger':
            try:
                newBlogger = Blogger.objects.get_or_create(userCredential=request.user)[0]
                print('Found')
            except:
                newBlogger = Blogger()
                print('New Blogger')
            newBlogger.userCredential = request.user
            newBlogger.aboutme = request.POST.get('aboutme')
            newBlogger.shortsay = request.POST.get('shortsay')
            newBlogger.profile = request.POST.get('profile')
            newBlogger.bloggerURL = request.POST.get('bloggerURL')
            newBlogger.save()
            # return render(newBlogger.bloggerURL)
            return redirect('blog' ,message="Success Profile Edit")

        if request.POST.get('blog') == 'blog':
            currentBlogger = Blogger.objects.get(userCredential=request.user)
            newBlog = Blogs()
            newBlog.blogUser = request.user
            newBlog.customTime = request.POST.get('customTime')
            try:
                # from resorts.views import uploadUphotoTry
                # ImagePosted = uploadUphotoTry(request)
                from userProfile.views import Upload_and_get_URL
                ImagePosted= Upload_and_get_URL(request)[0]
            except Exception as e:
                print(e)
                ImagePosted = request.POST.get('ImageUrl')
            """"""
            newBlog.ImageUrl = ImagePosted
            # 
            newBlog.postUrl = request.POST.get('postUrl')
            newBlog.title = request.POST.get('title')
            newBlog.context = request.POST.get('context')

            if request.POST.get('mixCoordinate') == '':
                print('\n\n NO MIx cooRdinATe\n-----------------------\n\n')
                newBlog.latitude = request.POST.get('latitude')
                newBlog.longitude = request.POST.get('longitude')
            else:
                print('Has Mix Coordinate')
                mixCoordinate = request.POST.get('mixCoordinate')
                newBlog.latitude,newBlog.longitude = ConvertCoordinates(mixCoordinate)
            print('\n\n LATITUDE: ',newBlog.latitude)
            print('\n\n LONGITUDE: ',newBlog.longitude)


            newBlog.placename = request.POST.get('placename')
            newBlog.save()
            currentBlogger.blogs.add(newBlog)
            currentBlogger.save()
            return redirect('blog' ,message="Successfully Posted")
            return render(request, 'blog/index.html',context)
            return render(currentBlogger.bloggerURL)


    try:
        if Blogger.objects.get(userCredential=request.user):
            currentUser = Blogger.objects.get(userCredential=request.user)
            context = {
                'blogForm':BlogsForm,
                'bloggerForm':BloggerForm,
                'currentUser':currentUser,
                'form':ImageForm,
                # 'profile_link':userPoster.objects.get(userID=request.user.id).photo
                'profile_link':userPoster.objects.get(userID=request.user.id).photo

            }
        else:
            context = {
                'blogForm':BlogsForm,
                'bloggerForm':BloggerForm,
                'profile_link':userPoster.objects.get(userID=request.user.id).photo
            }

    except:
        context = {
                'blogForm':BlogsForm,
                'bloggerForm':BloggerForm,
                'profile_link':'Please Register'
        }
    if message is not None:
        print('message Not None;\n\n',)
        context['message']=message
    return render(request, 'blog/index.html',context)

@api_view(['POST'])
def makepayment(request, pk):
    try:
        amount = int(request.POST.get('amount'))
    except Exception as e:
        data = request.data
        amount = data['amount']
    print('\nAmount: ',amount)
    originalUser = userPoster.objects.get(userID=request.user.id)
    if len(originalUser.hashes) < int(amount):
        return Response({'message':'Balance not enough'})   
    return recordTransaction(request,pk,int(amount),originalUser)

@api_view(['PUT'])
def confirmTransaction(request, pk):
    toConfirmTransaction = Transaction.objects.get(pk=pk)
    print(toConfirmTransaction.amount)
    print(toConfirmTransaction.confirmed)
    if toConfirmTransaction.confirmed:
        context = {'message':f'Already confirmed by: {toConfirmTransaction.confirmedBy},{toConfirmTransaction.confirmed}'}
        return Response(context)
    confirmation = request.data['confirmation']     
    if confirmation:
        toConfirmTransaction.target.hashes += toConfirmTransaction.hash
        toConfirmTransaction.confirmed = True
        toConfirmTransaction.target.save()
        context = {'message':f'Transaction Confirmed Successfully'}
    else:
        toConfirmTransaction.initiator.hashes += toConfirmTransaction.hash
        toConfirmTransaction.confirmed = False
        toConfirmTransaction.initiator.save()
        context = {'message':f'Transaction Canceled Successfully'}

    toConfirmTransaction.confirmedBy = request.user
    toConfirmTransaction.save()
    
    
    return Response(context)



def recordTransaction(request,targetID, amount,originalUser):
    targetUser = userPoster.objects.get(userID=targetID)
    originalHash, currentHash = originalUser.hashes[amount:],originalUser.hashes[:amount]
    originalUser.hashes = originalHash # deducted from the original
    try:
        original_Trans = originalUser.lastTransaction.last()
        userLastTransaction = original_Trans.id        
    except Exception as e:
        try:
            userLastTransaction = originalUser.lastTransaction.last().lastChainTransactionNo
        except Exception as e:
            userLastTransaction = 'Initial Transaction'

    transaction = Transaction()
    transaction.lastChainTransactionNo = userLastTransaction
    transaction.hash = currentHash
    transaction.initiator = originalUser
    transaction.target = targetUser
    transaction.save()
    originalUser.myTransactions.add(transaction)
    targetUser.myTransactions.add(transaction)
    targetUser.save()
    originalUser.save()

    context = {'message':f'₱ {amount} Advance Payment Sent to {targetUser.name}! \n\n Remaining Balance: ₱ {originalUser.currentBalance} \n '}
    return Response(context)


@api_view(['GET'])


def apiTest(request):
    xxx = {
    "results": [
        {
        "gender": "male",
        "name": {
            "title": "Mr",
            "first": "Arron",
            "last": "Walters"
        },
        "location": {
            "street": {
            "number": 4006,
            "name": "Park Avenue"
            },
            "city": "St Albans",
            "state": "Strathclyde",
            "country": "United Kingdom",
            "postcode": "IL8 2HL",
            "coordinates": {
            "latitude": "-10.4982",
            "longitude": "-92.3379"
            },
            "timezone": {
            "offset": "+9:30",
            "description": "Adelaide, Darwin"
            }
        },
        "email": "arron.walters@example.com",
        "login": {
            "uuid": "0ee69cd5-aef2-465c-a5f6-5cd77be75c60",
            "username": "yellowkoala424",
            "password": "enrique",
            "salt": "O48iztYi",
            "md5": "144e88407c8e23f75147927ef8689a25",
            "sha1": "3f22bb2911ba5fefeea4f8372fb501c9204ff253",
            "sha256": "d81d19c7c28c148fa5c5f1d681b917b9b2e61686975a76bd3b679acafd141b23"
        },
        "dob": {
            "date": "1988-01-24T02:24:33.701Z",
            "age": 35
        },
        "registered": {
            "date": "2019-04-15T07:14:52.058Z",
            "age": 4
        },
        "phone": "016977 5284",
        "cell": "07739 725622",
        "id": {
            "name": "NINO",
            "value": "OW 63 39 68 Z"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/49.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/49.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/49.jpg"
        },
        "nat": "GB"
        },
        {
        "gender": "female",
        "name": {
            "title": "Miss",
            "first": "Walburga",
            "last": "Neufeld"
        },
        "location": {
            "street": {
            "number": 4539,
            "name": "Im Winkel"
            },
            "city": "Marktbreit",
            "state": "Saarland",
            "country": "Germany",
            "postcode": 52573,
            "coordinates": {
            "latitude": "64.6989",
            "longitude": "147.8240"
            },
            "timezone": {
            "offset": "-8:00",
            "description": "Pacific Time (US & Canada)"
            }
        },
        "email": "walburga.neufeld@example.com",
        "login": {
            "uuid": "8cd08cdd-6a08-4841-8cc4-6bc483b123c7",
            "username": "whiteladybug220",
            "password": "bergkamp",
            "salt": "59qosx1g",
            "md5": "2bdb848939a0eaa46e4a8e342f6daf7b",
            "sha1": "a06e8695e299141d975ceb72fae3c90736b91b6a",
            "sha256": "a04665238aa1384c41c9348825b1b901755275be240e8ed6eeff7311ec933bdf"
        },
        "dob": {
            "date": "1957-08-27T12:52:08.293Z",
            "age": 66
        },
        "registered": {
            "date": "2003-11-01T09:20:07.291Z",
            "age": 19
        },
        "phone": "0526-3029840",
        "cell": "0177-9168887",
        "id": {
            "name": "SVNR",
            "value": "45 270857 N 967"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/women/41.jpg",
            "medium": "https://randomuser.me/api/portraits/med/women/41.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/women/41.jpg"
        },
        "nat": "DE"
        },
        {
        "gender": "female",
        "name": {
            "title": "Mrs",
            "first": "Aurora",
            "last": "Soto"
        },
        "location": {
            "street": {
            "number": 8403,
            "name": "Calle de Bravo Murillo"
            },
            "city": "San Sebastián",
            "state": "Navarra",
            "country": "Spain",
            "postcode": 52161,
            "coordinates": {
            "latitude": "-37.9781",
            "longitude": "-98.8884"
            },
            "timezone": {
            "offset": "+6:00",
            "description": "Almaty, Dhaka, Colombo"
            }
        },
        "email": "aurora.soto@example.com",
        "login": {
            "uuid": "9f041dd9-d572-45a5-b66a-617ddb03f83c",
            "username": "biggoose816",
            "password": "lalakers",
            "salt": "1kyXeoH4",
            "md5": "187e1a88a7635292859b66349cf94ccc",
            "sha1": "2292639f51f3631c922fc57e9ca8c87e356a940d",
            "sha256": "83f30a4f691ed219cb323f5e28ffc6935a3f1de4a9c7ada96c53650049d1bd78"
        },
        "dob": {
            "date": "1980-03-06T04:55:26.917Z",
            "age": 43
        },
        "registered": {
            "date": "2010-11-18T08:20:39.215Z",
            "age": 12
        },
        "phone": "919-097-978",
        "cell": "618-454-100",
        "id": {
            "name": "DNI",
            "value": "06222173-O"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/women/3.jpg",
            "medium": "https://randomuser.me/api/portraits/med/women/3.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/women/3.jpg"
        },
        "nat": "ES"
        },
        {
        "gender": "male",
        "name": {
            "title": "Mr",
            "first": "Todd",
            "last": "Beck"
        },
        "location": {
            "street": {
            "number": 3159,
            "name": "Stevens Creek Blvd"
            },
            "city": "Shepparton",
            "state": "Australian Capital Territory",
            "country": "Australia",
            "postcode": 5480,
            "coordinates": {
            "latitude": "-4.7853",
            "longitude": "65.7776"
            },
            "timezone": {
            "offset": "+4:30",
            "description": "Kabul"
            }
        },
        "email": "todd.beck@example.com",
        "login": {
            "uuid": "37fa6cb9-1536-4268-82df-8e387b723e8b",
            "username": "tinypanda830",
            "password": "testpass",
            "salt": "q3GiTKdc",
            "md5": "f268527a59445bcdd6e726fc06b5201b",
            "sha1": "817573c1293da13d517f239aed78bc28d92b2917",
            "sha256": "1bf2506b84f9815fed5a5ada6a2d2ca89ff26e2ec6d711c26628d151a826eb0d"
        },
        "dob": {
            "date": "1995-03-29T08:26:11.938Z",
            "age": 28
        },
        "registered": {
            "date": "2007-06-06T13:20:48.754Z",
            "age": 16
        },
        "phone": "06-0880-2379",
        "cell": "0493-633-604",
        "id": {
            "name": "TFN",
            "value": "032783748"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/85.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/85.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/85.jpg"
        },
        "nat": "AU"
        },
        {
        "gender": "male",
        "name": {
            "title": "Mr",
            "first": "Jorge",
            "last": "Duncan"
        },
        "location": {
            "street": {
            "number": 7887,
            "name": "Valwood Pkwy"
            },
            "city": "Launceston",
            "state": "Northern Territory",
            "country": "Australia",
            "postcode": 5357,
            "coordinates": {
            "latitude": "26.0530",
            "longitude": "35.7728"
            },
            "timezone": {
            "offset": "0:00",
            "description": "Western Europe Time, London, Lisbon, Casablanca"
            }
        },
        "email": "jorge.duncan@example.com",
        "login": {
            "uuid": "ab5eb39a-3478-431a-97d4-56f6957dfd40",
            "username": "silverpanda738",
            "password": "ne1469",
            "salt": "JrJgE11I",
            "md5": "b9bd7a7d4581c43a96224ed42d6c08f7",
            "sha1": "3e6045ce1eb685106d03052fe7073a9288779fae",
            "sha256": "833420f77914e0d81da4361d59edebb5cbf61575df039ff765edba246878e1b9"
        },
        "dob": {
            "date": "1999-09-15T20:28:15.779Z",
            "age": 24
        },
        "registered": {
            "date": "2015-07-03T08:50:46.644Z",
            "age": 8
        },
        "phone": "06-7847-8429",
        "cell": "0451-958-155",
        "id": {
            "name": "TFN",
            "value": "794003716"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/25.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/25.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/25.jpg"
        },
        "nat": "AU"
        },
        {
        "gender": "male",
        "name": {
            "title": "Mr",
            "first": "Dobrivoje",
            "last": "Selaković"
        },
        "location": {
            "street": {
            "number": 9100,
            "name": "Vinogradarska"
            },
            "city": "Sjenica",
            "state": "Rasina",
            "country": "Serbia",
            "postcode": 94756,
            "coordinates": {
            "latitude": "-85.4570",
            "longitude": "-90.2671"
            },
            "timezone": {
            "offset": "0:00",
            "description": "Western Europe Time, London, Lisbon, Casablanca"
            }
        },
        "email": "dobrivoje.selakovic@example.com",
        "login": {
            "uuid": "3ab60d50-d8d4-4303-9da5-5e9df39f9127",
            "username": "happyrabbit743",
            "password": "webster",
            "salt": "lKm5hFvJ",
            "md5": "ccdaf1e848f06c18c74a6750f1824fca",
            "sha1": "1e748ac6b91e1c6509d42585cad3537a5f428f7a",
            "sha256": "1d083395a3e9a5b369cf4d7304864d9907e1090842cbab86e901d89b8af51802"
        },
        "dob": {
            "date": "1994-04-21T02:08:47.555Z",
            "age": 29
        },
        "registered": {
            "date": "2005-07-10T00:21:20.981Z",
            "age": 18
        },
        "phone": "032-4226-788",
        "cell": "061-1719-350",
        "id": {
            "name": "SID",
            "value": "903185770"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/12.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/12.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/12.jpg"
        },
        "nat": "RS"
        },
        {
        "gender": "male",
        "name": {
            "title": "Monsieur",
            "first": "Michel",
            "last": "Guillaume"
        },
        "location": {
            "street": {
            "number": 5675,
            "name": "Rue de L'Abbé-Patureau"
            },
            "city": "Geltwil",
            "state": "Schwyz",
            "country": "Switzerland",
            "postcode": 7445,
            "coordinates": {
            "latitude": "-11.9584",
            "longitude": "14.9638"
            },
            "timezone": {
            "offset": "-4:00",
            "description": "Atlantic Time (Canada), Caracas, La Paz"
            }
        },
        "email": "michel.guillaume@example.com",
        "login": {
            "uuid": "b7ef4346-d12f-4723-9683-9514ed71bf1a",
            "username": "heavygoose779",
            "password": "nostromo",
            "salt": "qY1WvxDJ",
            "md5": "babec599f0cc479c895895a309da8f9f",
            "sha1": "55b3f63abd80b16b2f0a112fd3c1124c66c86fff",
            "sha256": "801f896f0837d7e242f42d373a136a21b8639847e3a84470cbc81b953b13557a"
        },
        "dob": {
            "date": "1968-06-27T06:29:59.611Z",
            "age": 55
        },
        "registered": {
            "date": "2017-09-29T03:05:16.385Z",
            "age": 6
        },
        "phone": "078 814 66 09",
        "cell": "076 118 92 65",
        "id": {
            "name": "AVS",
            "value": "756.1051.5578.72"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/66.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/66.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/66.jpg"
        },
        "nat": "CH"
        },
        {
        "gender": "male",
        "name": {
            "title": "Mr",
            "first": "Thomas",
            "last": "Anderson"
        },
        "location": {
            "street": {
            "number": 1583,
            "name": "Church Road"
            },
            "city": "Derby",
            "state": "Durham",
            "country": "United Kingdom",
            "postcode": "M08 5BY",
            "coordinates": {
            "latitude": "66.4353",
            "longitude": "121.4967"
            },
            "timezone": {
            "offset": "+5:00",
            "description": "Ekaterinburg, Islamabad, Karachi, Tashkent"
            }
        },
        "email": "thomas.anderson@example.com",
        "login": {
            "uuid": "dc6ec5d1-e8cd-46bd-bd26-c138e815ca60",
            "username": "ticklishkoala106",
            "password": "whitesox",
            "salt": "fhlpDT4w",
            "md5": "e3c2c0f79571d2a698d1a6cb10529ca5",
            "sha1": "0bfe5924f765d3d5cffad4a4cbb2be8ab3f60f82",
            "sha256": "43bad0b39c667cc893d1057c787cff675e2eaeb3769537fdc47af0ea8a8d3d56"
        },
        "dob": {
            "date": "1972-11-17T14:49:23.964Z",
            "age": 50
        },
        "registered": {
            "date": "2006-05-15T21:24:05.143Z",
            "age": 17
        },
        "phone": "017683 40016",
        "cell": "07973 455535",
        "id": {
            "name": "NINO",
            "value": "LL 26 59 58 G"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/men/40.jpg",
            "medium": "https://randomuser.me/api/portraits/med/men/40.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/men/40.jpg"
        },
        "nat": "GB"
        },
        {
        "gender": "female",
        "name": {
            "title": "Miss",
            "first": "Elli",
            "last": "Hatala"
        },
        "location": {
            "street": {
            "number": 7338,
            "name": "Mannerheimintie"
            },
            "city": "Liminka",
            "state": "Northern Savonia",
            "country": "Finland",
            "postcode": 27912,
            "coordinates": {
            "latitude": "-57.1971",
            "longitude": "163.5834"
            },
            "timezone": {
            "offset": "-2:00",
            "description": "Mid-Atlantic"
            }
        },
        "email": "elli.hatala@example.com",
        "login": {
            "uuid": "0fbecd2d-7861-4101-a333-1b4903e0a5cb",
            "username": "greenostrich265",
            "password": "erotica",
            "salt": "1nHZjqGx",
            "md5": "96a239e52cfb7c34645a73f42376c2ea",
            "sha1": "9d21610f6cc3fe93b2886356984524f770ca5e5b",
            "sha256": "3fc99f7efd7297c180aeba2f422fe466f566f841bc288f8907b5515bd76adaf8"
        },
        "dob": {
            "date": "1971-04-13T01:28:26.997Z",
            "age": 52
        },
        "registered": {
            "date": "2015-01-21T10:54:05.009Z",
            "age": 8
        },
        "phone": "06-036-812",
        "cell": "049-128-55-70",
        "id": {
            "name": "HETU",
            "value": "NaNNA776undefined"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/women/21.jpg",
            "medium": "https://randomuser.me/api/portraits/med/women/21.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/women/21.jpg"
        },
        "nat": "FI"
        },
        {
        "gender": "female",
        "name": {
            "title": "Miss",
            "first": "Rosalyn",
            "last": "Wheeler"
        },
        "location": {
            "street": {
            "number": 9386,
            "name": "North Street"
            },
            "city": "Worcester",
            "state": "Northamptonshire",
            "country": "United Kingdom",
            "postcode": "IN3 3BZ",
            "coordinates": {
            "latitude": "-70.4722",
            "longitude": "133.7754"
            },
            "timezone": {
            "offset": "-1:00",
            "description": "Azores, Cape Verde Islands"
            }
        },
        "email": "rosalyn.wheeler@example.com",
        "login": {
            "uuid": "4e82b900-eebc-4e4d-90dc-044bfe5a5691",
            "username": "happyleopard457",
            "password": "pothead",
            "salt": "xZ2oiZG5",
            "md5": "2715e66e9a607097d292c5d56eda6182",
            "sha1": "92ab72c7a5d367218dd41b483c9bea8f1bd3ee26",
            "sha256": "866af4235db561a7c7f6d48d9d06be74e8029f44409ca54e66cba3cdf1a88fda"
        },
        "dob": {
            "date": "1990-08-20T06:56:25.354Z",
            "age": 33
        },
        "registered": {
            "date": "2003-06-03T08:43:01.674Z",
            "age": 20
        },
        "phone": "015395 49344",
        "cell": "07304 362144",
        "id": {
            "name": "NINO",
            "value": "AN 23 76 38 B"
        },
        "picture": {
            "large": "https://randomuser.me/api/portraits/women/12.jpg",
            "medium": "https://randomuser.me/api/portraits/med/women/12.jpg",
            "thumbnail": "https://randomuser.me/api/portraits/thumb/women/12.jpg"
        },
        "nat": "GB"
        }
    ],
    "info": {
        "seed": "af6f1e010845079d",
        "results": 10,
        "page": 1,
        "version": "1.4"
    }
    }
    # return Response()
    # return JsonResponse(xxx)
    return HttpResponse(json.dumps(xxx), content_type="application/json")


@api_view(['GET'])
def getSchedules(request):
    scheduleList = allSchedules.objects.all().order_by('dateN')
    serializer = ScheduleSerializer(scheduleList,many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getPayments(request):
    payment = Payments.objects.all()
    serializer = PaymentSerializer(payment,many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getPayment(request,pk):
    payment = Payments.objects.get(id=pk)
    serializer = PaymentSerializer(payment,many=False)
    return Response(serializer.data)

@api_view(['PUT'])
def putPayment(request,pk):
    # data=request.data
    payment = Payments.objects.get(id=pk)
    serializer = PaymentSerializer(payment,data=request.data )
    if serializer.is_valid():
        serializer.save()
    return Response(request.data)


@api_view(['POST'])
def createPayment(request):
    data = request.data
    payment = Payments.objects.create(
        paypal_id=data["resource"]["id"],
        payer_email=data["resource"]["payer"]["email_address"],
        amount=data["resource"]["amount"]["value"],
        resort_id = int(data["resource"]["resort_id"]),
        room_id = int(data["resource"]["room_id"]),
        # body=json.dumps(data)
        body=json.dumps(data["resource"]["full_details"])
    )
    serializer = PaymentSerializer(payment, many=False)
    return Response(serializer.data)    

    # data = request.data
    # payment = Payments.objects.create(body=data['body'])
    # serializer = PaymentSerializer(payment,many=False)
    # return Response(serializer.data)
    
@api_view(['GET'])
def getBlogger(request,bloggerID):
    CurrentblogUser = Blogger.objects.get(userCredential=bloggerID)
    serializer = BloggerSerializer(CurrentblogUser, many=False)
    return Response(serializer.data)

    data = {
        'aboutme':'i am a part time Full Stack Developer using Python language',
        'shortsay':'Time is free but its priceless',
        'profile':'//Volumes/version2/Third/Visual Studio Code /GitHub/Christian Voyager.github.io/src/images/chicken_Group.png',

    }
    return Response(data)

@api_view(['GET'])
def getBlogs(request,bloggerID):
    BlogsItem = Blogs.objects.filter(blogUser=bloggerID)
    # BlogsItem = Blogs.objects.all()
    serializer = BlogsSerializer(BlogsItem, many=True)
    return Response(serializer.data)


# Storeproducts API views
@api_view(['GET'])
def get_storeproducts(request):
    storeproducts = Storeproducts.objects.all()
    serializer = StoreproductsSerializer(storeproducts, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_storeproduct(request, pk):
    try:
        storeproduct = Storeproducts.objects.get(id=pk)
        serializer = StoreproductsSerializer(storeproduct, many=False)
        return Response(serializer.data)
    except Storeproducts.DoesNotExist:
        return Response({'error': 'Storeproduct not found'}, status=404)

@api_view(['POST'])
def create_storeproduct(request):
    serializer = StoreproductsSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['PUT'])
def update_storeproduct(request, pk):
    try:
        storeproduct = Storeproducts.objects.get(id=pk)
        serializer = StoreproductsSerializer(storeproduct, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    except Storeproducts.DoesNotExist:
        return Response({'error': 'Storeproduct not found'}, status=404)

@api_view(['DELETE'])
def delete_storeproduct(request, pk):
    try:
        storeproduct = Storeproducts.objects.get(id=pk)
        storeproduct.delete()
        return Response({'message': 'Storeproduct deleted successfully'}, status=204)
    except Storeproducts.DoesNotExist:
        return Response({'error': 'Storeproduct not found'}, status=404)
    




@api_view(['GET','POST','DELETE','PUT'])
def getRoutes(request):
    routes = [
        {
        'Endpoint':'/notes/',
        'method':'GET',
        'body':None,
        'description':'Returns an array of notes'
    },
    {
        'Endpoint':'/notes/id',
        'method':'GET',
        'body':None,
        'description':'Returns a single note'
    },
    ]
    return Response(routes)


# Email Subscription Views
@require_http_methods(["POST"])
def subscribe_email(request):
    """Handle email subscription with IP tracking"""
    form = EmailSubscriberForm(request.POST)
    
    if form.is_valid():
        subscriber = form.save(commit=False)
        
        # Get IP address
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            subscriber.ip_address = ip
        except:
            ip = 'Failed'
        
        # Generate confirmation token
        subscriber.confirmation_token = secrets.token_urlsafe(32)
        
        # Track source and analytics
        subscriber.source = request.POST.get('source', 'unknown')
        subscriber.referrer_url = request.META.get('HTTP_REFERER', '')
        subscriber.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        subscriber.save()
        
        # TODO: Send confirmation email here
        # send_confirmation_email(subscriber)
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for subscribing! Please check your email to confirm.'
        })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    }, status=400)


@require_http_methods(["GET"])
def confirm_subscription(request, token):
    """Confirm email subscription via token"""
    try:
        subscriber = EmailSubscribers.objects.get(confirmation_token=token, is_confirmed=False)
        subscriber.is_confirmed = True
        from django.utils import timezone
        subscriber.confirmed_date = timezone.now()
        subscriber.save()
        
        return render(request, 'subscription_confirmed.html', {'subscriber': subscriber})
    except EmailSubscribers.DoesNotExist:
        return render(request, 'subscription_error.html', {'error': 'Invalid or expired token'})


@require_http_methods(["GET"])
def unsubscribe(request, token):
    """Unsubscribe via token"""
    try:
        subscriber = EmailSubscribers.objects.get(confirmation_token=token)
        
        if request.method == 'POST':
            subscriber.is_active = False
            from django.utils import timezone
            subscriber.unsubscribed_date = timezone.now()
            subscriber.unsubscribe_reason = request.POST.get('reason', '')
            subscriber.save()
            
            return render(request, 'unsubscribed.html')
        
        return render(request, 'unsubscribe_confirm.html', {'subscriber': subscriber})
    except EmailSubscribers.DoesNotExist:
        return render(request, 'subscription_error.html', {'error': 'Subscriber not found'})


def chatgpt_view(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                question = data.get('question', '').strip()
                if not question:
                    return JsonResponse({'error': 'No question provided'})
                
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[{"role": "user", "content": question}]
                )
                answer = response.choices[0].message.content.strip()
                return JsonResponse({'response': answer})
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'})
            except Exception as e:
                return JsonResponse({'error': f'Error: {str(e)}'})
    
    return render(request, 'chatgpt_template.html')

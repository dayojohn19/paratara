from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
#
import os
from .models import UserCredentials, UserCredentialsBackUP, userPoster,chat_room_item
import json
from .forms import ImageForm
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
def show_html(request):
    return render(request, 'userProfile/show_html.html')
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # In case of multiple proxies, take the first IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def render_template(request, template_name, context=None):
    # user_ip = get_client_ip(request)
    # print(f'\n\Your IP is {user_ip}\n Rendering Template: ', template_name, '\n\n')
    # f"Your IP is {user_ip}"
    if context is None:
        context = {}
    return render(request, template_name, context)

def Messages_Room(request):
    # if request.method == 'POST':
    #     new_room = chat_room_item.objects.get_or_create()[0]
    user = userPoster.objects.get(userID=request.user.id)
    context = {
        'currentUser': user
    }
    return render(request, 'userProfile/Messages_Room.html', context)


def extract_Data(request):
    print('\n\nExtracting\n\n')
    from django.core import serializers
    objects = userPoster.objects.all()
    with open(r'/Mode_extracted_data.json', "w") as out:
        mast_point = serializers.serialize("json", objects)
        out.write(mast_point)
    # template = loader.get_template('some_template.html')
    context = {'object': objects}
    # return HttpResponse(template.render(context, request))
    print('\nDone Extracting\n\n')


def gettingUserPoster(request, csrf_token=None, userID=None):
    print('Current USEDR: ',userID)
    if userID is not None:
        try:
            # user = userPoster.objects.get(userID=userID)
            user = userPoster.objects.get_or_create(userID=userID)[0]
            request.session.setdefault('how_many_visits', 0)
            request.session['how_many_visits'] += 1
            if (userID != request.user.id and int(request.session['how_many_visits']) < 2):
                user.reputations += 1
                user.save()
            # return HttpResponseRedirect(reverse("userProfile:profileOf", request.user.id))
            UserVisitor = request.user.additionalCreds
            if UserVisitor != user:
                print(UserVisitor.MyVisitors)
                print(UserVisitor.MyVisitations)
                UserVisitor.visitedUser.add(user)
                print('\n Added VisitorUser: ', UserVisitor, 'Visited: ', user)
                print(UserVisitor.MyVisitors)
                print(UserVisitor.MyVisitations)
                user.visitorUser.add(UserVisitor)
                print('\n Success Added VisitedUser....',
                      user, 'By', UserVisitor)
                print(UserVisitor.MyVisitors)
                print(UserVisitor.MyVisitations)
            # Add Visitor on UserPage
            # user.visitorUser.add(request.user.additionalCreds)
                UserVisitor.save()
                user.save()
                print('Done')
                print(UserVisitor.MyVisitors)
                print(UserVisitor.MyVisitations)
            else:
                print('\n Same User')
            # if (userID != request.user.id):
            #     UserVisitor = request.user.additionalCreds
            #     UserVisitor.visitedUser.add(user)
            #     UserVisitor.save()

        except Exception as e:
            user = userPoster.objects.get(userID=userID)
            print(e)
            # return HttpResponseRedirect(reverse("userProfile:profileOf", request.user.id))
    else:
        user = userPoster.objects.get(userID=userID)
    if request.user.is_authenticated:
        try:
            # pageviewer = userPoster.objects.get(id=request.user.id)
            
            pageviewer = userPoster.objects.get(id=userID)
        except:
            print('User Logged in but cant find in userPoster', userID)
            pageviewer = None
    else:
        pageviewer = None
    message = ''
    pageUser = user
    context = {
        'message': message,
        'form': ImageForm,
        'pageUser': pageUser,
        'pageViewer':pageviewer
    }
    return render_template(request, 'userProfile/index.html', context)
    # return render(request, 'userProfile/index.html', context)

    # return user


def functiontoregisterfromFacebook(request, social_auth_obj):
    print('registering')
    try:
        NewFacePoster = userPoster.objects.get_or_create(
            userID=request.user.id, name=social_auth_obj['name'], photo=social_auth_obj['picture']['data']['url'], signedFrom='facebook')[0]
        userBackUp = UserCredentialsBackUP.objects.create(
            userID=request.user.id, userPassword=social_auth_obj['id'])    # Creating BackUp
        userBackUp.save()
        request.user.additionalCreds = NewFacePoster
        request.user.photoLink = social_auth_obj['picture']['data']['url']
        request.user.save()
        print('New Poster Created')
        return NewFacePoster
    except Exception as e:
        print('Failed to Create New Poster')
        print(e)

    # import time
    # my_time = time.strftime('%b. %d, %Y %-I:%M %p', time.localtime(social_auth_obj['auth_time']))
    # print(my_time)


def profile(request):
    if request.user:
        try:     
            if request.user.additionalCreds is None:  # if first time logging
                print('first TIme Logging\n\n\n\n')
                from social_django.models import UserSocialAuth
                social_auth_obj = UserSocialAuth.objects.get(
                    user=request.user).extra_data
                print('made New User')
                # if log from facebook
                if request.user.social_auth.values_list('provider')[0][0] == 'facebook':
                    print('using Facebook')
                    user = functiontoregisterfromFacebook(
                        request, social_auth_obj)
            else:
                user = userPoster.objects.get(userID=request.user.id)
                print('Old Timer')
            context = {
                'message': '. . . . ',
                'form': ImageForm,
                'pageUser': user
            }
        except Exception as e:
            print('\n\n\n', e)
            context = {
                'message': 'Please Log in'
            }
    else:
        context = {
            'message': 'Please Log in'
        }
    return render_template(request, 'userProfile/index.html', context)    
    # return render(request, 'userProfile/index.html', context)


def logoutUser(request):
    logout(request)
    return HttpResponseRedirect(reverse("userProfile:profile"))


def logoutUserJSON(request):
    logout(request)
    return redirect('home:home')
    return JsonResponse('Log Out Successfully', safe=False)


# @login_required
# TODO make a csrf on js
# TODO return reverse to its page source url
@csrf_exempt
def loginUserJSON(request):
    if request.method == 'POST':
        dataJSON = json.loads(request.body)
        user = authenticate(request, username=dataJSON.get('usernameJSON'), password=dataJSON.get(
            'passwordJSON'), backend='django.contrib.auth.backends.ModelBackend')
        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return JsonResponse(['Successfully Log In', user.username, user.email], safe=False)
        else:
            return JsonResponse('Wrong Username or Password', safe=False)
    pass


def loginUser(request, currentPath=None):
    if request.method == 'POST':
        username = request.POST["userName"]
        password = request.POST["userPassword"]
        user = authenticate(request, username=username, password=password)
        # Check if authentication successful
        print('\n Path: ', request.path)
        
        if user is not None:
            login(request, user)
            # return gettingUserPoster(request,userID=request.user.id)
            # return HttpResponseRedirect(reverse("home:home"))
            if currentPath is not None:
                return HttpResponseRedirect(currentPath)
            request.session.set_expiry(1209600)
            return HttpResponseRedirect(reverse("home:home"))
            # return gettingUserPoster(request, userID=request.user.id)
            # return HttpResponseRedirect(reverse("userProfile:profile"))
        else:
            # return render(request, "userProfile/index.html", {
            #     "message": "Invalid username and/or password."
            # })
            return render_template(request, 'userProfile/index.html', {
                "message": "Invalid username and/or password."
            })
    else:
        # return render(request, "userProfile/index.html")
        # return HttpResponseRedirect(reverse("userProfile:profile"))
        return HttpResponseRedirect(reverse("home:home"))
        return gettingUserPoster(request, userID=request.user.id)
        # return redirect('userProfile:profile')


def changePassword(request):
    if request.method == 'POST':
        currentPassword = request.POST.get('currentPassword')
        newPassword = request.POST.get('newPassword')
        newPasswordConfirmation = request.POST.get('newPasswordConfirmation')
        
        # return
        user = authenticate(
            request, username=request.user.username, password=currentPassword)
        if user is None:
            return render_template(request, 'userProfile/index.html', {
                "message": "Current Password is incorrect."
            })
            # return render(request, "userProfile/index.html", {
            #     "message": "Current Password is incorrect."
            # })
        if newPassword != newPasswordConfirmation:
            return render_template(request, 'userProfile/index.html', {
                "message": "New Passwords must match."
            })
            # return render(request, "userProfile/index.html", {
            #     "message": "New Passwords must match."
            # })
        try:
            user.set_password(newPassword)
            user.save()
            print('Changed Password')
            userBackUp = UserCredentialsBackUP.objects.get(userID=request.user.id)
            userBackUp.userPassword = newPassword
            userBackUp.save()
            print('Changed BackUp Password')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return render_template(request, 'userProfile/index.html', {
                "message": "Password Changed Successfully."
            })
            # return render(request, "userProfile/index.html", {
            #     "message": "Password Changed Successfully."
            # })
        except Exception as e:
            print(e)
            return render_template(request, 'userProfile/index.html', {
                "message": "Failed to change Password."
            })
            # return render(request, "userProfile/index.html", {
            #     "message": "Failed to change Password."
            # })
    else:
        return HttpResponseRedirect(reverse("userProfile:profile"))

def registerUser(request, previouspath=None):
    user_ip = request.META.get('REMOTE_ADDR')
    # If behind a proxy:
    user_ip = request.META.get('HTTP_X_FORWARDED_FOR', user_ip)
    
    print('\n\nYour IP is ', user_ip, '\n\n')

    if request.method != 'POST':
        return render_template(request, 'userProfile/index.html', {})        
        # return render(request, 'userProfile/index.html')
        
    userName = request.POST.get('userName')
    userEmail = request.POST.get('userEmail')
    userPassword = request.POST.get('userPassword')
    userPasswordConfirmation = request.POST['userPasswordConfirmation']
    if userPassword != userPasswordConfirmation:
        # return render(request, "userProfile/index.html", {
        #     "message": "Passwords must match."
        # })  # RETURN WITH MESSAGE
        return render_template(request, 'userProfile/index.html', {"message": "Passwords must match."})  
    print('\nprevious path: ', previouspath)
    try:
        user = UserCredentials.objects.create_user(
            userName, userEmail, userPassword)
        user.save()
        print('\nUSER ID : ', user.id)
        userBackUp = UserCredentialsBackUP.objects.create(
            userID=user.id, userPassword=userPassword)
        userBackUp.save()
        print('\nuserID: ', userBackUp.userID, userBackUp.id)
        NewuserPoster = userPoster.objects.create(
            userID=user.id, name=user.username, contact=userEmail)
        NewuserPoster.save()
        print('\nUserID: ', NewuserPoster.userID, NewuserPoster.id)
        user.additionalCreds = NewuserPoster
        user.save()

    except IntegrityError:
        # return render(request, "userProfile/index.html", {
        #     "message": "Username already taken."
        # })
        return render_template(request, 'userProfile/index.html', {"message": "Username already taken."})  
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    return HttpResponseRedirect(reverse("home:home"))
    # return HttpResponseRedirect(reverse("userProfile:profile"))

    return gettingUserPoster(request, userID=request.user.id)
    # return HttpResponseRedirect(reverse("userProfile:profileOf",int(request.user.id)))

    return render(request, 'userProfile/index.html')


def privacypolicy(request):
    return render(request, 'userProfile/privacy.html')


def termsandconditions(request):
    return render(request, "userProfile/terms.html")

# @csrf_exempt


@login_required
def deleteUser(request):
    user = request.user
    user.delet()
    HttpResponse("We Have deleted your identification successfully",
                 content_type="text/plain")

# @csrf_protect

 
@csrf_exempt
def registerUserJSON(request):
    print('\n\nRegistering User JSON\n\n')

    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    print('\n\n\nPOSTING\n\n\n')
    from home.models import Places_v2

    try:
        dataJSON = json.loads(request.body)
    except Exception:
        return JsonResponse(['Invalid JSON body'], safe=False, status=400)

    userName = (dataJSON.get('username') or '').strip()
    userEmail = (dataJSON.get('contact') or '').strip()
    userPassword = dataJSON.get('password') or ''
    userPasswordConfirmation = dataJSON.get('passwordConfirmation') or ''
    currentplaceID = dataJSON.get('placeID')

    if not userName or not userPassword or not currentplaceID:
        return JsonResponse(['Missing required fields'], safe=False, status=400)

    if userPassword != userPasswordConfirmation:
        return JsonResponse(['Password taken and Must Match'], safe=False, status=400)

    currentPlace = Places_v2.objects.filter(id=currentplaceID).first()
    if currentPlace is None:
        return JsonResponse(['Invalid placeID'], safe=False, status=400)

    print('\n\n')
    print('Username: ', userName)
    print('Password: ', userPassword)
    print('Contact: ', userEmail)
    print('\n\n')

    photo_url = dataJSON.get('photoURL')
    putname = (dataJSON.get('putname') or '').strip()
    contact_value = userEmail or userName

    # 1) If user already exists and password matches, log them in.
    print('trying to authenticate first')
    user = authenticate(request, username=userName, password=userPassword)
    print('There is already a User: ', user)
    if user is not None:
        print('logging In')
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        try:
            user.visitedPlace.add(currentPlace)
        except Exception as e:
            print(e)

        poster, _ = userPoster.objects.get_or_create(
            userID=user.id,
            name=(user.username or contact_value),
            defaults={'contact': contact_value},
        )
        if contact_value and not poster.contact:
            poster.contact = contact_value

        if photo_url:
            poster.photo = photo_url
            user.photoLink = photo_url
        if putname:
            if not userPoster.objects.filter(userID=user.id, name=putname).exclude(id=poster.id).exists():
                poster.name = putname

        poster.save()
        if user.additionalCreds_id != poster.id:
            user.additionalCreds = poster
            user.save()

        return JsonResponse(['Logged In'], safe=False)

    # 2) Otherwise create a new user safely.
    try:
        print('Creating New User and Credentials')
        newUser = UserCredentials.objects.create_user(
            username=userName,
            email=userEmail or '',
            password=userPassword,
        )
    except IntegrityError:
        return JsonResponse(['Username already taken.'], safe=False, status=409)
    except Exception as e:
        print(e)
        return JsonResponse(['Data Server Failed to Register'], safe=False, status=500)

    try:
        newUser.visitedPlace.add(currentPlace)
    except Exception as e:
        print(e)

    try:
        UserCredentialsBackUP.objects.update_or_create(
            userID=newUser.id,
            defaults={'userPassword': userPassword},
        )
    except Exception as e:
        print(e)

    poster, _ = userPoster.objects.get_or_create(
        userID=newUser.id,
        name=(userName or contact_value),
        defaults={'contact': contact_value},
    )
    if contact_value and poster.contact != contact_value:
        poster.contact = contact_value

    if photo_url:
        poster.photo = photo_url
        newUser.photoLink = photo_url
    if putname:
        if not userPoster.objects.filter(userID=newUser.id, name=putname).exclude(id=poster.id).exists():
            poster.name = putname

    poster.save()
    newUser.additionalCreds = poster
    newUser.save()

    login(request, newUser, backend='django.contrib.auth.backends.ModelBackend')
    print('Created New User and Credentials')
    return JsonResponse(['Thank you for coming..'], safe=False)


def uploadPhoto(request):
    if request.method == 'POST':
        # TODO Changing FilePath Upload on Webdriver, segregate profile pictures from verification ID
        # TODO Made filename to 'userID__**fileName'
        user = userPoster.objects.get(userID=request.user.id)
        Imageurls = Upload_and_get_URL(request)
        print('\n\n\n\n\n\n')
        print('Image URL LOCAL: ', Imageurls[2])
        folderLink = Imageurls[2]
        user.folderLink = folderLink

        purpose = request.POST.get('purpose')
        print('\n\n What is the purpose is it profilePhoto? ',purpose)
        currentUser = request.user
        print('\n\n Who is the User: maybe its admin',currentUser)
        if purpose == "profilePhoto":
            user.photo = Imageurls[0]
            currentUser.photoLink = Imageurls[0]

        elif purpose == "verification":
            # 
            from .ID_Generator import Generate_ID
            # user.verification = Imageurls[0]
            print("\n\nGENERATING ID ",user)
            member_id_link = Generate_ID(request, user).andGetURL()
            print("\n\nGENERATING ID ",member_id_link)
            print('\n\n\n')

            print(member_id_link)
            print('\n\n--------\n\n')
            # member_id_link = 'https://drive.google.com/uc?export=view&id=' + \
            member_id_link = 'https://lh3.google.com/u/0/d/' + \
                member_id_link[0]
            user.member_ID = member_id_link
            user.verificationID = Imageurls[0]
            user.verified = True
        user.save()
        currentUser.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def Upload_and_get_URL(request):
    print('Uploading and getting the URL...\n\n\n')
    if request.method == 'POST':
        from .forms import ImageForm
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            # from userProfile.GoogleforDrive import Create_Service
            form.save()
            # from userProfile.GoogleInitService import filesUpload
            from .cloudinary_uploader import uploadtoCloudinary
            ImageObject = form.instance
            imageURLinit = ImageObject.image.url
            imageURL = imageURLinit[1:]
            print('\n\nImage LOCAL URL: ', imageURL)
            imagetwoURL = os.path.splitext(imageURL)
            imageURL = imagetwoURL[0]
            # fileURL = filesUpload(request, [imageURL+imagetwoURL[1]])
            fullURL = uploadtoCloudinary(request, imageURL+imagetwoURL[1],request.user.username+'_'+str(ImageObject.id))
            # Change it to new Initial URL for file Uploading
            # initialURL = 'https://drive.google.com/uc?export=view&id='
            # initialURL = 'https://lh3.google.com/u/0/d/'
            # fullURL = initialURL+fileURL[0]
            print('\n\nreturning: ',fullURL)
            return [fullURL, 'ImageObject', ImageObject.image.path]
        else:
            print('\n\n Form Not Valid \n\n')

    else:
        print('\n Please put POST REQUEST\n\n')
        return ['no', 'no2']


def aboutUs(request):
    # return redirect('home:home')
    from datetime import date
    from home.models import Places_v2

    today = date.today()
    default_place = Places_v2.objects.order_by('id').first()

    context = {
        "default_place_id": default_place.id if default_place else None,
        "default_month": int(today.month),
        "default_year": int(today.year),
    }
    return render(request, "userProfile/about.html", context)


def howitwork(request):
    return render(request, "userProfile/howitwork.html")


def tour_guide_register(request, place_slug=None):
    from django import forms
    from .models import TourGuide
    from home.models import allSchedules, TouristSpot, Places_v2
    from django.contrib.auth import login
    from django.db import IntegrityError

    # Get the place if slug is provided
    selected_place = None
    if place_slug:
        try:
            selected_place = Places_v2.objects.get(slug=place_slug)
        except Places_v2.DoesNotExist:
            selected_place = None

    class TourGuideRegistrationForm(forms.ModelForm):
        # User registration fields
        username = forms.CharField(max_length=150, help_text="Choose a username")
        email = forms.EmailField(required=False, help_text="Your email address (optional)")
        password = forms.CharField(widget=forms.PasswordInput, help_text="Choose a password")
        password_confirm = forms.CharField(widget=forms.PasswordInput, help_text="Confirm your password")
        
        # Tour guide fields
        selfie = forms.ImageField(required=True, help_text="Take a selfie for your profile photo")
        display_name = forms.CharField(max_length=64, required=False, help_text="Display name (defaults to username)")
        
        class Meta:
            model = TourGuide
            fields = ['primary_place', 'mobile_number', 'bio', 'experience_years', 'certifications']
            widgets = {
                'bio': forms.Textarea(attrs={'rows': 4}),
                'certifications': forms.Textarea(attrs={'rows': 3}),
            }

    if request.method == 'POST':
        form = TourGuideRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Extract user data
            username = form.cleaned_data['username']
            email = form.cleaned_data.get('email', '').strip()  # Make email optional
            password = form.cleaned_data['password']
            password_confirm = form.cleaned_data['password_confirm']
            selfie = form.cleaned_data['selfie']
            display_name = form.cleaned_data.get('display_name', '').strip()
            
            # Validate passwords match
            if password != password_confirm:
                form.add_error('password_confirm', 'Passwords do not match.')
                return render(request, 'userProfile/tour_guide_register.html', {
                    'form': form,
                    'tours': allSchedules.objects.all()[:10],
                    'tourist_spots': TouristSpot.objects.all()[:10],
                })
            
            try:
                # Upload selfie to Cloudinary
                from .cloudinary_uploader import uploadtoCloudinary
                photo_url = uploadtoCloudinary(request, selfie, f"tour_guide_{username}_selfie")
                print(f"DEBUG: Photo uploaded successfully: {photo_url}")
                
                # Create user account
                user = UserCredentials.objects.create_user(
                    username=username,
                    email=email or None,  # Use None if email is empty
                    password=password
                )
                
                # Create backup
                userBackUp = UserCredentialsBackUP.objects.create(
                    userID=user.id, 
                    userPassword=password
                )
                
                # Create userPoster
                poster = userPoster.objects.create(
                    userID=user.id,
                    name=display_name or username,
                    contact=email or '',  # Use empty string if no email
                    photo=photo_url
                )
                user.additionalCreds = poster
                user.save()
                
                # Create tour guide profile
                tour_guide = form.save(commit=False)
                tour_guide.user = user
                tour_guide.save()
                print(f"DEBUG: Created TourGuide profile for user {tour_guide}")
                
                # Handle many-to-many relationships
                selected_tours = request.POST.getlist('tours')
                selected_spots = request.POST.getlist('tourist_spots')
                
                if selected_tours:
                    tours = allSchedules.objects.filter(id__in=selected_tours)
                    tour_guide.tours.set(tours)
                
                if selected_spots:
                    spots = TouristSpot.objects.filter(id__in=selected_spots)
                    tour_guide.tourist_spots.set(spots)
                    for spot in spots:
                        print('DEBUG: Associating tour guide with spot:', spot.name)
                        spot.tourguide.add(tour_guide)
                        print('DEBUG: Tour guide added to spot:', spot.tourguide.all())
                        spot.save()
                
                # Log the user in
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                return redirect('userProfile:tour_guide_profile', username=user.username)
                
            except IntegrityError:
                form.add_error('username', 'Username already exists. Please choose a different one.')
            except Exception as e:
                form.add_error(None, f'Registration failed: {str(e)}')
        else:
            print(f"DEBUG: Form is not valid. Errors: {form.errors}")
    else:
        form = TourGuideRegistrationForm()
        # Pre-select the place if provided
        if selected_place:
            form.fields['primary_place'].initial = selected_place
            form.fields['primary_place'].disabled = True
    
    context = {
        'form': form,
        'tours': allSchedules.objects.select_related('schedulePlace').all(),
        'tourist_spots': TouristSpot.objects.select_related('place').all(),
        'places': Places_v2.objects.all(),
        'selected_place': selected_place,
    }
    return render(request, 'userProfile/tour_guide_register.html', context)


def tour_guide_profile(request, username):
    from .models import TourGuide
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    
    User = get_user_model()
    
    try:
        user = User.objects.get(username=username)
        tour_guide = TourGuide.objects.select_related('primary_place', 'user__additionalCreds').get(user=user)
    except (User.DoesNotExist, TourGuide.DoesNotExist):
        return render(request, 'userProfile/tour_guide_not_found.html')
    
    # Get the latest tourist assignment
    tourist_assignments = tour_guide.tourist_assignments.select_related('tourist').order_by('-assigned_at').first()
    
    # Convert timestamp to local time if assignment exists
    if tourist_assignments:
        tourist_assignments.assigned_at_local = timezone.localtime(tourist_assignments.assigned_at)
    
    context = {
        'tour_guide': tour_guide,
        'user': user,
        'tourist_assignments': tourist_assignments,
    }
    return render(request, 'userProfile/tour_guide_profile.html', context)


def tour_guide_list(request):
    """Display a list of all tour guides with filtering options"""
    from .models import TourGuide
    from home.models import Places_v2
    
    # Get ALL tour guides with related data (both active and inactive)
    tour_guides = TourGuide.objects.select_related('user', 'primary_place').all().order_by('-created_at')
    
    # Get all places for filter dropdown
    places = Places_v2.objects.filter(tour_guides__isnull=False).distinct().order_by('placename')
    
    # Calculate statistics
    total_guides = TourGuide.objects.count()
    active_guides = TourGuide.objects.filter(is_active=True).count()
    total_places = Places_v2.objects.filter(tour_guides__isnull=False).distinct().count()
    
    context = {
        'tour_guides': tour_guides,
        'places': places,
        'total_guides': total_guides,
        'active_guides': active_guides,
        'total_places': total_places,
    }
    return render(request, 'userProfile/tour_guide_list.html', context)


def toggle_tour_guide_status(request, guide_id):
    """Toggle tour guide active/inactive status via AJAX"""
    from .models import TourGuide
    import json
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        tour_guide = TourGuide.objects.get(id=guide_id)
        data = json.loads(request.body)
        is_active = data.get('is_active', False)
        
        tour_guide.is_active = is_active
        tour_guide.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Tour guide {tour_guide.user.username} is now {"active" if is_active else "inactive"}',
            'is_active': is_active
        })
    except TourGuide.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tour guide not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
 
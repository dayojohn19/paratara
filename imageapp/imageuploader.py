
# TODO chnage the uploading location
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import time
import requests
import base64


import pickle
import os
try:
    from google_auth_oauthlib.flow import Flow, InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
    GOOGLE_IMPORT_ERROR = None
except ImportError as e:
    GOOGLE_API_AVAILABLE = False
    GOOGLE_IMPORT_ERROR = e
import datetime
import time
from .forms import ImageForm
from django.db import models


import os
import time

"""
USES

Upload_and_get_URL(request) with files
return [url_to_use, url_to_backup]

def getPlacePhoto(request, placename)
return 'url_photo'

https://john-christoper.imgbb.com

"""

# from .GoogleforDrive import Create_Service
def _require_google_api():
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError(
            'Google upload dependencies are not installed. Install google-api-python-client, '
            'google-auth and google-auth-oauthlib to enable this feature.'
        ) from GOOGLE_IMPORT_ERROR


def Create_Service(client_secret_file, api_name, api_version, *scopes):
    _require_google_api()
    print('\n 1 sec delay....\n\n')
    time.sleep(1)
 
    print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)
 
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    if not cred or not cred.valid: 
        print('\n\n CRED NOT VALID')
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            #
            # flow.redirect_uri('https://gentle-springs-04001.herokuapp.com/')
            #
            flow.authorization_url(access_type='offline',
                                   include_granted_scopes='true')
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)
    try:
        service = build(API_SERVICE_NAME, API_VERSION,
                        credentials=cred, static_discovery=False)
        print(API_SERVICE_NAME, 'service created successfully')
        # **************************
           # VIEWING CALENDAR # **************************
        # **************************
        # print("""
        # Creating Calendar Service....
        # """)
        # Calendarservice = build('calendar', 'v3', credentials=cred)
        # now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        # print('Getting the upcoming 1000 events')
        # events_result = Calendarservice.events().list(calendarId='primary', timeMin=now,maxResults=1000, singleEvents=True, orderBy='startTime').execute()
        # events = events_result.get('items', [])
        # if not events:
        #     print('No upcoming events found.')
        # for event in events:
        #     start = event['start'].get('dateTime', event['start'].get('date'))
        #     print(start, event['summary'])

        # print("""
        # DONE Creating Calendar Service....
        # """)
        # **************************
            # END OF VIEWING CALENDAR        
        # **************************
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None
 

def convert_to_RFC_datetime(year=1900, month=1, day=1, hour=0, minute=0):
    dt = datetime.datetime(year, month, day, hour, minute, 0).isoformat() + 'Z'
    return dt

# from Google import Create_Service

# CLIENT_S_FILE = 'client_s_API.json'
CLIENT_S_FILE = { "web": { "client_id": "1010238589793-53d9pr9fpf7aecsssqirkvmjias8ir7r.apps.googleusercontent.com", "project_id": "thermal-list-338806", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_secret": "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" } }

# UPLOADING FILE on drive
API_NAME = 'drive'
 
API_VERSION = 'v3'
# Scopes for Drive
SCOPES_for_Drive = ['https://www.googleapis.com/auth/drive',"https://www.googleapis.com/auth/calendar",'https://www.googleapis.com/auth/calendar']
service = None
if GOOGLE_API_AVAILABLE:
    try:
        service = Create_Service(CLIENT_S_FILE, API_NAME,
                                 API_VERSION, SCOPES_for_Drive)
    except Exception as e:
        print('Google Drive service init failed:', e)
        service = None

folder_id = '1mdB5SCnyfLy8n4lHBi-3PVhpy7fHc4k2'
all_files = ['picture2.jpg', 'picture2.jpg']
mime_types = ['image/jpeg']
# IMGBB_API_KEY = "65ed182b008522d2c762031a3ff4953b"  # get from imgbb.com
IMGBB_API_KEY = "ca7f3a26f5fb6343337e4a4f02c07b12"  # get from imgbb.com repapaka20
def compress_image(uploaded_file, max_size_mb=1, quality=50):
    print('Compressing image...')
    time.sleep(1)  # Simulate time-consuming task
    # Check file size (bytes → MB)
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        print('No compression needed.')
        return uploaded_file  # already small enough

    # Open image with Pillow
    img = Image.open(uploaded_file)

    # Convert to RGB if not already (important for PNG with alpha)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Save to memory with lower quality
    output_io = BytesIO()
    img.save(output_io, format='JPEG', quality=quality)
    output_io.seek(0)

    # Create InMemoryUploadedFile so Django can save it
    compressed_file = InMemoryUploadedFile(
        output_io,               # file
        'ImageField',            # field name
        f"{uploaded_file.name.split('.')[0]}_compressed.jpg",  # new filename
        'image/jpeg',            # content type
        sys.getsizeof(output_io), # size
        None                     # charset
    )
    print('Image compressed.')
    time.sleep(2)
    return compressed_file


print('LOADING')
def upload_to_imgbb(file_obj):
    file_obj = compress_image(file_obj)
    file_obj.seek(0)  # rewind pointer after compression

    # Read file and encode in base64, then decode to string
    encoded_image = base64.b64encode(file_obj.read()).decode('utf-8')

    url = "https://api.imgbb.com/1/upload"
    # IMGBB_API_KEY = "65ed182b008522d2c762031a3ff4953b"  # your imgbb API key
    IMGBB_API_KEY = "ca7f3a26f5fb6343337e4a4f02c07b12"  # get from imgbb.com repapaka20

    payload = {
        "key": IMGBB_API_KEY.strip(),  # strip to remove stray spaces/newlines
        "image": encoded_image,
    }

    # Make the request
    res = requests.post(url, data=payload)

    # Log for debugging
    print("Status:", res.status_code)
    print("Response:", res.text)

    # Raise if bad status
    res.raise_for_status()

    return res.json()["data"]["url"]
    
def getPlacePhoto(request, placename):
    import requests
    access_key = "fXI_L-wmv-PZt4chRdmotjG3ha2vQntZgLm3bbb5QHY"
    url = f"https://api.unsplash.com/search/photos"
    params = {
        "query": placename,
        "client_id": access_key,
        "per_page": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['results']:
            image_url = data['results'][0]['urls']['regular']
            print(f"Setting background for {image_url}")
            time.sleep(1)
            print(f"Setting background for {image_url}")

            time.sleep(1)
            print(f"Setting background for {image_url}")
            time.sleep(1)
            print(f"Setting background for {image_url}")
            time.sleep(1)

            return image_url
        else:
            #TODO find a new way to get image_url
            print(f"No image found for {placename}")
            time.sleep(1)
            print(f"No image found for {placename}")
            time.sleep(1)
            print(f"No image found for {placename}")
            time.sleep(1)
            return None
    except requests.RequestException as e:
        print(f"Error fetching Unsplash image: {e}")
        print(f"Error fetching Unsplash image: {e}")
        print(f"Error fetching Unsplash image: {e}")
        print(f"Error fetching Unsplash image: {e}")
        return None

def filesUpload(request,file_names): # Send request.POST here, with file_name = filePATH
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError(
            'Google upload is disabled because Google API dependencies are not installed.'
        ) from GOOGLE_IMPORT_ERROR

    global service
    if service is None:
        service = Create_Service(CLIENT_S_FILE, API_NAME, API_VERSION, SCOPES_for_Drive)

    print('\n\nFILE Name: ',file_names)
    print('\n\n')
    time.sleep(2)
    purpose = request.POST.get('purpose')
    if purpose == "profilePhoto":
        # folder_id = '1L6KVom7TJjZrJuu-BN9zb0tswmvz8JdP'
        folder_id = '1gOG6aUyygMzBn9uvQSen1fMLaLMqlbQ4'
    elif purpose == "verification":
        folder_id = '1dARijnD7EMgIcSwS9ppCadhU5jSjuuxB'
        folder_id = '1dARijnD7EMgIcSwS9ppCadhU5jSjuuxB'
    # elif purpose == "verification":
    #     folder_id = '1AO-ulRmE7_tydV2xahA0TsI1aU0iyAKz'
    elif purpose == "resort":
        # folder_id = '1Gz97KeGZqgS5NdkgxvskWlPYtoMb7QXf'
        folder_id = '1dUDyb2xcg8JFIxNVn-14ttM3v2hpJoj0'
    elif purpose == "blog":
        folder_id = '1DkcZeW8pGEDxbclLk9YAwF7mjeMZx8o3'
    # elif purpose == 'credentials':
    #     folder_id = '1UyBMGLw85jSwK2iDLGyN5O8DbdsEXpLR'
    else: 
        print('No purpose indicated = resort, verification, profilePhoto')
        # FOR COLLECTION
        # user_folder_name = str(request.user.id)+'__'+request.user.username
        # user_folder_name = 'collectionscollections'
        # folder_id = get_or_create_newfolder('1UyBMGLw85jSwK2iDLGyN5O8DbdsEXpLR',user_folder_name)
        # FOR COLLECTION
        folder_id = '10k9Yo8GoVtmpT5IdOCZufykWw1z7yiRj'
    print('sleeping', folder_id)
    time.sleep(2)
    try:
        print('service: ', service)
        all_uploaded_files = []
        for file_name in file_names:
            print('File Name: ',file_name)
            file_meta = {   
                # FOR COLLECTION
                # 'name': str(request.user.id)+'__'+request.user.username+'__'+purpose,
                'name': 'Collection__Collection__Collection',
                'parents': [folder_id]
            }
            media = MediaFileUpload(file_name)
            uploadedFile = service.files().create(
                body=file_meta,
                media_body=media,
                fields='id'
            ).execute()
            print('Finished Executing..\n\n')
            all_uploaded_files.append(uploadedFile.get('id'))
            print('Finished Executing2..\n\n')
        return all_uploaded_files
        
    except Exception as e:
        print(e)
        print('\n Cant upload files' )
        
        Create_Service(CLIENT_S_FILE, API_NAME,
                       API_VERSION, SCOPES_for_Drive)
        filesUpload(request,file_names)




def Upload_and_get_URL(request):
    print('Uploading and getting the URL...\n\n\n')
    if request.method == 'POST':
        
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            # Start UPLOADING IN GOOGLE
            # from userProfile.GoogleforDrive import Create_Service
            image_obj = form.save(commit=False)

            # Get IP address
            try:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')
                image_obj.ip_address = ip
            except:
                ip = None
            
                # TODO GET GEOLOCATOPN HERE from django.contrib.gis.geoip2 import GeoIP2
            image_obj.ip_address = ip
            # Track source and analytics
            image_obj.source = request.POST.get('source', 'unknown')
            image_obj.referrer_url = request.META.get('HTTP_REFERER', '')
            image_obj.user_agent = request.META.get('HTTP_USER_AGENT', '')


            form.save()
            # from userProfile.GoogleInitService import filesUpload
            ImageObject = form.instance
            imageURLinit = ImageObject.image.url
            imageURL = imageURLinit[1:]
            imagetwoURL = os.path.splitext(imageURL)
            imageURL = imagetwoURL[0]
            try:
                fileURL = filesUpload(request, [imageURL+imagetwoURL[1]])
                # Change it to new Initial URL for file Uploading
                # initialURL = 'https://drive.google.com/uc?export=view&id='
                initialURL = 'https://lh3.google.com/u/0/d/'
                fullURL = initialURL+fileURL[0]
                # END UPLOADING IN GOOGLE
            except:
                print('Failed Uploading to Google')
                fullURL = 'https://error.com'



            # START UPLOADING IN IMBB
            # form = ImageForm(request.POST, request.FILES)

            # file_obj = request.FILES.get("image")
            file_obj = form.cleaned_data['image'] 
            print("Name:", file_obj.name, "Size:", file_obj.size, "Type:", file_obj.content_type)
            time.sleep(5)
                # file_obj = request.FILES["image"]
                # from ..webSchedule.utils import upload_to_imgbb
                # from ..webSchedule.utils import upload_to_imgbb
                # from webSchedule.utils import upload_to_imgbb
            image_url = upload_to_imgbb(file_obj)
            print("\n\n IMAGE URL: ", image_url)
            # form.save()
            # END UPLOADING IN IMBB
            form.imbbURL = image_url
            form.googleURL = fullURL

            form.save()
        # return [image_url, fullURL]
            return image_url
        # return render(request, 'singlepage2/uploadimage.html', {'message': form, 'image_url': image_url})
            # return [fullURL, 'ImageObject', ImageObject.image.path]
        else:
            print(form.errors) 
            print('\n\n Form Not Valid \n\n')

    else:
        
        print('\n Please put POST REQUEST\n\n')
        return ['no', 'no2']


# @csrf_exempt  # remove this if you're using {% csrf_token %} in form
# def upload_imgbb(request):
#     if request.method == "GET":
#         # from singlepage2.forms import ImgUploadForm
#         from .forms import ImageForm
#         # form = ImgUploadForm()
#         form = ImageForm()
#         # from imageapp.googleuploader import Upload_and_get_URL, ImageForm
#         return render(request, 'singlepage2/uploadimage.html',{'form': form})


# uploadIT(all_files)
"""def uploadToDrive(file_name):
    folder_id = '1mdB5SCnyfLy8n4lHBi-3PVhpy7fHc4k2'
    file_meta= {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_name)
    uploadedFile = service.files().create(
        body=file_meta,
        media_body=media,
        fields='id'
    )
    print('\n\n SUCESS\n\n YOURE GREAT')
uploadToDrive('picture2.jpg')"""


def get_or_create_newfolder(credentialParentFolderID,user_folder_name):
    try:
        print('Getting Parent Folder: ',credentialParentFolderID)
        files = []
        page_token = None
        while True:
            print('Still True..')
            response = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{user_folder_name}'",
                                            # driveId='1GCeWNlsQtJluCWheKChPjG064uSf3eue',
                                            # includeItemsFromAllDrives=True,
                                            # supportsAllDrives=True,
                                            # corpora='drive',

                                            spaces='drive',
                                            fields='nextPageToken, '
                                                   'files(id, name)',

                                            pageToken=page_token).execute()
            print('Trying..')
            try:
                if len(response.get('files'))>=1:
                    print('\n\n Has Folder\n\n')
                    print('Returning to folder ID: ',response.get('files')[0].get('id'))
                    return response.get('files')[0].get('id')
                    return credentialParentFolderID
            except:   
            # else:
                print('Exception Creating New file meta')
                # TODO CREATE A sub folder inside a parent of credentials
                file_metadata = {
                    'name':user_folder_name,
                    'mimeType':'application/vnd.google-apps.folder',
                    'parents':[credentialParentFolderID]
                }
                newFolder = service.files().create(body=file_metadata,fields='id').execute()
                # print('Created new Folder: ',newFolder.get('id'))

                return newFolder.get('id')
                # Process change
            # print(F'Found file: {file.get("name")}, {file.get("id")}')
            # files.extend(response.get('files', []))
            # page_token = response.get('nextPageToken', None)
            # if page_token is None:

            break
        # fileName.get('name') == 'Tree Profiles' for fileName in files.values():
        # if next((i.get('name')) for i in files if i==user_folder_name):
        # try:
        #     m = next((i) for i in files if i.get('name')==user_folder_name)
        #     print(m)
        #     print(m.get('id'))

        #     print('Found \n\n')
        #     print('Found \n\n')
        # except StopIteration:
        #     create_folder(user_folder_name)

        #     print(' NOt Found \n\n')


    except:
        print('get_or_create Could not make it')
        pass



# def create_folder(user_folder_name):
#     """ Create a folder and prints the folder ID
#     Returns : Folder Id

#     Load pre-authorized user credentials from the environment.
#     TODO(developer) - See https://developers.google.com/identity
#     for guides on implementing OAuth2 for the application.
#     """
#     # creds, _ = google.auth.default()

#     try:
#         # create drive api client
#         service = build('drive', 'v3', credentials=creds)
#         file_metadata = {
#             'name':user_folder_name ,
#             'mimeType': 'application/vnd.google-apps.folder',
#             'parents':'1UyBMGLw85jSwK2iDLGyN5O8DbdsEXpLR'
#         }

#         # pylint: disable=maybe-no-member
#         file = service.files().create(body=file_metadata, fields='id'
#                                       ).execute()
#         print(F'Folder ID: "{file.get("id")}".')
#         return file.get('id')

#     except HttpError as error:
#         print(F'An error occurred: {error}')
#         return None


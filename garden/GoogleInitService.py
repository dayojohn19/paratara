print("2")
try:
    from googleapiclient.http import MediaFileUpload
    from .GoogleforDrive import Create_Service
    GOOGLE_API_AVAILABLE = True
    GOOGLE_IMPORT_ERROR = None
except Exception as e:
    GOOGLE_API_AVAILABLE = False
    GOOGLE_IMPORT_ERROR = e
print("2")
import os
print("2")
import time
print("2")
print("2")

# from Google import Create_Service

CLIENT_S_FILE = 'client_s_API.json'
# UPLOADING FILE on drive
API_NAME = 'drive'

API_VERSION = 'v3'
# Scopes for Drive
SCOPES_for_Drive = ['https://www.googleapis.com/auth/drive',"https://www.googleapis.com/auth/calendar",'https://www.googleapis.com/auth/calendar']
service = None
if GOOGLE_API_AVAILABLE:
    try:
        service = Create_Service(CLIENT_S_FILE, API_NAME, API_VERSION, SCOPES_for_Drive)
    except Exception as e:
        print('Google Drive service init failed:', e)
        service = None

folder_id = '1mdB5SCnyfLy8n4lHBi-3PVhpy7fHc4k2'
all_files = ['picture2.jpg', 'picture2.jpg']
mime_types = ['image/jpeg']

print('LOADING')

 
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


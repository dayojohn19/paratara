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


def _require_google_api():
    if not GOOGLE_API_AVAILABLE:
        raise RuntimeError(
            'Google API dependencies are not installed. Install google-api-python-client, '
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


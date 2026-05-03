import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'thermal-list-338806-4603674b3ae6.json')
creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)


def delete_children(folder_id):
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='nextPageToken, files(id, name, mimeType)',
            spaces='drive',
            pageToken=page_token,
        ).execute()
        items = results.get('files', [])
        for item in items:
            service.files().delete(fileId=item['id']).execute()
            print(f"Deleted: {item['name']}")
        page_token = results.get('nextPageToken')
        if not page_token:
            break


results = service.files().list(
    q="name='QRCards' and mimeType='application/vnd.google-apps.folder' and trashed=false",
    fields='files(id, name)',
    spaces='drive',
).execute()
files = results.get('files', [])
if not files:
    print("QRCards folder not found.")
else:
    root_id = files[0]['id']
    print(f"Deleting all contents of QRCards (id: {root_id})...\n")
    delete_children(root_id)
    print("\nAll contents deleted.")

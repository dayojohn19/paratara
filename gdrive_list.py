"""
List all files and subfolders inside the QRCards Google Drive folder,
then return/print a list of direct download links for every file.
Uses the same service account credentials as apis/gdrive_upload.py.

Run:
    python list_gdrive.py
"""

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
_DEFAULT_CRED_PATH = 'thermal-list-338806-4603674b3ae6.json'


def get_service():
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', _DEFAULT_CRED_PATH)
    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)


def list_folder(service, folder_id, folder_name='QRCards', indent=0):
    """Recursively list files/subfolders and return file download metadata."""
    prefix = '  ' * indent
    print(f"{prefix}📁 {folder_name}/")

    collected_files = []

    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='nextPageToken, files(id, name, mimeType, size, createdTime)',
            spaces='drive',
            pageToken=page_token,
            orderBy='folder,name',
        ).execute()

        items = results.get('files', [])
        for item in items:
            is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
            if is_folder:
                collected_files.extend(
                    list_folder(service, item['id'], item['name'], indent + 1)
                )
            else:
                size = item.get('size', '?')
                size_str = f"{int(size):,} bytes" if size != '?' else 'unknown size'
                print(f"{'  ' * (indent + 1)}📄 {item['name']}  ({size_str})")
                collected_files.append(
                    {
                        'name': item['name'],
                        'id': item['id'],
                        'download_url': (
                            f"https://drive.google.com/uc?export=download&id={item['id']}"
                        ),
                    }
                )

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    return collected_files


def main():
    service = get_service()

    root_folder_id = os.getenv('GDRIVE_QR_FOLDER_ID')

    if not root_folder_id:
        # Find the QRCards folder
        results = service.files().list(
            q="name='QRCards' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields='files(id, name)',
            spaces='drive',
        ).execute()
        files = results.get('files', [])
        if not files:
            print("No 'QRCards' folder found in this service account's Drive.")
            return
        root_folder_id = files[0]['id']

    print(f"\nGoogle Drive Structure (folder ID: {root_folder_id})\n")
    files = list_folder(service, root_folder_id)

    print("\nDownload links:")
    if not files:
        print("No files found.")
    else:
        for idx, item in enumerate(files, start=1):
            print(f"{idx}. {item['name']}: {item['download_url']}")

    print("\nDone.")


if __name__ == '__main__':
    main()

def delete_gdrive_file_by_id(file_id):
    """
    Delete a file from Google Drive by its file ID.
    Args:
        file_id (str): The ID of the file to delete.
    Returns:
        bool: True if deleted successfully, False otherwise.
    """
    if not GDRIVE_AVAILABLE:
        raise RuntimeError(
            'google-api-python-client is not installed. '
            'Add google-api-python-client and google-auth to requirements.'
        )
    try:
        service = _get_service()
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"Failed to delete file from Google Drive: {e}")
        return False
"""
Google Drive upload helper for QR card images.

Authenticates via a service account JSON (path from GOOGLE_APPLICATION_CREDENTIALS
env var, falling back to the bundled thermal-list-338806-4603674b3ae6.json file).

Folder structure created/reused on Drive:
  QRCards/
    QR/       ← raw QR code PNGs
    Masters/  ← high-res composite (300 DPI, for print)
    Web/      ← web-optimised composite (for storage / display)

Set GDRIVE_QR_FOLDER_ID in the environment to pin files under an existing
top-level folder; otherwise a "QRCards" folder is created automatically.

To auto-share the root folder, set GDRIVE_QR_SHARE_WITH as comma-separated
emails. Default: johnwebsiteprojects@gmail.com,myworldisadigitallife@gmail.com
"""

import os
import re

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive']
_DEFAULT_CRED_PATH = 'thermal-list-338806-4603674b3ae6.json'


def _get_service():
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', _DEFAULT_CRED_PATH)
    creds = service_account.Credentials.from_service_account_file(
        cred_path, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)


def _get_or_create_folder(service, name, parent_id=None):
    """Return the Drive folder ID for *name*, creating it if it does not exist."""
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        " and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(
        q=query, fields='files(id)', spaces='drive'
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']

    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    folder = service.files().create(body=meta, fields='id').execute()
    return folder['id']


def _make_public(service, file_id):
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()


def _share_folder_with_email(service, folder_id, email):
    if not email:
        return
    service.permissions().create(
        fileId=folder_id,
        body={'type': 'user', 'role': 'writer', 'emailAddress': email},
        sendNotificationEmail=False,
    ).execute()


def _parse_share_emails(raw_value):
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(',') if item.strip()]


def _safe_folder_name(value, fallback='Uncategorized'):
    """Return a Drive-safe folder name with minimal normalization."""
    if value is None:
        return fallback
    cleaned = re.sub(r'[\\/:*?"<>|]+', '_', str(value)).strip()
    return cleaned or fallback


def _upload_stream(service, stream, filename, folder_id, mimetype='image/png'):
    """Upload a BytesIO *stream* to Drive and return its public view URL."""
    stream.seek(0)
    meta = {'name': filename, 'parents': [folder_id]}
    media = MediaIoBaseUpload(stream, mimetype=mimetype, resumable=False)
    f = service.files().create(body=meta, media_body=media, fields='id').execute()
    file_id = f['id']
    _make_public(service, file_id)
    return f'https://drive.google.com/uc?export=view&id={file_id}'


def upload_qr_card_images(
    qr_stream,
    master_stream,
    web_stream,
    name_slug,
    place_folder_name=None,
    collection_folder_name=None,
):
    """
    Upload 3 QR card image streams to Google Drive.

    Args:
        qr_stream:     BytesIO of the raw QR code PNG
        master_stream: BytesIO of the high-res composite PNG (300 DPI)
        web_stream:    BytesIO of the web-optimised composite PNG
        name_slug:     str like "{collectionName}-{collectionUniqueID}"
        place_folder_name: Optional place name used to create
                  Masters/<place_folder_name>/
        collection_folder_name: Optional collection name used to create
                       Masters/<place_folder_name>/<collection_folder_name>/

    Returns:
        Public URL of the web-optimised image (for use as collectionLocalFile).

    Raises:
        RuntimeError if google-api-python-client is not installed.
    """
    if not GDRIVE_AVAILABLE:
        raise RuntimeError(
            'google-api-python-client is not installed. '
            'Add google-api-python-client and google-auth to requirements.'
        )

    service = _get_service()

    root_id = os.getenv('GDRIVE_QR_FOLDER_ID') or _get_or_create_folder(
        service, 'QRCards'
    )

    # Share root folder so it is visible in recipients' "Shared with me".
    share_with_raw = os.getenv(
        'GDRIVE_QR_SHARE_WITH',
        'johnwebsiteprojects@gmail.com,myworldisadigitallife@gmail.com'
    )
    for share_email in _parse_share_emails(share_with_raw):
        try:
            _share_folder_with_email(service, root_id, share_email)
        except Exception as e:
            print(f'Google Drive folder share skipped for {share_email}: {e}')

    qr_folder     = _get_or_create_folder(service, 'QR',      root_id)
    master_folder = _get_or_create_folder(service, 'Masters', root_id)
    master_place_folder = _get_or_create_folder(
        service,
        _safe_folder_name(place_folder_name),
        master_folder,
    )
    master_collection_folder = _get_or_create_folder(
        service,
        _safe_folder_name(collection_folder_name),
        master_place_folder,
    )
    web_folder    = _get_or_create_folder(service, 'Web',     root_id)

    _upload_stream(service, qr_stream,     f'{name_slug}-QR.png',     qr_folder)
    _upload_stream(
        service,
        master_stream,
        f'{name_slug}-MASTER.png',
        master_collection_folder,
    )
    web_url = _upload_stream(service, web_stream, f'{name_slug}.png', web_folder)

    return web_url

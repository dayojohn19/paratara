from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import time
import requests
import base64
from django.conf import settings
try:
    import cloudinary
    import cloudinary.uploader
except Exception:
    cloudinary = None

# Compress image to be under max_size_mb (default 1MB)
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


 



# Legacy IMGBB config removed. Using Cloudinary. Configure via Django settings:
# CLOUDINARY_URL or CLOUDINARY = {"cloud_name":..., "api_key":..., "api_secret":...}


def upload_to_imgbb_with_metadata(file_obj):
    """Upload image to Cloudinary and return metadata.

    Returns a dict like:
      {"url": str, "public_id": str|None, "result": dict}
    (keeps old function name for backward compatibility)
    """
    if cloudinary is None:
        raise RuntimeError('cloudinary library is not installed')

    file_obj = compress_image(file_obj)
    try:
        # Ensure Cloudinary is configured from Django settings if provided
        if getattr(settings, 'CLOUDINARY', None):
            cfg = settings.CLOUDINARY
            cloudinary.config(**cfg)
        elif getattr(settings, 'CLOUDINARY_URL', None):
            cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)

        # Reset file pointer and upload
        try:
            file_obj.seek(0)
        except Exception:
            pass

        res = cloudinary.uploader.upload(file_obj, resource_type='image')
        return {
            'url': res.get('secure_url') or res.get('url'),
            'public_id': res.get('public_id'),
            'result': res,
        }
    except Exception:
        raise


def delete_imgbb_image(public_id: str) -> bool:
    """Best-effort delete of a Cloudinary image by `public_id`.

    Kept function name for backward compatibility.
    """
    if cloudinary is None:
        return False
    public_id = (public_id or '').strip()
    if not public_id:
        return False
    try:
        if getattr(settings, 'CLOUDINARY', None):
            cloudinary.config(**settings.CLOUDINARY)
        elif getattr(settings, 'CLOUDINARY_URL', None):
            cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)
        res = cloudinary.uploader.destroy(public_id, resource_type='image')
        # Cloudinary returns {'result': 'ok'} when deleted, 'not found' otherwise
        return res.get('result') in ('ok', 'not_found')
    except Exception:
        return False

def upload_to_imgbb(file_obj):
    """Upload image to Cloudinary and return secure URL.

    Function kept for backward compatibility with the old name.
    """
    if cloudinary is None:
        raise RuntimeError('cloudinary library is not installed')
    file_obj = compress_image(file_obj)
    try:
        if getattr(settings, 'CLOUDINARY', None):
            cloudinary.config(**settings.CLOUDINARY)
        elif getattr(settings, 'CLOUDINARY_URL', None):
            cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL)

        try:
            file_obj.seek(0)
        except Exception:
            pass

        res = cloudinary.uploader.upload(file_obj, resource_type='image')
        return res.get('secure_url') or res.get('url')
    except Exception:
        raise


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
            return image_url
        else:
            print(f"No image found for {placename}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching Unsplash image: {e}")
        return None


# SMS functionality using Semaphore API
def send_semaphore_sms(phone_number, message):
    """
    Send SMS using Semaphore API
    
    Args:
        phone_number (str): Phone number in international format (+639xxxxxxxxx)
        message (str): SMS message content
    
    Returns:
        dict: API response from Semaphore
    """
    from django.conf import settings
    import requests
    import re
    
    try:
        api_key = settings.SEMAPHORE_API_KEY
        url = 'https://api.semaphore.co/api/v4/messages'
        
        # Clean phone number - remove + and any non-digits
        clean_number = re.sub(r'\D', '', phone_number)
        if clean_number.startswith('63'):
            # Already in correct format
            pass
        elif clean_number.startswith('0'):
            # Convert 09xx to 639xx
            clean_number = '63' + clean_number[1:]
        else:
            # Assume it's missing country code
            clean_number = '63' + clean_number
        
        payload = {
            'apikey': api_key,
            'number': clean_number,
            'message': message,
            'sendername': 'Paratara'
        }
        
        print(f"Sending SMS to {clean_number} (original: {phone_number}) with message: {message}")
        print(f"API URL: {url}")
        print(f"Payload: {payload}")
        
        response = requests.post(url, data=payload, timeout=30)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text[:500]}")  # First 500 chars
        
        if response.status_code == 200:
            # Check if response is JSON or HTML
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                try:
                    result = response.json()
                    print(f"SMS API response: {result}")
                    return result
                except ValueError as e:
                    return {
                        'error': f'Invalid JSON response: {e}',
                        'response_text': response.text[:500]
                    }
            else:
                # HTML response (likely an error message)
                return {
                    'error': 'API returned HTML response (likely account issue)',
                    'response_text': response.text.strip()
                }
        else:
            return {
                'error': f'HTTP {response.status_code}',
                'response_text': response.text[:500]
            }
        
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return {'error': f'Request failed: {str(e)}'}
    except Exception as e:
        print(f"SMS Error: {e}")
        return {'error': str(e)}


def send_twilio_sms(phone_number, message):
    """
    Send SMS using Twilio API
    
    Args:
        phone_number (str): Phone number in international format (+639xxxxxxxxx)
        message (str): SMS message content
    
    Returns:
        dict: API response from Twilio
    """
    from django.conf import settings
    from twilio.rest import Client
    import re
    
    try:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_PHONE_NUMBER
        
        # Clean phone number for Twilio (must be E.164 format: +xxxxxxxxxx)
        clean_number = re.sub(r'\D', '', phone_number)  # Remove all non-digits
        
        if not clean_number.startswith('63'):
            if clean_number.startswith('0'):
                # Convert 09xx to 639xx
                clean_number = '63' + clean_number[1:]
            else:
                # Assume it's missing country code
                clean_number = '63' + clean_number
        
        # Add + prefix for E.164 format
        if not clean_number.startswith('+'):
            clean_number = '+' + clean_number
        
        print(f"Sending Twilio SMS to {clean_number} (original: {phone_number})")
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=clean_number
        )
        
        print(f"Twilio SMS sent: {message.sid}")
        return {
            'success': True,
            'sid': message.sid,
            'status': message.status,
            'to': message.to,
            'from': message.from_
        }
        
    except Exception as e:
        print(f"Twilio SMS Error: {e}")
        return {'error': str(e)}


def send_resort_sms_twilio(resort, message):
    """
    Send SMS to a resort's contact number using Twilio
    
    Args:
        resort: ResortItem instance
        message (str): SMS message content
    """
    if resort.contactNumber:
        return send_twilio_sms(resort.contactNumber, message)
    else:
        print(f"No contact number for resort: {resort.name}")
        return None

from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import time
import requests
import base64

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

    # JPEG does not support alpha. Flatten transparency first, then convert.
    if img.mode in ("RGBA", "LA"):
        base = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.getchannel("A")
        base.paste(img.convert("RGB"), mask=alpha)
        img = base
    elif img.mode == "P":
        # Palette images can carry transparency; convert through RGBA first.
        img = img.convert("RGBA")
        base = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.getchannel("A")
        base.paste(img.convert("RGB"), mask=alpha)
        img = base
    elif img.mode not in ("RGB",):
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


 



# IMGBB_API_KEY = "65ed182b008522d2c762031a3ff4953b"  # get from imgbb.com
IMGBB_API_KEY = "ca7f3a26f5fb6343337e4a4f02c07b12"  # get from imgbb.com repapaka20


def upload_to_imgbb_with_metadata(file_obj):
    """Upload an image to IMGBB and return metadata needed for deletion.

    Returns a dict like:
      {"url": str, "delete_hash": str|None, "delete_url": str|None, "id": str|None}
    """
    file_obj = compress_image(file_obj)
    encoded_image = base64.b64encode(file_obj.read())
    url = "https://api.imgbb.com/1/upload"

    payload = {
        "key": IMGBB_API_KEY,
        "image": encoded_image,
    }

    res = requests.post(url, data=payload)
    res.raise_for_status()
    body = res.json() or {}
    data = body.get("data") or {}
    return {
        "url": data.get("url"),
        "delete_hash": data.get("delete_hash"),
        "delete_url": data.get("delete_url"),
        "id": data.get("id"),
    }


def delete_imgbb_image(delete_hash: str) -> bool:
    """Best-effort delete of an IMGBB image by delete_hash."""
    delete_hash = (delete_hash or "").strip()
    if not delete_hash:
        return False

    url = f"https://api.imgbb.com/1/image/{delete_hash}"
    try:
        res = requests.delete(url, params={"key": IMGBB_API_KEY}, timeout=15)
        if res.ok:
            return True
        # Some environments may block DELETE; try POST as fallback.
        res = requests.post(url, data={"key": IMGBB_API_KEY}, timeout=15)
        return bool(res.ok)
    except Exception:
        return False

def upload_to_imgbb(file_obj):
    # Read file and encode in base64
    file_obj = compress_image(file_obj)
    encoded_image = base64.b64encode(file_obj.read())
    url = "https://api.imgbb.com/1/upload"
    
    payload = {
        "key": IMGBB_API_KEY,
        "image": encoded_image,
    }
    
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()["data"]["url"]  # Get direct image URL

def get_image_url_from_search(query):
    from ddgs import DDGS

    # 'max_results' set to 1 to get the top hit
    with DDGS() as ddgs:
        results = [r for r in ddgs.images(query, max_results=1)]
        if results:
            return results[0]['image']
    return None


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
            print(f"Setting background for from webutils 152 {image_url}")
            resp = requests.get(image_url, timeout=10)
            resp.raise_for_status()
            content = resp.content
            size = len(content)
            return InMemoryUploadedFile(
                BytesIO(content),
                'ImageField',
                f"{placename}.jpg",
                'image/jpeg',
                size,
                None
            )
        else:
            print(f"No image found for {placename} on Unsplash — trying fallback search")
            try:
                fallback = get_image_url_from_search(placename)
                if fallback:
                    print(f"Fallback search found image: {fallback}")
                    image_url = fallback
                    print(f"Setting background for  webutils 172{image_url}")
                    return image_url
                    resp = requests.get(image_url, timeout=10)
                    resp.raise_for_status()
                    content = resp.content
                    size = len(content)
                    return InMemoryUploadedFile(
                        BytesIO(content),
                        'ImageField',
                        f"{placename}.jpg",
                        'image/jpeg',
                        size,
                        None
                    )
                else:
                    print(f"Fallback search returned no image for {placename}")
                    return None
            except Exception as fe:
                print(f"Error during fallback search for {placename}: {fe}")
                return None
    except requests.RequestException as e:
        print(f"Error fetching Unsplash image for {placename}: {e} — trying fallback search")
        try:
            fallback = get_image_url_from_search(placename)
            if fallback:
                print(f"Fallback search found image: {fallback}")
                image_url = fallback
                print(f"Setting background for from 199 from webschedule utils getplacephoto {image_url}")
                resp = requests.get(image_url, timeout=10)
                resp.raise_for_status()
                content = resp.content
                size = len(content)
                return InMemoryUploadedFile(
                    BytesIO(content),
                    'ImageField',
                    f"{placename}.jpg",
                    'image/jpeg',
                    size,
                    None
                )
            else:
                print(f"Fallback search returned no image for {placename}")
                return None
        except Exception as fe:
            print(f"Fallback search also failed for {placename}: {fe}")
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

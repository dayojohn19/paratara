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
    print('\n\n FIle SIZE: ', uploaded_file.size)
    if isinstance(uploaded_file.size, tuple):
    # Choose one number (for example width or height)
        value = uploaded_file.size[0]
        file_size_mb = value / (1024 * 1024)
    else:    
        file_size_mb = uploaded_file.size / (1024 * 1024)
    print('File size (MB): ', file_size_mb)
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

    file_size = output_io.getbuffer().nbytes
    # Create InMemoryUploadedFile so Django can save it
    compressed_file = InMemoryUploadedFile(
        output_io,               # file
        'ImageField',            # field name
        f"{uploaded_file.name.split('.')[0]}_compressed.jpg",  # new filename
        'image/jpeg',            # content type
        file_size,
        # sys.getsizeof(output_io), # size
        # output_io.getbuffer().nbytes,
        None                     # charset
    )
    print('Image compressed.')
    time.sleep(2)
    return compressed_file






IMGBB_API_KEY = "65ed182b008522d2c762031a3ff4953b"  # get from imgbb.com

def upload_to_imgbb(file_obj):
    # Read file and encode in base64
    file_obj = compress_image(file_obj)
    try:
        encoded_image = base64.b64encode(file_obj.read())
    except Exception as e:
        print("Error encoding image to base64:", e)
        # buffer = BytesIO()
        # file_obj.seek(0) 
        encoded_image = base64.b64encode(file_obj.read()).decode('utf-8')
        # encoded_image = base64.b64encode(file_obj.getvalue()).decode("utf-8")
        # with open(file_obj, "rb") as fimage:
        #     encoded_image = base64.b64encode(fimage.read())        
        # encoded_image = file_obj
    url = "https://api.imgbb.com/1/upload"
    
    payload = {
        "key": IMGBB_API_KEY,
        "image": encoded_image,
    }
    
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()["data"]["url"]  # Get direct image URL


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

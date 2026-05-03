"""
Uploading Images to IMBB
upload_to_imgbb(file_obj) - Uploads image file to imgbb and returns the image URL
returns the image URL


"""
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import time

import requests
import base64
 
# IMGBB_API_KEY = "65ed182b008522d2c762031a3ff4953b"  # get from imgbb.com
IMGBB_API_KEY = "ca7f3a26f5fb6343337e4a4f02c07b12"  # get from imgbb.com repapaka20

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



def UploadImage(request):
    if request.method == 'POST':
        print('\n\n\n\n DONE DONE \n\n', request.POST, request.FILES)
        try:
            # ImagePosted = uploadUphotoTry(request)
            # New Way of Uploading Image using imbb
            from webSchedule.utils import upload_to_imgbb
            file_obj = request.FILES.get("image")
            image_url = upload_to_imgbb(file_obj)
            print("\n\n IMAGE URL: ", image_url)
            ImagePosted =image_url
            
        except Exception as e:
            print(e)
            ImagePosted = request.POST['imageURL']
    return ImagePosted
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

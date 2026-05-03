import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from django.core.files.uploadedfile import UploadedFile
import os
 
def uploadtoCloudinary(request, image_file, public_id):
    # Configuration - always set this
    cloudinary.config( 
        cloud_name = "dg6xfou1t", 
        api_key = "875272749645643", 
        api_secret = "1KRVTKh6DiluDJB2SIovyFpizd0", # Click 'View API Keys' above to copy your API secret
        secure=True
    )
    
    # Handle both file paths (strings) and Django UploadedFile objects
    if isinstance(image_file, UploadedFile):
        # For Django UploadedFile objects, upload directly
        upload_result = cloudinary.uploader.upload(image_file, public_id=public_id)
    else:
        # For file paths (existing behavior)
        # Upload an image
        upload_result = cloudinary.uploader.upload(image_file, public_id=public_id)
    
    print(upload_result["secure_url"])

    # Optimize delivery by resizing and applying auto-format and auto-quality
    optimize_url, _ = cloudinary_url(public_id, fetch_format="auto", quality="auto")
    print(optimize_url)
    # Transform the image: auto-crop to square aspect_ratio
    auto_crop_url, _ = cloudinary_url(public_id, width=500, height=500, crop="auto", gravity="auto")
    print(auto_crop_url)

    return upload_result["secure_url"]

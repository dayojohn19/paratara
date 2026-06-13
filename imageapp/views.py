from django.shortcuts import render
from .models import googleimagemodel
# Create your views here.

from django.http import JsonResponse
from django.conf import settings
from django.utils.text import slugify
import os
import time
import uuid
import io

try:
    from pillow_heif import register_heif_opener
except ImportError:
    register_heif_opener = None
else:
    register_heif_opener()

# def getimages(request, placename):
#     allimages = googleimagemodel.objects.filter(imageclassID=placename)
#     # return in json allimages.imbbURL and allimages.imageclassID

def getimages(request, placename):
    # Filter images by imageclassID
    allimages = googleimagemodel.objects.filter(imageclassID=placename)

    # Create a list of dicts with the fields you want
    images_list = [
        {"imbbURL": img.imbbURL.url if hasattr(img.imbbURL, "url") else img.imbbURL,
         "imageclassID": img.imageclassID}
        for img in allimages
    ]

    return JsonResponse({"images": images_list})





def _blur_faces(image):
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise ValueError("opencv-python-headless is required to detect and blur faces") from error

    cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        raise ValueError("OpenCV face detector could not be loaded")

    from PIL import ImageFilter

    rgb_image = image.convert("RGB")
    cv_image = cv2.cvtColor(np.array(rgb_image), cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(
        cv_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
    )

    if len(faces) == 0:
        return image

    blurred_image = image.copy()
    width, height = blurred_image.size
    for x, y, face_width, face_height in faces:
        padding_x = int(face_width * 0.18)
        padding_y = int(face_height * 0.24)
        left = max(0, x - padding_x)
        top = max(0, y - padding_y)
        right = min(width, x + face_width + padding_x)
        bottom = min(height, y + face_height + padding_y)
        face_region = blurred_image.crop((left, top, right, bottom))
        blur_radius = max(12, min(face_width, face_height) // 3)
        face_region = face_region.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        blurred_image.paste(face_region, (left, top))

    return blurred_image


def _save_blog_editor_webp(request):
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as error:
        raise ValueError("Pillow is required to convert blog images to WebP") from error
    if register_heif_opener:
        register_heif_opener()

    place_slug = slugify(request.POST.get("blog_place_slug") or request.POST.get("imageclassID") or "")
    title_slug = slugify(request.POST.get("blog_title_slug") or "blog")

    if not place_slug:
        raise ValueError("Missing blog place slug")

    uploaded_file = request.FILES["image"]
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    blogs_root = os.path.abspath(os.path.join(settings.BASE_DIR, "singlepage2", "templates", "blogs"))
    place_dir = os.path.abspath(os.path.join(blogs_root, place_slug))
    assets_dir = os.path.abspath(os.path.join(place_dir, "assets"))

    if os.path.commonpath([blogs_root, assets_dir]) != blogs_root:
        raise ValueError("Invalid blog asset path")

    os.makedirs(assets_dir, exist_ok=True)
    requested_name = slugify(request.POST.get("image_name") or "")
    if requested_name:
        filename = f"{requested_name}.webp"
        file_path = os.path.join(assets_dir, filename)
        suffix = 2
        while os.path.exists(file_path):
            filename = f"{requested_name}-{suffix}.webp"
            file_path = os.path.join(assets_dir, filename)
            suffix += 1
    else:
        filename = f"{title_slug}-{int(time.time())}-{uuid.uuid4().hex[:8]}.webp"
        file_path = os.path.join(assets_dir, filename)

    try:
        with Image.open(uploaded_file) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            image = _blur_faces(image)

            # Iteratively reduce WebP size to fit under 99KB.
            max_bytes = 99 * 1024
            quality_start = 84
            quality_min = 40
            quality_step = 4
            scale = 1.0
            scale_min = 0.50
            scale_step = 0.90

            base_image = image
            encoded = None

            while scale >= scale_min and encoded is None:
                if scale < 1.0:
                    w, h = base_image.size
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    working = base_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                else:
                    working = base_image

                quality = quality_start
                while quality >= quality_min:
                    buf = io.BytesIO()
                    working.save(buf, "WEBP", quality=quality, method=6)
                    data = buf.getvalue()
                    if len(data) <= max_bytes:
                        encoded = data
                        break
                    quality -= quality_step

                if encoded is None:
                    scale *= scale_step
    except UnidentifiedImageError as error:
        raise ValueError(
            "Unsupported image format. Phone camera HEIC/HEIF images need pillow-heif installed or must be converted to JPEG before upload."
        ) from error

    if encoded is None:
        raise ValueError("Could not compress image under 99KB")

    with open(file_path, "wb") as f:
        f.write(encoded)

    return {
        "file_path": file_path,
        "filename": filename,
        "image_url": f"/pages/blog/{place_slug}/assets/{filename}",
        "imageclassID": place_slug,
    }


def uploadimage(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "POST required"}, status=405)

    if "image" not in request.FILES:
        return JsonResponse({"status": "error", "error": "No image file provided"}, status=400)

    if request.POST.get("source") == "blog_inline_editor" or request.POST.get("blog_place_slug"):
        try:
            saved_image = _save_blog_editor_webp(request)
        except Exception as error:
            return JsonResponse({"status": "error", "error": str(error)}, status=400)

        newimage = googleimagemodel.objects.create(
            imageclassID=saved_image["imageclassID"],
            imbbURL=saved_image["image_url"],
        )

        return JsonResponse({
            "status": "success",
            "image_id": newimage.id,
            "image_url": saved_image["image_url"],
            "imbbURL": saved_image["image_url"],
            "imageclassID": saved_image["imageclassID"],
            "filename": saved_image["filename"],
            "file_path": saved_image["file_path"],
            "format": "webp",
            "storage": "local_blog_assets",
        })

    from imageapp.imageuploader import Upload_and_get_URL
    imgurl = Upload_and_get_URL(request)

    if not imgurl or not isinstance(imgurl, str):
        return JsonResponse({"status": "error", "error": "Image upload failed"}, status=400)

    newimage = googleimagemodel.objects.create(imageclassID=request.POST.get("imageclassID"), imbbURL=imgurl)

    return JsonResponse({
        "status": "success",
        "image_id": newimage.id,
        "image_url": imgurl,
        "imbbURL": imgurl,
        "imageclassID": newimage.imageclassID,
    })
    # return JsonResponse({"status": "error"}, status=400)

# class googleimagemodel(models.Model):
#     ### ForeignKey('userProfile.userPoster',on_delete=models.CASCADE,null=True)
#     imageclassID = models.IntegerField(default=0)
#     usesrID = models.IntegerField(default=0)
#     timesmtamp = models.DateTimeField(auto_now_add=True)
#     imbbURL = models.URLField(blank=True)
#     googleURL = models.URLField(blank=True)

# Upload_and_get_URL(request) with files
# return url

# on html


# <form action="{% url 'imageapp:uploadimage' %}" method="POST" enctype="multipart/form-data" class="p-3 border rounded">
#     <div class="mb-3">
#         {% csrf_token %}
#         <label for="formFile" class="form-label">Upload an image</label>
#         <input required="" class="form-control" type="file" id="formFile" name="image" accept="image/*">
#     </div>
#     <button type="submit" class="btn btn-primary">Try Image</button>
# </form>



"""
USES

Upload_and_get_URL(request) with files
return [url_to_use, url_to_backup]

def getPlacePhoto(request, placename)
return 'url_photo'

https://john-christoper.imgbb.com

"""

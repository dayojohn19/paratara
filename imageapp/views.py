from django.shortcuts import render
from .models import googleimagemodel
# Create your views here.

from django.http import JsonResponse
from django.conf import settings
from django.utils.text import slugify
import os
import time
import uuid

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





def _save_blog_editor_webp(request):
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise ValueError("Pillow is required to convert blog images to WebP") from error

    place_slug = slugify(request.POST.get("blog_place_slug") or request.POST.get("imageclassID") or "")
    title_slug = slugify(request.POST.get("blog_title_slug") or "blog")

    if not place_slug:
        raise ValueError("Missing blog place slug")

    uploaded_file = request.FILES["image"]
    blogs_root = os.path.abspath(os.path.join(settings.BASE_DIR, "singlepage2", "templates", "blogs"))
    place_dir = os.path.abspath(os.path.join(blogs_root, place_slug))
    assets_dir = os.path.abspath(os.path.join(place_dir, "assets"))

    if os.path.commonpath([blogs_root, assets_dir]) != blogs_root:
        raise ValueError("Invalid blog asset path")

    os.makedirs(assets_dir, exist_ok=True)
    filename = f"{title_slug}-{int(time.time())}-{uuid.uuid4().hex[:8]}.webp"
    file_path = os.path.join(assets_dir, filename)

    with Image.open(uploaded_file) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        image.save(file_path, "WEBP", quality=84, method=6)

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

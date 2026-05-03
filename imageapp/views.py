from django.shortcuts import render
from .models import googleimagemodel
# Create your views here.

from django.http import JsonResponse

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





def uploadimage(request):
    from imageapp.imageuploader import Upload_and_get_URL
    imgurl = Upload_and_get_URL(request)
    request.POST.get("imageclassID")
    newimage = googleimagemodel.objects.create(imageclassID = request.POST.get("imageclassID"), imbbURL = imgurl )

    return JsonResponse({"status": "success"})
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
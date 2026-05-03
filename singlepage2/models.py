from django.db import models

# Create your models here.


class TravelPages2(models.Model):
    html_title = models.CharField(max_length=264)
    html_body = models.TextField()


class ImageUploadsModel(models.Model):
    title = models.CharField(max_length=100,blank=True, null=True)
    image = models.ImageField(upload_to='imageuploads/')
    image_url = models.URLField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
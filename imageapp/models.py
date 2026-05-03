from django.db import models

# Create your models here.
from django_resized import ResizedImageField

class googleimagemodel(models.Model):
    ### ForeignKey('userProfile.userPoster',on_delete=models.CASCADE,null=True)
    imageclassID = models.CharField(max_length=500,blank=True,null=True)
    usesrID = models.IntegerField(default=0)
    timesmtamp = models.DateTimeField(auto_now_add=True)
    imbbURL = models.URLField(blank=True)
    googleURL = models.URLField(blank=True)
    image = ResizedImageField(size=[400, 400], crop=[
                              'middle', 'center'], quality=50, upload_to='imageuploaded', blank=True, null=True)
    def __str__(self):
        return f"{self.imageclassID} {self.imbbURL}"

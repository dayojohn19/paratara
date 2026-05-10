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
    description = models.TextField(blank=True)
    # IP tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # TODO GET GEOLOCATOPN HERE from django.contrib.gis.geoip2 import GeoIP2
    ip_location = models.JSONField(null=True,blank=True)
    # Analytics
    source = models.CharField(max_length=100, blank=True, help_text='Where they subscribed from')
    referrer_url = models.URLField(blank=True)
    user_agent = models.TextField(blank=True)
    unsubscribe_reason = models.TextField(blank=True)    

    # Timestamps
    subscribed_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    unsubscribed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.imageclassID} {self.imbbURL}"

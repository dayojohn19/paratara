from django.db import models
from django.urls import reverse
# Create your models here.
from datetime import datetime
import ast
import json
from django.utils.text import slugify
class RequestPage(models.Model):
    page_name = models.CharField(max_length=555)
    requesting_ip = models.GenericIPAddressField()
    timesmtamp = models.DateTimeField(auto_now_add=True)
    def readable_last_request(self):
            if self.timesmtamp:
                return self.timesmtamp.strftime("%B %d, %Y, %I:%M %p")  # e.g., September 16, 2025, 01:45 PM
            return "N/A"

    def __str__(self):
        return f"{self.requesting_ip}       ->    {self.page_name} at {self.readable_last_request()}  "

class RequestLog(models.Model):
    # requestPages = models.ForeignKey('home.RequestPage', on_delete=models.CASCADE, related_name='requestLogs', null=True)
    requestPages = models.ManyToManyField('home.RequestPage', blank=True, related_name='requestLogsList')
    ip_location_json = models.JSONField(blank=True, null=True)
    
    # ip_location = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    last_request = models.DateTimeField(auto_now=True)
    page = models.CharField(max_length=555)
    method = models.CharField(max_length=10)
    count = models.PositiveIntegerField(default=1)
    timesmtamp = models.DateTimeField(auto_now_add=True)
    
    def readable_last_request(self):
            if self.last_request:
                return self.last_request.strftime("%B %d, %Y, %I:%M %p")  # e.g., September 16, 2025, 01:45 PM
            return "N/A"



    class Meta:
        unique_together = ('ip_address', 'page')  # optional, per page/IP combination
    def __str__(self):
        # Safely extract nested fields from ip_location_json
        city = (
            self.ip_location_json.get("city_info", {}).get("city")
            if self.ip_location_json else None
        )
        time_zone = (
            self.ip_location_json.get("city_info", {}).get("time_zone")
            if self.ip_location_json else None
        )

        # Fallbacks for missing data
        city = city or "Unknown city"
        time_zone = time_zone or "Unknown timezone"

        return f"{city} | {time_zone} --  {self.last_request.strftime('%B %d, %Y, %I:%M %p')}  ----- {self.ip_address} |  --- {self.page} ({self.count} times)"        
    # def __str__(self):
    #     country = self.ip_location_json if self.ip_location_json else 'Unknown'
    #     return f"{self.ip_address} -> {self.readable_last_request()} -> {self.page} {country}"
    # def __str__(self):
    #     # return f"{self.ip_address} -> {self.page} ({self.count} times)"
    #     return f"{self.count}  {self.readable_last_request()}   "

class Comment(models.Model):
    senderID = models.IntegerField(default=0)
    message = models.TextField()
    messanger = models.CharField(max_length=64)
    sender = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, null=True)
    schedule = models.ForeignKey('home.allSchedules', on_delete=models.CASCADE, related_name='postSchedule', null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    origin = models.CharField(max_length=64, default='website')

    def __str__(self):
        return f"{self.sender}:{self.message[:30]}"

    @property
    def messageSummary(self):
        return self.message[:30]

    class Meta:
        ordering = ["-id"]


class SchedTypeAndMode(models.Model):
    modeName = models.CharField(max_length=24)
    scheduleObject = models.ManyToManyField(
        'home.allSchedules', blank=True, related_name='SchedLists')

    @property
    def ScheduleLists(self):
        return self.scheduleObject.all()

class SiargaoEventSchedule(models.Model):
    place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='eventPlace', null=True, blank=True)
    exactDate = models.CharField(max_length=304, blank=True)
    # Basic poster / host info
    posterName = models.CharField(max_length=64, default='Anonymous')
    posterURL = models.URLField(blank=True, default="http://none.com")
    posterImageURL = models.URLField(blank=True)
    posterVerified = models.BooleanField(default=False)
    posterID = models.IntegerField(default=0)
    posterReputation = models.IntegerField(default=0)
    
    # Event / schedule info
    scheduleTitle = models.CharField(max_length=200, blank=True)
    scheduleWebsite = models.URLField(blank=True, null=True)
    scheduleImageURL = models.URLField(blank=True)
    scheduleTypeAndMode = models.CharField(max_length=64, blank=True, null=True)
    schedulePlace = models.CharField(max_length=255, blank=True)  # location text
    meetPlace = models.CharField(max_length=64, blank=True)
    meetTime = models.CharField(max_length=24, blank=True, null=True)
    endDate = models.CharField(max_length=64, blank=True)
    scheduleCost = models.CharField(max_length=64, blank=True)
    
    # Dates
    dateN = models.IntegerField(default=datetime.now().day, blank=True)
    monthN = models.IntegerField(default=datetime.now().month, blank=True)
    yearN = models.IntegerField(default=datetime.now().year, blank=True)
    
    # Description / additional info
    additionalDetails = models.TextField(blank=True)
    otherDetails = models.TextField(blank=True, null=True)
    locations_json = models.TextField(blank=True)  # store the data-locations JSON
    backgroundURL = models.URLField(blank=True)
    thumbnailURL = models.URLField(blank=True)
    markerURL = models.URLField(blank=True)
    
    # Host info
    host_name = models.CharField(max_length=64, blank=True)
    host_link = models.URLField(blank=True)
    
    # Meta
    fetchID = models.IntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def get_locations(self):
        """Return locations as Python objects."""
        if self.locations_json:
            try:
                return json.loads(self.locations_json)
            except json.JSONDecodeError:
                return []
        return []

    def __str__(self):
        return f"{self.scheduleTitle} - {self.dateN}/{self.monthN}/{self.yearN}"

class allSchedules(models.Model):
    fetchID = models.IntegerField(default=1)
    comment = models.ManyToManyField(
        'home.Comment', blank=True, related_name='commentList')
    # poster = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE, null=True, blank=True)
    detailsContact = models.CharField(max_length=94, default='+639568543802')
    #
    posterVerified = models.BooleanField(default=False)
    posterID = models.IntegerField(default=1)
    posterName = models.CharField(max_length=64, default='Anonymous')
    posterURL = models.URLField(blank=True, default="http://none.com", )
    posterImageURL = models.URLField(blank=True)
    scheduleImageURL = models.URLField(blank=True, default=0)
    posterReputation = models.IntegerField(default=0)
    #
    scheduleID = models.IntegerField(null=True, blank=True)
    posterInstagram = models.CharField(max_length=64, blank=True)
    # dateN= models.IntegerField(null=True, blank=True)
    dateN = models.IntegerField(default=datetime.now().day, blank=True)
    monthN = models.IntegerField(blank=True, default=datetime.now().month)
    yearN = models.IntegerField(blank=True, default=datetime.now().year)
    additionalDetails = models.TextField(blank=True)
    otherDetails = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    reviewCount = models.IntegerField(default=0)
    schedulePlace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='arrivingTo', null=True)
    meetPlace = models.CharField(max_length=64, blank=True)
    meetTime = models.CharField(max_length=24, blank=True, null=True)
    endDate = models.CharField(max_length=64, blank=True)
    scheduleTitle = models.CharField(max_length=64, blank=True)
    scheduleCost = models.CharField(max_length=64, blank=True)
    scheduleWebsite = models.URLField(blank=True, null=True)
    scheduleTypeAndMode = models.CharField(max_length=34, blank=True, null=True)
    # scheduleTypeAndMode = models.ForeignKey('home.SchedTypeAndMode', on_delete=models.CASCADE, related_name='typeandmode', null=True, blank=True)
    scheduleTravelType = models.CharField(max_length=64, blank=True)
    MakerOrLooker = models.CharField(max_length=64, blank=True)

    def serialize(self):
        return {
            "aasdadasd": 'asdasda'
        }

    @property
    def posterAllDetails(self):
        return self.poster

    @property
    def comments(self):
        return self.comment.all().reverse()

    @property
    def commentCount(self):
        return self.comment.count()

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"Sched ID: {self.id} {self.schedulePlace}"

    def get_absolute_url(self):
        return reverse("home:schedule_detail", args=[str(self.id)])

 
class Places_v2(models.Model):
    slug = models.SlugField(blank=True,unique=True)
    blog = models.ManyToManyField('apis.Blogs', blank=True, related_name="bloglists")
    reviewCount = models.IntegerField(default=0)
    placeID = models.IntegerField(blank=True, null=True, default=0)
    placename = models.CharField(max_length=64)
    eventSchedules = models.ManyToManyField('home.SiargaoEventSchedule', blank=True, related_name='eventSchedulesLists')
    placesSchedules = models.ManyToManyField(
        allSchedules, blank=True, related_name='allScheds')

    placePhoto = models.CharField(blank=True, max_length=9999, null=True)

    discussion = models.ManyToManyField(
        'home.PlaceDiscussion', blank=True, related_name='discussionsLists')
    # resortItems = models.ManyToManyField('resorts.resortItem',null=True, blank=True,related_name="RESORTS_OF_PLACE")
    resortItem = models.ManyToManyField(
        'resorts.resortItem', blank=True, related_name="RESORTS_OF_PLACE")
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.placename)
        super().save(*args, **kwargs)
    def get_absolute_url(self):
        return reverse('home:checkPlaceSlug', kwargs={'slug': self.slug})
        
    def serialize(self):
        return {
            "placeID": self.placeID,
            "placeName": self.placename
        }

    def __str__(self):
        return f"{self.placename}"
    @property
    def blogs(self):
        return self.blog.all()

    @property
    def SchedList(self):
        return self.placesSchedules.all()

    @property
    def eventList(self):
        return self.eventSchedules.all()

    @property
    def resortList(self):
        return self.resortItem.all()

    @property
    def SchedListCount(self):
        return self.placesSchedules.count()

    @property
    def discussions(self):
        return self.discussion.all()

    class Meta:
        ordering = ["-id"]


class PlaceDiscussion(models.Model):
    # schedulePlace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='arrivingTo', null=True)

    place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='placediscuss', null= True)
    discuss = models.TextField()
    # discusser = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE,related_name='discusserUser', blank=True, null=True)
    discusserName = models.CharField(max_length=64, default='ANONYMOUS')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.place}: {self.discuss}"
    # class Meta:
    #     ordering = ["-id"]


class ResortMessages(models.Model):
    guestName = models.CharField(default='Anonymous', max_length=32)
    resortID = models.IntegerField()
    guestMessage = models.TextField()
    guestContact = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.guestMessage} ___ {self.guestContact}"

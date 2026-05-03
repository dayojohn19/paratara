from django.db import models
from django.urls import reverse
# Create your models here.
from datetime import datetime
import ast
import json
from django.utils.text import slugify
from django.utils import timezone

class BlockedIP(models.Model):
    """Track blocked IPs and their expiration time"""
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    reason = models.CharField(max_length=255, default="Too many 404 errors")
    
    def is_active(self):
        """Check if the IP block is still active"""
        return timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Blocked: {self.ip_address} until {self.expires_at.strftime('%B %d, %Y, %I:%M %p')}"

class RequestPage(models.Model):
    page_name = models.CharField(max_length=555)
    requesting_ip = models.GenericIPAddressField()
    timesmtamp = models.DateTimeField(auto_now_add=True)
    status_code = models.IntegerField(default=200)  # Track HTTP status code
    
    def readable_last_request(self):
            if self.timesmtamp:
                return self.timesmtamp.strftime("%B %d, %Y, %I:%M %p")  # e.g., September 16, 2025, 01:45 PM
            return "N/A"
    
    def is_404(self):
        """Check if this request resulted in a 404 error"""
        return self.status_code == 404
    
    @classmethod
    def is_page_404(cls, page_name):
        """Check if a specific page_name has any 404 errors"""
        return cls.objects.filter(page_name=page_name, status_code=404).exists()
    
    @classmethod
    def get_404_count_for_page(cls, page_name):
        """Get count of 404 errors for a specific page_name"""
        return cls.objects.filter(page_name=page_name, status_code=404).count()

    def __str__(self):
        return f"{self.requesting_ip}       ->    {self.page_name} at {self.readable_last_request()}  "


class RequestPageSummary(models.Model):
    requesting_ip = models.GenericIPAddressField(unique=True)
    ip_location_json = models.JSONField(blank=True, null=True)
    city = models.CharField(max_length=128, blank=True, null=True)
    country_name = models.CharField(max_length=128, blank=True, null=True)
    continent_name = models.CharField(max_length=128, blank=True, null=True)
    pages_json = models.JSONField(default=dict, blank=True)
    total_requests = models.PositiveIntegerField(default=0)
    unique_pages = models.PositiveIntegerField(default=0)
    earliest_timesmtamp = models.DateTimeField(null=True, blank=True)
    latest_timesmtamp = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # ordering = ["-updated_at", "-latest_timesmtamp", "unique_pages"]
        ordering = ["earliest_timesmtamp", "-latest_timesmtamp", "unique_pages"]

    def __str__(self):
        earliest = self.earliest_timesmtamp.strftime("%B %d, %Y, %I:%M %p") if self.earliest_timesmtamp else "N/A"
        latest = self.latest_timesmtamp.strftime("%B %d, %Y, %I:%M %p") if self.latest_timesmtamp else "N/A"
        location = ""
        if self.continent_name or self.country_name or self.city:
            parts = [p for p in [self.continent_name, self.country_name, self.city] if p]
            location = " " + " / ".join(parts)
        return f"-{earliest} -> {latest} | {location} | {self.total_requests} req | {self.requesting_ip} |  {self.unique_pages} pages "
 
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

    def get_full_url(self):
        """Construct the full URL from the page field"""
        base_url = "http://127.0.0.1:8000"
        return f"{base_url}{self.page}"

    def check_if_404(self):
        """Check if any of the related RequestPage objects have a 404 status code"""
        return self.requestPages.filter(status_code=404).exists()

    def get_404_count(self):
        """Get the count of 404 errors for this RequestLog"""
        return self.requestPages.filter(status_code=404).count()

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

        return f"{time_zone} | {city} --  {self.last_request.strftime('%B %d, %Y, %I:%M %p')}  | {self.ip_address} |   {self.page} ({self.count} times)"        
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
    # Optional link to a resort package item that generated this event
    package = models.ForeignKey(
        'resorts.Packages',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='siargao_event_schedules'
    )
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
    endPlace = models.CharField(max_length=64, blank=True)
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


class SiargaoEventRegistrant(models.Model):
    event = models.ForeignKey(
        'home.SiargaoEventSchedule',
        on_delete=models.CASCADE,
        related_name='registrants'
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    event_date = models.CharField(max_length=304, blank=True)
    pax = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['event', 'email'], name='uniq_siargao_event_reg_email')
        ]

    def __str__(self):
        return f"{self.full_name}... ({self.event_date}) -> {self.event.scheduleTitle}"

class Joiner(models.Model):
    user = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, null=True)
    schedule = models.ForeignKey('home.allSchedules', on_delete=models.CASCADE, related_name='joinerList', null=True)
    contact = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    pickLocation = models.CharField(max_length=128, blank=True)
    pickCoordinate = models.CharField(max_length=128, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    def __str__(self):
        return f"{self.user} joined {self.schedule}"
        
 

class CommunityBulletinPost(models.Model):
    place = models.ForeignKey(
        'home.Places_v2',
        on_delete=models.CASCADE,
        related_name='community_bulletin_posts',
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    ai_title = models.CharField(max_length=160, blank=True)
    ai_description = models.TextField(blank=True)

    # Social posting state
    social_posting = models.BooleanField(default=False)
    social_posted_at = models.DateTimeField(blank=True, null=True)
    social_last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.place_id:
            place_name = getattr(getattr(self, 'place', None), 'placename', None)
            if place_name:
                prefix = f"Community Bulletin for {place_name}".strip()
                place_link = None
                try:
                    from django.conf import settings
                    base_url = (getattr(settings, 'SITE_URL', None) or 'https://paratara.com').rstrip('/')
                    place_path = None
                    try:
                        place_path = self.place.get_absolute_url()
                    except Exception:
                        place_path = None
                    if place_path:
                        place_link = f"{base_url}{place_path}"
                except Exception:
                    place_link = None

                desc = (self.ai_description or '').strip()
                if not desc:
                    self.ai_description = f"{prefix}\n{place_link}".strip() if place_link else prefix
                else:
                    updated = desc
                    if not updated.lower().startswith(prefix.lower()):
                        header = f"{prefix}\n{place_link}".strip() if place_link else prefix
                        updated = f"{header}\n\n{updated}".strip()
                    elif place_link and (place_link not in updated):
                        # Insert link right after the first line (the prefix)
                        lines = updated.splitlines()
                        if lines:
                            lines.insert(1, place_link)
                            updated = "\n".join(lines).strip()
                    self.ai_description = updated
        super().save(*args, **kwargs)

    def __str__(self):
        title = (self.ai_title or '').strip() or 'Bulletin post'
        return f"{title} ({self.place_id})"


def _community_bulletin_upload_path(instance, filename: str) -> str:
    return f"community_bulletin/place_{instance.post.place_id}/post_{instance.post_id}/{filename}"


class CommunityBulletinImage(models.Model):
    post = models.ForeignKey(
        'home.CommunityBulletinPost',
        on_delete=models.CASCADE,
        related_name='images',
    )
    image_url = models.URLField(max_length=2000,blank=True,null=True)
    imgbb_delete_hash = models.CharField(max_length=64, blank=True, null=True)
    imgbb_delete_url = models.URLField(max_length=2000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Image {self.id} for post {self.post_id}"


class FacebookPagePost(models.Model):
    """Mirror posts from a Facebook Page onto the website.

    Populated by a scheduled management command that calls the Graph API.
    """

    fb_post_id = models.CharField(max_length=128, unique=True)
    message = models.TextField(blank=True)
    permalink_url = models.URLField(max_length=2000, blank=True)
    created_time = models.DateTimeField(blank=True, null=True)
    media_json = models.JSONField(blank=True, null=True)
    raw_json = models.JSONField(blank=True, null=True)

    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_time", "-imported_at"]
 
    def __str__(self):
        return f"FB {self.fb_post_id}"

class allSchedules(models.Model):
    SCHEDULE_TYPE_CHOICES = [
        ('carpool', 'Carpool'),
        # ('tour', 'Tour'),
    ]
    scheduleTypeAndMode = models.CharField(max_length=34, choices=SCHEDULE_TYPE_CHOICES, blank=True, null=True)
    dateN = models.IntegerField(default=datetime.now().day, blank=True)
    monthN = models.IntegerField(blank=True, default=datetime.now().month)
    yearN = models.IntegerField(blank=True, default=datetime.now().year)    
    schedulePlace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='arrivingTo', null=True)
    meetPlace = models.CharField(max_length=64, blank=True)
    endPlace = models.CharField(max_length=64, blank=True)
    joinerUser = models.ManyToManyField('home.Joiner', blank=True, related_name='joinerUsers')
    comment = models.ManyToManyField('home.Comment', blank=True, related_name='commentList')
    poster = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, null=True)
    meetTime = models.CharField(max_length=24, blank=True, null=True)




    posterName = models.CharField(max_length=64, default='Anonymous')
    posterURL = models.URLField(blank=True, default="http://none.com", )
    posterImageURL = models.URLField(blank=True)
    scheduleImageURL = models.URLField(blank=True, default=0)
    detailsContact = models.CharField(max_length=94, default='')
    posterReputation = models.IntegerField(default=0)

    fetchID = models.IntegerField(default=1)
    # poster = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE, null=True, blank=True)
    #
    posterVerified = models.BooleanField(default=False)
    posterID = models.IntegerField(default=1)
    #
    scheduleID = models.IntegerField(null=True, blank=True)
    posterInstagram = models.CharField(max_length=64, blank=True)
    # dateN= models.IntegerField(null=True, blank=True)

    additionalDetails = models.TextField(blank=True)
    otherDetails = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    reviewCount = models.IntegerField(default=0)


    
    endDate = models.CharField(max_length=64, blank=True)
    scheduleTitle = models.CharField(max_length=64, blank=True)
    scheduleCost = models.CharField(max_length=64, blank=True)
    scheduleWebsite = models.URLField(blank=True, null=True)
    
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

 
class FacebookPage(models.Model):
    page_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    link = models.URLField(max_length=2000, blank=True)
    about = models.TextField(blank=True)
    category = models.CharField(max_length=128, blank=True)
    created_time = models.DateTimeField(blank=True, null=True)
    raw_json = models.JSONField(blank=True, null=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return f"FB Page: {self.name} ({self.page_id})"


class Places_v2(models.Model):
    slug = models.SlugField(blank=True,unique=True)
    blog = models.ManyToManyField('apis.Blogs', blank=True, related_name="bloglists")
    reviewCount = models.IntegerField(default=0)
    placeID = models.IntegerField(blank=True, null=True, default=0)
    placename = models.CharField(max_length=64)
    eventSchedules = models.ManyToManyField('home.SiargaoEventSchedule', blank=True, related_name='eventSchedulesLists')
    placesSchedules = models.ManyToManyField(
        allSchedules, blank=True, related_name='allScheds')

    facebook_pages = models.ManyToManyField(
        FacebookPage, blank=True, related_name='places')

    placePhoto = models.CharField(blank=True, max_length=9999, null=True)

    discussion = models.ManyToManyField(
        'home.PlaceDiscussion', blank=True, related_name='discussionsLists')
    # resortItems = models.ManyToManyField('resorts.resortItem',null=True, blank=True,related_name="RESORTS_OF_PLACE")
    resortItem = models.ManyToManyField(
        'resorts.resortItem', blank=True, related_name="RESORTS_OF_PLACE")
    def save(self, *args, **kwargs):
        # Auto-generate a unique slug from placename if missing
        if not self.slug:
            base_slug = slugify(self.placename) or f"place-{self.id or ''}".strip('-')
            slug = base_slug
            i = 1
            while Places_v2.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
        # Ensure placeID is always equal to the object's id
        if self.placeID != self.id:
            self.placeID = self.id
            super().save(update_fields=["placeID"])
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
        return self.blog.all().order_by('-timestamp')

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


class Visit(models.Model):
    tourist_spot = models.ForeignKey('home.TouristSpot', on_delete=models.CASCADE)
    tourist = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.tourist} visited {self.tourist_spot} at {self.timestamp}"


class TouristSpot(models.Model):
    place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='tourist_spots')
    spot_id = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    desc = models.TextField(blank=True)
    coords = models.JSONField(blank=True, null=True)
    img = models.URLField(null=True,blank=True, max_length=500)
    qr_code_url = models.URLField(blank=True, max_length=500)
    url = models.URLField(null=True, blank=True, max_length=500)

    resortItem = models.ManyToManyField('resorts.resortItem', blank=True, related_name="TOURIST_SPOTS_OF_RESORT")
    tourists = models.ManyToManyField('userProfile.UserCredentials', through='home.Visit', related_name='visited_spots')
    tourguide = models.ManyToManyField('userProfile.TourGuide', blank=True, related_name='spots_guided')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} in {self.place}"
    @property
    def tourGuides(self):
        return self.tourguide.all()
    @property
    def resortList(self):
        return self.resortItem.all()


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

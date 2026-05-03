from django.apps import apps
from django.db import models
from django.urls import reverse
# Create your models here.

from django.utils.text import slugify







class InactiveResortItem(models.Model):
    resortGallery = models.ManyToManyField('resorts.sideImagesURLs', blank=True)
    resortQRLink = models.URLField(null=True, blank=True)
    websiteURL = models.CharField(max_length=512, null=True, blank=True)
    resortAccomodations = models.ManyToManyField('resorts.resortPackages', blank=True, related_name="inactive_packages_of_accomodations")
    resortSchedules = models.ManyToManyField('home.allSchedules', blank=True, related_name="inactive_resortScheduleList")
    adminManager = models.ManyToManyField('userProfile.UserCredentials', blank=True, related_name="inactive_resortAdmins")
    registeredBy = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, blank=True, null=True, related_name="inactive_registeredBy")
    resort_ID = models.IntegerField(default=0)
    name = models.CharField(max_length=64, blank=True)
    RealName = models.CharField(max_length=64, blank=True)
    address = models.CharField(max_length=128, blank=True)
    place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, blank=True, null=True, related_name='InactiveEstablishmentPlace')
    contactNumber = models.CharField(max_length=128, blank=True)
    contactEmail = models.CharField(max_length=128, blank=True)
    whatsappNumber = models.CharField(max_length=128, blank=True)
    open_hours = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Example: Mon–Sun 8:00 AM – 9:00 PM"
    )
    promotionalVideo = models.URLField(blank=True)
    virtualpicture = models.URLField(blank=True)
    headerImage = models.URLField(blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    reviews = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    resortActivities = models.ManyToManyField('resorts.resortPackages', blank=True, related_name="inactive_packages_of_activities")
    resortTour = models.ManyToManyField('resorts.resortPackages', blank=True, related_name="inactive_packages_of_tour")
    resortFood = models.ManyToManyField('resorts.resortPackages', blank=True, related_name="inactive_packages_of_food")
    province = models.CharField(max_length=63, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    last_visited = models.DateTimeField(null=True, blank=True, help_text="Last time a manager visited or updated this resort.")
    slug = models.SlugField(max_length=255, null=True, blank=True, default='')
    
    # Resort Amenities/Characteristics
    has_wifi = models.BooleanField(default=False, help_text="Free WiFi available")
    has_pool = models.BooleanField(default=False, help_text="Swimming pool available")
    has_bidet = models.BooleanField(default=False, help_text="Bidet in comfort rooms")
    has_parking = models.BooleanField(default=False, help_text="Parking available")
    has_restaurant = models.BooleanField(default=False, help_text="On-site restaurant")
    has_bar = models.BooleanField(default=False, help_text="Bar/lounge available")
    has_spa = models.BooleanField(default=False, help_text="Spa services available")
    has_gym = models.BooleanField(default=False, help_text="Fitness center/gym")
    has_beach_access = models.BooleanField(default=False, help_text="Direct beach access")
    has_air_conditioning = models.BooleanField(default=False, help_text="Air conditioning in rooms")
    has_hot_water = models.BooleanField(default=False, help_text="Hot water available")
    has_breakfast = models.BooleanField(default=False, help_text="Breakfast included/available")
    has_laundry = models.BooleanField(default=False, help_text="Laundry service available")
    pet_friendly = models.BooleanField(default=False, help_text="Pets allowed")
    family_friendly = models.BooleanField(default=False, help_text="Family-friendly facilities")
    has_generator = models.BooleanField(default=False, help_text="Backup generator available")
    
    # Payment Methods
    accepts_gcash = models.BooleanField(default=False, help_text="Accepts GCash payment")
    accepts_cash = models.BooleanField(default=False, help_text="Accepts cash payment")
    accepts_debit_card = models.BooleanField(default=False, help_text="Accepts debit card payment")
    accepts_credit_card = models.BooleanField(default=False, help_text="Accepts credit card payment")
    
    def __str__(self):
        return f"[INACTIVE] {self.RealName} "

class feedback(models.Model):
    pass

 
class contractTerms(models.Model):
    pass
  

class resortItem(models.Model):
    is_active = models.BooleanField(default=False) 
    resortGallery = models.ManyToManyField('resorts.sideImagesURLs', blank=True)
    resortQRLink = models.URLField(null=True, blank=True)  # QR code image link
    websiteURL = models.CharField(max_length=512, null=True, blank=True)  # Resort's website link
    resortActivities = models.ManyToManyField(
        'resorts.resortPackages', blank=True, related_name="packages_of_activities")
    resortTour = models.ManyToManyField(
        'resorts.resortPackages', blank=True, related_name="packages_of_tour")
    resortFood = models.ManyToManyField(
        'resorts.resortPackages', blank=True, related_name="packages_of_food")    
    resortAccomodations = models.ManyToManyField(
        'resorts.resortPackages', blank=True, related_name="packages_of_accomodations")
    resortSchedules = models.ManyToManyField(
        'home.allSchedules', blank=True, related_name="resortScheduleList")
    adminManager = models.ManyToManyField(
        'userProfile.UserCredentials', blank=True, related_name="resortAdmins")
    registeredBy = models.ForeignKey(
        'userProfile.UserCredentials', on_delete=models.CASCADE, blank=True, null=True)
    resort_ID = models.IntegerField(default=0)
    name = models.CharField(max_length=64, blank=True)
    RealName = models.CharField(max_length=64, blank=True)
    address = models.CharField(max_length=128, blank=True)
    place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, blank=True, null=True, related_name='EstablishmentPlace')
    contactNumber = models.CharField(max_length=128, blank=True)
    contactEmail = models.CharField(max_length=128, blank=True)
    whatsappNumber = models.CharField(max_length=128, blank=True)
    open_hours = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text="Example: Mon–Sun 8:00 AM – 9:00 PM"
    )
    promotionalVideo = models.URLField(blank=True)
    virtualpicture = models.URLField(blank=True)
    headerImage = models.URLField(blank=True)
    latitude = models.FloatField(blank=True)
    longitude = models.FloatField(blank=True)
    reviews = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    province = models.CharField(max_length=63, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    last_visited = models.DateTimeField(null=True, blank=True, help_text="Last time a manager visited or updated this resort.")
    # slug = models.SlugField(blank=True, unique=True, default="")
    slug = models.SlugField(max_length=255, null=True, blank=True, default='')
    
    # Resort Amenities/Characteristics
    has_wifi = models.BooleanField(default=False, help_text="Free WiFi available")
    has_pool = models.BooleanField(default=False, help_text="Swimming pool available")
    has_bidet = models.BooleanField(default=False, help_text="Bidet in comfort rooms")
    has_parking = models.BooleanField(default=False, help_text="Parking available")
    has_restaurant = models.BooleanField(default=False, help_text="On-site restaurant")
    has_bar = models.BooleanField(default=False, help_text="Bar/lounge available")
    has_spa = models.BooleanField(default=False, help_text="Spa services available")
    has_gym = models.BooleanField(default=False, help_text="Fitness center/gym")
    has_beach_access = models.BooleanField(default=False, help_text="Direct beach access")
    has_air_conditioning = models.BooleanField(default=False, help_text="Air conditioning in rooms")
    has_hot_water = models.BooleanField(default=False, help_text="Hot water available")
    has_breakfast = models.BooleanField(default=False, help_text="Breakfast included/available")
    has_laundry = models.BooleanField(default=False, help_text="Laundry service available")
    pet_friendly = models.BooleanField(default=False, help_text="Pets allowed")
    family_friendly = models.BooleanField(default=False, help_text="Family-friendly facilities")
    has_generator = models.BooleanField(default=False, help_text="Backup generator available")
    
    # Payment Methods
    accepts_gcash = models.BooleanField(default=False, help_text="Accepts GCash payment")
    accepts_cash = models.BooleanField(default=False, help_text="Accepts cash payment")
    accepts_debit_card = models.BooleanField(default=False, help_text="Accepts debit card payment")
    accepts_credit_card = models.BooleanField(default=False, help_text="Accepts credit card payment")
    
    def save(self, *args, **kwargs):
        # Auto-slugify the name field (Resort URL Name)
        if self.RealName:
            self.name = slugify(self.RealName)
        # Set slug from name if not already set
        if not self.slug:
            self.slug = self.name
        # Auto-generate websiteURL based on place and resort slugs
        if self.place and not self.websiteURL:
            place_slug = self.place.slug if self.place.slug else slugify(self.place.placename)
            resort_slug = self.slug
            self.websiteURL = f'https://paratara.com/{place_slug}/check/{resort_slug}'
        # Update last_visited to now if not set
        from django.utils import timezone
        if not self.last_visited:
            self.last_visited = timezone.now()
        super().save(*args, **kwargs)
    def get_absolute_url(self):
        return reverse("resorts:getResort2", args=[str(self.name)])

    @property
    def GalleryImages(self):
        return self.resortGallery.all()
    @property
    def ActivitiesList(self):
        return self.resortActivities.all()
    @property
    def FoodsList(self):
        return self.resortFood.all()    

    @property
    def AccomodationsList(self):
        return self.resortAccomodations.all()

    @property
    def TourList(self):
        return self.resortTour.all()

    @property
    def FoodList(self):
        return self.resortFood.all()

    @property
    def resortmanagerList(self):
        return self.adminManager.all()

    @property
    def active_subscription(self):
        ResortSubscription = apps.get_model('resortManagement', 'ResortSubscription')
        return ResortSubscription.objects.filter(
            resort=self,
            status=ResortSubscription.StatusChoices.ACTIVE
        ).order_by('-end_date').first()

    @property
    def has_active_subscription(self):
        active_sub = self.active_subscription
        return bool(active_sub and active_sub.is_active)

    def __str__(self):
        return f"{self.name} - {self.address} // {self.place}"

    def __str__(self):
        return f"{self.RealName} "

    # def get_absolute_url(self):
    #     return reverse("resorts:getResort2", args=[str(self.slug)])

    def serialize(self):
        active_sub = self.active_subscription
        serialized = {
            # "resort_Schedules": self.resortSchedules,
            # "resort_place": self.place,

            "resort_QRLink": self.resortQRLink,
            "resort_ID": self.id,
            "resort_name": self.name,
            "resort_RealName": self.RealName,
            "resort_address": self.address,
            "resort_contactNumber": self.contactNumber,
            "resort_contactEmail": self.contactEmail,
            "resort_whatsappNumber": self.whatsappNumber,
            "resort_open_hours": self.open_hours,
            "resort_promotionalVideo": self.promotionalVideo,
            "resort_headerImage": self.headerImage,
            "resort_latitude": self.latitude,
            "resort_longitude": self.longitude,
            "resort_reviews": self.reviews,
            "resort_own_description": self.description,
            "resort_Accomodations": [resortpackage.serialize() for resortpackage in self.resortAccomodations.all()],
            "resort_Schedules": [schedule.serialize() for schedule in self.resortSchedules.all()],
            "resort_Activities": [resortpackage.serialize() for resortpackage in self.resortActivities.all()],
            "resort_Tour": [resortpackage.serialize() for resortpackage in self.resortTour.all()],
            "resort_Food": [resortpackage.serialize() for resortpackage in self.resortFood.all()],
            "resort_Gallery": [resortgallery.serialize() for resortgallery in self.resortGallery.all()],
            "resort_province": self.province,
            "resort_timestamp":  str(self.timestamp),
            "resort_last_visited": self.last_visited.isoformat() if self.last_visited else None,
            "virtualpicture": self.promotionalVideo,
            # Amenities/Characteristics
            "amenities": {
                "wifi": self.has_wifi,
                "pool": self.has_pool,
                "bidet": self.has_bidet,
                "parking": self.has_parking,
                "restaurant": self.has_restaurant,
                "bar": self.has_bar,
                "spa": self.has_spa,
                "gym": self.has_gym,
                "beach_access": self.has_beach_access,
                "air_conditioning": self.has_air_conditioning,
                "hot_water": self.has_hot_water,
                "breakfast": self.has_breakfast,
                "laundry": self.has_laundry,
                "pet_friendly": self.pet_friendly,
                "family_friendly": self.family_friendly,
                "generator": self.has_generator,
            },
            # Payment Methods
            "payment_methods": {
                "gcash": self.accepts_gcash,
                "cash": self.accepts_cash,
                "debit_card": self.accepts_debit_card,
                "credit_card": self.accepts_credit_card,
            }
        }
        serialized["has_active_subscription"] = self.has_active_subscription
        serialized["active_subscription"] = active_sub.to_dict() if active_sub else None
        return serialized

 
# return reverse('home:checkPlaceSlug', kwargs={'slug': self.slug})


class resortPackages(models.Model):
    PackageTitle = models.CharField(max_length=64)
    ItemOfResort = models.ForeignKey(
        'resorts.resortItem', on_delete=models.CASCADE, null=True, related_name='itemOfResort')
    subPackages = models.ManyToManyField(
        'resorts.Packages', blank=True, related_name='packagesOfActivities')

    def __str__(self):
        return f"{self.PackageTitle}"

    @property
    def subPackagesList(self):
        return self.subPackages.all()

    def serialize(self):
        from django.utils import timezone
        now = timezone.now()
        return {
            'resortpackage_id': self.id,
            'package_title': self.PackageTitle,
            # Only include non-expired subpackages (if expires_at is set)
            'package_subpackage': [
                packages.serialize()
                for packages in self.subPackages.all()
                if getattr(packages, 'expires_at', None) is None or getattr(packages, 'expires_at') > now
            ]
        }


class sideImagesURLs(models.Model):
    urlField = models.URLField()

    def __str__(self):
        return f"{self.urlField}"

    def serialize(self):
        return f"{self.urlField}"
 
 
class Packages(models.Model):
    packageName = models.ForeignKey(
        'resorts.resortPackages', on_delete=models.CASCADE, null=True, related_name='ppa')
    ImageURL = models.ManyToManyField(
        'resorts.sideImagesURLs', blank=True, related_name='imagesOfSide')
    title = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    information = models.TextField(blank=True)
    price = models.IntegerField(default=0)
    website = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    # Optional expiration for Special Promotions or time-bound offers
    expires_at = models.DateTimeField(null=True, blank=True)
    # Track last update time for this package
    updated_at = models.DateTimeField(auto_now=True)

    # Link resort package items to generated place events (SiargaoEventSchedule)
    siargaoevents = models.ManyToManyField(
        'home.SiargaoEventSchedule',
        blank=True,
        related_name='packages'
    )

    def __str__(self):
        return f"{self.title}"

    @property
    def images(self):
        return self.ImageURL.all()

    def serialize(self):
        return {
            'package_id': self.id,
            'package_name': self.title,
            'package_description': self.description,
            'package_information': self.information,
            'package_price': self.price,
            'package_website': self.website,
            'is_available': self.is_available,
            'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None,
            'package_resort': self.packageName.PackageTitle,
            'package_image': [sideImage.serialize() for sideImage in self.ImageURL.all()],
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    # models.ManyToManyField('home.allSchedules',blank=True,related_name='postLists')


class EventRegistration(models.Model):
    event = models.ForeignKey(
        'resorts.Packages',
        on_delete=models.CASCADE,
        related_name='registrations',
        help_text='The event/promo item being registered for.'
    )
    resort = models.ForeignKey(
        'resorts.resortItem',
        on_delete=models.CASCADE,
        related_name='event_registrations'
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    pax = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    date = models.CharField(max_length=256, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['event', 'email'], name='uniq_event_registration_email')
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email}) -> {self.event.title}"

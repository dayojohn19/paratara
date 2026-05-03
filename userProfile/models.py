from django.db import models
from django.contrib.auth.models import AbstractUser
from django_resized import ResizedImageField

# Create your models here.


class UserCredentials(AbstractUser):
    photoLink = models.URLField(blank=True)
    additionalCreds = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE, null=True)

    visitedPlace = models.ManyToManyField(
        'home.Places_v2',
        blank=True,
        related_name='visited_users',
        help_text='Places this user has visited'
    )
    
    # IP tracking and analytics
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text='IP address at registration/login')
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, help_text='IP address of last login')
    user_agent = models.TextField(blank=True, help_text='Browser/device info')
    referrer_url = models.URLField(blank=True, help_text='Page they came from during registration')

    def save(self, *args, **kwargs):
        # Auto-capture IP and user agent if available
        from userProfile.middleware import get_current_request, get_client_ip
        
        request = get_current_request()
        if request:
            # Capture IP on first save (registration)
            if not self.pk and not self.ip_address:
                self.ip_address = get_client_ip(request)
                self.user_agent = request.META.get('HTTP_USER_AGENT', '')
                self.referrer_url = request.META.get('HTTP_REFERER', '')
            
            # Always update last login IP
            if self.pk:  # User already exists (login)
                self.last_login_ip = get_client_ip(request)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id}_{self.additionalCreds}"
    pass


class UserCredentialsBackUP(models.Model):
    userID = models.IntegerField()
    userPassword = models.CharField(max_length=32)


class userManager(models.Manager):
    def get_by_natural_key(self, userID, name):
        return self.get(userID=userID, name=name)


class chat_room_item(models.Model):
    chat_room_item_ID = models.IntegerField(blank=True, null=True)
    admin_ID = models.CharField(max_length=10, blank=True, null=True)
    receiver = models.CharField(max_length=64, blank=True, null=True)
    sender = models.CharField(max_length=64, blank=True, null=True)
    chat_room_name = models.CharField(max_length=128, blank=True)


class userPoster(models.Model):
    chatRoomslists = models.ManyToManyField(
        "chat_room_item", blank=True, related_name='chatroomlistofitem')
    userID = models.IntegerField(blank=True)

    visitedUser = models.ManyToManyField(
        "userPoster", blank=True, related_name='visitedList')
    visitorUser = models.ManyToManyField(
        "userPoster", blank=True, related_name='visitorList')
    # userIsBlogger = models.BooleanField(blank=True,default=False)

    name = models.CharField(max_length=64, blank=True,
                            default='Facebook not Connected')
    contact = models.CharField(max_length=128, blank=True)
    photo = models.URLField(blank=True)
    posts = models.ManyToManyField(
        'home.allSchedules', blank=True, related_name='postLists')
    verified = models.BooleanField(default=False)
    verificationID = models.URLField(blank=True)
    ###  verificationImage = models.ForeignKey('userProfile.ImageModel',on_delete=models.CASCADE,null=True)
    upVote = models.IntegerField(default=0)
    downVote = models.IntegerField(default=0)
    registeredTimeStamp = models.DateTimeField(auto_now_add=True)
    reputations = models.IntegerField(default=1)
    signedFrom = models.CharField(max_length=64, blank=True)
    age_range = models.CharField(max_length=32, blank=True, choices=[
        ('under_18', 'Under 18'),
        ('18_24', '18-24'),
        ('25_34', '25-34'),
        ('35_44', '35-44'),
        ('45_54', '45-54'),
        ('55_64', '55-64'),
        ('65_plus', '65+'),
        ('prefer_not_to_disclose', 'Prefer not to disclose')
    ])
    gender = models.CharField(max_length=32, blank=True, choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('prefer_not_to_disclose', 'Prefer not to disclose')
    ])
    objects = userManager()
    folderLink = models.URLField(blank=True)
    member_ID = models.URLField(blank=True)
    member_type = models.CharField(max_length=32, default='Associate Member')

    myTransactions = models.ManyToManyField(
        'apis.Transaction', blank=True, related_name='User_TransactionList')
    hashes = models.TextField(default='')
 
    class Meta:
        unique_together = [['userID', 'name']]

    def natural_key(self):
        # Return a tuple compatible with userManager.get_by_natural_key
        return (self.userID, self.name)
    # natural_key.dependencies = ['userProfile.userPoster']

    def save(self, *args, **kwargs):
        # Ensure name is never saved as NULL in the database
        if self.name is None:
            self.name = 'Facebook not Connected'
        super(userPoster, self).save(*args, **kwargs)

    @property
    def user_chatroom_list(self):
        return self.chatRoomslists.all().order_by('-id')

    @property
    def MyVisitors(self):
        return self.visitorUser.all().order_by('-id')[:10]

    @property
    def MyVisitations(self):
        return self.visitedUser.all().order_by('-id')[:10]

    @property
    def lastTransaction(self):
        return self.myTransactions.all()

    @property
    def lastFewTransaction(self):
        return self.myTransactions.all().order_by('-id')[:10]

    @property
    def unconfirmedTransaction(self):
        return self.myTransactions.filter(confirmed=None).all()

    def TransactionCount(self):
        return len(self.myTransactions.all())

    @property
    def currentBalance(self):
        return len(self.hashes)

    @property
    def allPosts(self):
        return self.posts.all()

    def __str__(self):
        return f"{self.name}_{self.userID}"


class TourGuideTourist(models.Model):
    tour_guide = models.ForeignKey('userProfile.TourGuide', on_delete=models.CASCADE, related_name='tourist_assignments')
    tourist = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, related_name='tour_guide_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True, help_text="When this tourist started being guided")
    
    class Meta:
        unique_together = ['tour_guide', 'tourist']
    
    def __str__(self):
        return f"{self.tour_guide} guiding {self.tourist} since {self.assigned_at}"


class TourGuide(models.Model):
    user = models.OneToOneField('userProfile.UserCredentials', on_delete=models.CASCADE, related_name='tour_guide_profile')
    primary_place = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, null=True, blank=True, related_name='tour_guides', help_text="Primary place where this tour guide operates")
    tours = models.ManyToManyField('home.allSchedules', blank=True, related_name='guided_tours')
    tourist_spots = models.ManyToManyField('home.TouristSpot', blank=True, related_name='tour_guides')
    guided_tourists = models.ManyToManyField('userProfile.UserCredentials', blank=True, related_name='guided_by', help_text="Tourists currently being guided by this tour guide", through='userProfile.TourGuideTourist')
    mobile_number = models.CharField(max_length=15, blank=True, help_text="Mobile number for contact")
    bio = models.TextField(blank=True, help_text="Brief biography of the tour guide")
    experience_years = models.PositiveIntegerField(default=0, help_text="Years of experience as a tour guide")
    certifications = models.TextField(blank=True, help_text="Tour guide certifications or licenses")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tour Guide: {self.user.username}"

    class Meta:
        verbose_name = "Tour Guide"
        verbose_name_plural = "Tour Guides"


class ImageModel(models.Model):
    ### ForeignKey('userProfile.userPoster',on_delete=models.CASCADE,null=True)
    usesrID = models.IntegerField(default=0)
    image = ResizedImageField(size=[400, 400], crop=[
                              'middle', 'center'], quality=50, upload_to='UserProfileImages2')

    def __str__(self):
        return f"{self.usesrID} {self.image}"

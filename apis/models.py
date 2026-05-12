from django.db import models
from django.utils.text import slugify
from django.urls import reverse
# Create your models here.


class Storeproducts(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)
    affiliate_link = models.URLField(blank=True)

    def __str__(self):
        return self.name





class EmailSubscribers(models.Model):
    FREQUENCY_CHOICES = (
        ('instant', 'Instant - Every new post'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
        ('monthly', 'Monthly Digest'),
    )
    
    # Essential fields
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    subscribed_date = models.DateTimeField(auto_now_add=True)
    confirmed_date = models.DateTimeField(null=True, blank=True)
    unsubscribed_date = models.DateTimeField(null=True, blank=True)
    
    # Email verification
    is_confirmed = models.BooleanField(default=False)
    confirmation_token = models.CharField(max_length=64, blank=True)
    
    # IP tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Engagement tracking
    last_email_sent = models.DateTimeField(null=True, blank=True)
    email_open_count = models.IntegerField(default=0)
    link_click_count = models.IntegerField(default=0)
    
    # Preferences 
    email_frequency = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='weekly'
    )
    interested_categories = models.JSONField(default=list, blank=True)
    
    # Analytics
    source = models.CharField(max_length=100, blank=True, help_text='Where they subscribed from')
    referrer_url = models.URLField(blank=True)
    user_agent = models.TextField(blank=True)
    unsubscribe_reason = models.TextField(blank=True)
    
    def __str__(self):
        status = "✓" if self.is_confirmed else "?"
        active = "Active" if self.is_active else "Inactive"
        return f"{status} {self.email} - {active}"
    
    class Meta:
        ordering = ['-subscribed_date']
        verbose_name = 'Email Subscriber'
        verbose_name_plural = 'Email Subscribers'

class Payments(models.Model):
    paypal_id = models.CharField(max_length=100, blank=True, null=True)
    payer_email = models.EmailField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    body = models.TextField(blank=True, null=True)  
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)    
    resort_id = models.IntegerField(blank=True, null=True)
    room_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        created_str = self.created.strftime("%b %d, %Y %I:%M %p")  
        amount_str = f"{self.amount:,.2f}" 
        return f"{created_str} -      ₱{amount_str}         - {self.payer_email}   -  {self.paypal_id}"        
        # return f"{self.created} ₱ {self.amount} {self.payer_email}"
        # return self.body[0:30]

    class Meta:
        ordering = ['-updated']


class Transaction(models.Model):
    transactionNo = models.CharField(max_length=64, blank=True)
    lastChainTransactionNo = models.CharField(max_length=64)
    hash = models.TextField(blank=True)
    amount = models.IntegerField(default=0)
    initiator = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE, related_name='initiatorTransaction', null=True)
    target = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE, related_name='targetTransaction', null=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(null=True, blank=True)
    confirmedBy = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, related_name='confirmedbytrack', null=True)

    @property
    def amount(self):
        return len(self.hash)

    def __str__(self):
        return f"{self.lastChainTransactionNo} {self.hash} - {self.confirmedBy} - {self.id}"


class Blogger(models.Model):
    # userCredential = models.ForeignKey('userProfile.UserCredentials', on_delete=models.CASCADE, null=True, related_name='BloggerCredential')
    aboutme = models.TextField(blank=True)
    shortsay = models.CharField(max_length=124, blank=True)
    profile = models.URLField(blank=True)
    blogs = models.ManyToManyField(
'apis.Blogs', blank=True, related_name='BlogsBlogger')
    bloggerURL = models.URLField(blank=True)

    @property
    def blogsList(self):
        return self.blogs.all()

 
class Blogs(models.Model):
    # blogUser = models.ForeignKey('userProfile.UserCredentials',on_delete=models.CASCADE, null=True, related_name='UserOfBlog')
    category_choices = (
        ('Guide', 'Guide'),
        ('Story', 'Story'),
        ('Tip and Trick', 'Tip and Trick'),
        ('Explore', 'Explore'),

    )


    category = models.CharField(choices=category_choices,max_length=24,default='Guide')    

    blogplace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, null=True, blank=True, related_name='blogplaceitem')
    title = models.CharField(max_length=64, blank=True)
    textContent = models.TextField(blank=True, null=True)
    summarize = models.CharField(max_length=400, default='Discover more about this destination')
    readtime = models.IntegerField(default=5)


    longitude = models.CharField(blank=True, max_length=64)
    latitude = models.CharField(blank=True, max_length=64)

    timestamp = models.DateTimeField(auto_now_add=True)


    localurlpath = models.CharField(max_length=125, blank=True)

    def __str__(self):
        return f"{self.blogplace} {self.title} long: {self.latitude} lat: {self.longitude} "
    
    def save(self, *args, **kwargs):
        if not self.localurlpath and self.blogplace and self.title:
            self.localurlpath = f"/pages/blog/{slugify(self.blogplace.placename)}/{slugify(self.title)}/"
        # Calculate readtime based on word count (assuming 200 words per minute)
        if self.textContent:
            word_count = len(self.textContent.split())
            self.readtime = max(1, word_count // 185) # Ensure at least 1 minute read time
        super().save(*args, **kwargs)

    def get_absolute_url(self):
            return reverse("singlepage2:bloghtmlpost", kwargs={
                "slug": slugify(self.blogplace),
                "slugSec": slugify(self.title)
            })        
        # return reverse("apis:schedule_detail", args=[str(self.blogplace) , str(self.title)] )

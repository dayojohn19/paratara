from django.db import models

# Create your models here.

class Comment(models.Model):
    message = models.TextField()
    messanger = models.CharField(max_length=64)
    schedule = models.ForeignKey('home.allSchedules',on_delete=models.CASCADE,related_name='postSchedule')
    timestamp = models.DateTimeField(auto_now_add=True)
    # def serialize(self):
    #     return {
    #         "message": self.message,
    #         "messanger":self.messanger,
    #         "schedule":self.schedule
    #         }
class allSchedules(models.Model):
    comment = models.ManyToManyField('home.Comment',blank=True,related_name='commentList')
    poster = models.ForeignKey('userProfile.userPoster',on_delete=models.CASCADE,null=True)
    detailsContact = models.CharField(max_length=94)
    posterName = models.CharField(max_length=64, default='Anonymous')    
    
    scheduleID = models.IntegerField(null=True, blank=True)
    posterInstagram = models.CharField(max_length=64, blank=True)
    dateN= models.IntegerField(null=True, blank=True)
    monthN = models.IntegerField(blank=True)
    yearN= models.IntegerField(blank=True)
    additionalDetails = models.TextField(blank=True)
    otherDetails = models.TextField(blank=True , null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    reviewCount = models.IntegerField(default=0)
    schedulePlace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='arrivingTo', null=True)
    meetPlace = models.CharField(max_length=64, blank=True)
    meetTime = models.CharField(max_length=24, blank=True, null=True)
    endDate = models.CharField(max_length=64, blank=True)
    scheduleTitle = models.CharField(max_length=64, blank=True)
    scheduleCost = models.CharField(max_length=64, blank=True)
    scheduleWebsite = models.URLField(blank=True, null=True)
    scheduleTypeAndMode = models.CharField(max_length=34, blank=True)
    scheduleTravelType = models.CharField(max_length=64,blank=True)
    MakerOrLooker = models.CharField(max_length=64, blank=True)
    @property
    def comments(self):
        return self.comment.all()
    @property
    def commentCount(self):
        return self.comment.count()
    class Meta:
        ordering = ["-id"]

class Places_v2(models.Model):
    reviewCount = models.IntegerField(default=0)
    placeID = models.IntegerField(blank=True,null=True, default=0)
    placename= models.CharField(max_length=64)
    placesSchedules = models.ManyToManyField(allSchedules, blank=True, related_name='allScheds')
    placePhoto = models.CharField(blank=True, max_length=9999)
    discussion = models.ManyToManyField('home.PlaceDiscussion',blank=True,related_name='discussionsLists')
    def serialize(self):
        return {
            "placeID": self.placeID,
            "placeName": self.placename
        }
    def __str__(self):
        return f"{self.placename}"
    @property
    def SchedList(self):
        return self.placesSchedules.all()

    def SchedListCount(self):
        return self.placesSchedules.count()
    @property
    def discussions(self):
        return self.discussion.all()   

    class Meta:
        ordering = ["-id"]

class PlaceDiscussion(models.Model):
    # schedulePlace = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, related_name='arrivingTo', null=True)

    place = models.ForeignKey('home.Places_v2',on_delete=models.CASCADE, related_name='placediscuss')
    discuss = models.TextField()
    discusser = models.ForeignKey('userProfile.userPoster', on_delete=models.CASCADE,related_name='discusserUser', blank=True,null=True)
    discusserName = models.CharField(max_length=64, default='ANONYMOUS')
    timestamp = models.DateTimeField(auto_now_add=True)
    # class Meta:
    #     ordering = ["-id"]

class ResortMessages(models.Model):
    guestName = models.CharField(default='Anonymous',max_length=32)
    resortID = models.IntegerField()
    guestMessage = models.TextField()
    guestContact = models.CharField(max_length=64)
    def __str__(self):
        return f"{self.guestMessage}"

        
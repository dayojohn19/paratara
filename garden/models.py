
# from django_resized import ResizedImageField
from django.db import models

# Create your models here.

# In each Province there will be PlaceProfile
# In each Place Profile there will be Collection
# In Each Collection there will be Visitor
# In Each Visitor there will be Memories

"""

Place - Where The Collections are
Collection -  be each Cards that will be Scan


Visitor will scan a Collection
and Create Memories

"""
 # Group of collections (funnel/grouping)
class CollectionGroup(models.Model):
    name = models.CharField(max_length=128, unique=True)
    address = models.CharField(max_length=128, unique=True, blank=True, null=True)
    collections = models.ManyToManyField('garden.Collection', blank=True, related_name='groups')

    def __str__(self):
        return self.name

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'collections': [c.id for c in self.collections.all()],
        }
# Visitor will scan a Collection
class testClastt(models.Model):
    pass
class PlaceProfile(models.Model):
    placeVisitor = models.ManyToManyField(
        'garden.Visitor', blank=True, related_name='placeVisitorLists')
    # placeCollections = models.ManyToManyField('garden.Collection', blank=True,  related_name='placeCollection')
    # placeCollections = models.ManyToManyField('garden.Collection', blank=True,  related_name='placeCollection')
    placeCollections = models.CharField(max_length=64,blank=True,null=True)
    placeName = models.CharField(max_length=64)
    placePicture = models.URLField()
    placeisVisited = models.BooleanField(default=False)
    placeLastVisited = models.DateTimeField(auto_now=True)
    placeFirstVisited = models.DateTimeField(auto_now_add=True)
    placeProvince = models.ForeignKey('garden.Province', on_delete=models.CASCADE, null=True, related_name='targetPlace')
    # placeProvince = models.CharField(max_length=64,null=True,blank=True)

    @property
    def placeVisitorLists(self):
        return [visitor.visitorName for visitor in self.placeVisitor.all()]

    def __str__(self):
        return f"{self.placeName}  -  {self.placeProvince}"

    def serialize(self):
        return {
            'placeID': self.id,
            'placeUniqueID': self.placeUniqueID,
            'placeName': self.placeName,
            'placePicture': self.placePicture,
            "placeVisitor": [visitor.serialize() for visitor in self.placeVisitor.all()],
            "placeCollections": [visitor.serialize() for visitor in self.placeCollections.all()],
        }


class Visitor(models.Model):
    visitorName = models.CharField(max_length=64)
    visitorID = models.CharField(max_length=12)
    # visitorVisitedPlace = models.ForeignKey(
    #     'garden.PlaceProfile', on_delete=models.CASCADE, blank=True, null=True, related_name='visitorvisitedplaceobject')
    visitorPlaces  = models.ManyToManyField(
        'garden.PlaceProfile', blank=True,  related_name='visitedPlaceLists')    
    #
    visitorCollections = models.ManyToManyField(
        'garden.Collection', blank=True,  related_name='visitorcollectionlists')
    # make it more profiling to users
    visitorMemories = models.ManyToManyField(
        'garden.Memory', blank=True,  related_name='visitorcollectionlists')
    visitorTimestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            'visitorName': self.visitorName,
            "visitorCollections": [mem.serialize() for mem in self.visitorCollections.all()],

        }

    def __str__(self): 
        return f"{self.visitorName} : {self.visitorID}"
 

class Province(models.Model):
    provinceName = models.CharField(max_length=64)
    provincePlaces = models.ManyToManyField(
        PlaceProfile, blank=True,  related_name='provinceplacelists')
    provinceVisitor = models.ManyToManyField('garden.Visitor', blank=True, related_name='provincevisitorlists')

    def __str__(self):
        return f"{self.provinceName}"

    def serialize(self):
        return {
            "provincePlaces": [mem.serialize() for mem in self.provincePlaces.all()],
            "provinceVisitor": [mem.serialize() for mem in self.provinceVisitor.all()],
        }


class Memory(models.Model):
    memoryPicture = models.URLField()
    memoryAbout = models.TextField()
    memoryVisitor = models.ForeignKey(
        'garden.Visitor', on_delete=models.CASCADE, null=False, related_name='visitormemorylists')
    memoryisPrivate = models.BooleanField(default=False)
    memoryTimestamp = models.DateTimeField(auto_now_add=True)

    def serialize(self):
        return {
            'memoryAbout': self.memoryAbout,
            'memoryPicture': self.memoryPicture,
            'memoryisPrivate': self.memoryisPrivate,
            'memoryTimestamp': self.memoryTimestamp.isoformat() if self.memoryTimestamp else None,
        }


class Collection(models.Model):

    THEME_CHOICES = (
        ('black', 'Black'),
        ('gold', 'Gold'),
        ('champagne', 'Champagne'),
        ('emerald', 'Emerald'),
        ('sapphire', 'Sapphire'),
        ('ruby', 'Ruby'),
        ('rose-gold', 'Rose Gold'),
        ('platinum', 'Platinum'),
        ('pearl', 'Pearl'),
        ('bronze', 'Bronze'),
    )

    touristSpot = models.ManyToManyField('home.TouristSpot', blank=True,  related_name='touristspotcollections')
    collectionTheme = models.CharField(choices=THEME_CHOICES,max_length=24,blank=True,null=True)
    collectionLocalFile= models.CharField(max_length=1000, null=True,blank=True)
    collectionImageIndicator = models.CharField(
        max_length=1000, blank=True, null=True)
    collectionName = models.CharField(max_length=128)
    collectionDescription = models.TextField(blank=True, null=True)
    collectionPicture = models.URLField(null=True, blank=True)
    collectionVideo = models.URLField(null=True, blank=True)
    collectionGoogleDriveURL = models.URLField(null=True, blank=True)
    collectionUniqueID = models.CharField(
        max_length=500, null=True, blank=True)
    collectionGroup = models.ForeignKey('garden.CollectionGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='primaryCollections')
    collectionPlace = models.ForeignKey('garden.PlaceProfile', on_delete=models.CASCADE, null=False,blank=True, related_name='targetPlace')
    collectionPlaceDirect = models.ForeignKey('home.Places_v2', on_delete=models.CASCADE, null=True, blank=True, related_name='targetPlaceDirect')
    # collectionPlace = models.CharField(max_length=64,null=True,blank=True)
    # collectionPlace = models.CharField(max_length=64,null=True,blank=True)
    collectionIsCollected = models.BooleanField(default=False)
    collectionCollector = models.ForeignKey(Visitor, on_delete=models.CASCADE, null=True, blank=True, related_name='targetCollector')
    collectionMemory = models.ManyToManyField('garden.Memory', blank=True,  related_name='provinceplacelists')
    collectionTimstamp = models.DateTimeField(auto_now_add=True)
    collectionCollected = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return f"{self.collectionTimstamp} {self.collectionPlace.placeName }  -  {self.collectionName}  -  {self.collectionUniqueID}  -     {self.collectionCollector}"
        # return f" -  {self.collectionName}  -  {self.collectionUniqueID}  -     {self.collectionCollector}"

    def forQRValues(self):
        # return f' {self.collectionName}, {self.collectionPlace} ,{self.coll ectionUniqueID}'
        return f' {self.collectionName},{self.collectionUniqueID}'

    # @property
    def visitorInfo(self):
        return {
            'collectionDescription': self.collectionDescription,
            'collectionPicture': self.collectionPicture,
            'collectionName': self.collectionName,
            'collectionPlace': self.collectionPlace,
            'collectionProvince': self.collectionPlace.placeProvince.provinceName,
            # 'collectionProvince': self.collectionPlace,
        }

    def serialize(self):
        # This return on    the serialize
        return {


            'collectionDescription': self.collectionDescription,
            'collectionName': self.collectionName,
            'placeVisitorLists': self.collectionPlace.placeVisitorLists,
            'collectionPicture': self.collectionPicture,
            'collectionVideo': self.collectionVideo,
            'collectionCollector': self.collectionCollector.visitorName if self.collectionCollector else None,
            'collectionCollectorID': self.collectionCollector.visitorID if self.collectionCollector else None,

            'collectionGroup': self.collectionGroup.name if self.collectionGroup else None,
            'collectionGroupID': self.collectionGroup.id if self.collectionGroup else None,
            'groups': [g.serialize() for g in self.groups.all()],

            'collectionUniqueID': self.collectionUniqueID,
            'collectionPlace': self.collectionPlace.placeName,
            'collectionPlaceID': self.collectionPlaceDirect.id if self.collectionPlaceDirect else None,
            'collectionPlaceDirectName': self.collectionPlaceDirect.slug if self.collectionPlaceDirect else None,
            'collectionIsCollected': self.collectionIsCollected,
            # 'collectionMemory':self.collectionMemory
            'collectionProvince': self.collectionPlace.placeProvince.provinceName,
            "collectionMemory": [mem.serialize() for mem in self.collectionMemory.all()],
            # 'collectionTimstamp': self.collectionTimstamp,
            # 'collectionCollected': self.collectionCollected, 
            'collectionTimstamp': self.collectionTimstamp.isoformat() if self.collectionTimstamp else None,
            'collectionCollected': self.collectionCollected.isoformat() if self.collectionCollected else None,            
        }

# TODO ADD NOTES:
# A place Notes or guides



# class QRCode(models.Model):
#     qrString = models.TextField()
#     qrTarget = models.ForeignKey(
#         'garden.Collection', on_delete=models.CASCADE, null=True, related_name='targetPlace')
#     qrImage = ResizedImageField(size=[400, 400], crop=[
#         'middle', 'center'], quality=50, upload_to='UserProfileImages')

#     def __str__(self):
#         return f"{self.qrTarget} {self.qrString}"

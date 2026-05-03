
# Register your models here.
from django.contrib import admin

# Register your models here.
from .models import *


class CollectionAdmin(admin.ModelAdmin):
	list_display = (
		'collectionName',
		'collectionPlace',
		'collectionUniqueID',
		'collectionCollector',
		'collectionIsCollected',
		'collectionTimstamp',
		'collectionCollected',
	)
	readonly_fields = ('collectionTimstamp', 'collectionCollected')
	search_fields = ('collectionName', 'collectionUniqueID', 'collectionPlace__placeName')
	list_filter = ('collectionIsCollected', 'collectionPlace__placeProvince')


admin.site.register(Visitor)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(PlaceProfile)
admin.site.register(Province)
admin.site.register(Memory)

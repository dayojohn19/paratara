from django.contrib import admin

# Register your models here.
from .models import FacebookPage,SiargaoEventSchedule, BlockedIP,SiargaoEventRegistrant, RequestPage, RequestLog, ResortMessages, Places_v2, allSchedules, Comment, PlaceDiscussion, SchedTypeAndMode,TouristSpot, Joiner,RequestPageSummary


admin.site.register(SiargaoEventSchedule)
admin.site.register(SiargaoEventRegistrant)
admin.site.register(ResortMessages)
admin.site.register(Places_v2)
admin.site.register(allSchedules)
admin.site.register(Comment)
admin.site.register(PlaceDiscussion)

admin.site.register(RequestPage)
admin.site.register(RequestLog)
admin.site.register(TouristSpot)
admin.site.register(Joiner)
admin.site.register(RequestPageSummary)
admin.site.register(BlockedIP)
admin.site.register(FacebookPage)



from django.contrib import admin

# Register your models here.
from .models import (
    Continent,
    Country,
    FacebookPage,
    PlaceDirectory,
    Region,
    SiargaoEventSchedule,
    BlockedIP,
    SiargaoEventRegistrant,
    RequestPage,
    RequestLog,
    ResortMessages,
    Places_v2,
    allSchedules,
    Comment,
    PlaceDiscussion,
    SchedTypeAndMode,
    TouristSpot,
    Joiner,
    RequestPageSummary,
)


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


@admin.register(Continent)
class ContinentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "continent")
    raw_id_fields = ("continent",)
    search_fields = ("code", "name")
    list_filter = ("continent",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "region")
    raw_id_fields = ("region",)
    search_fields = ("code", "name")
    list_filter = ("region",)


@admin.register(PlaceDirectory)
class PlaceDirectoryAdmin(admin.ModelAdmin):
    list_display = (
        "place_id",
        "place",
        "country",
        "region",
        "continent",
        "place_type",
        "is_published",
        "popularity_score",
    )
    raw_id_fields = ("place", "continent", "region", "country")
    search_fields = ("place__placename", "place__slug", "country__code", "country__name")
    list_filter = ("is_published", "place_type", "continent", "region", "country")

    def save_model(self, request, obj, form, change):
        from .place_directory import sync_place_directory

        sync_kwargs = {
            "place_type": obj.place_type,
            "is_published": obj.is_published,
            "popularity_score": obj.popularity_score,
        }
        if obj.country_id:
            sync_kwargs["country"] = obj.country
        elif obj.region_id:
            sync_kwargs["region"] = obj.region
        elif obj.continent_id:
            sync_kwargs["continent"] = obj.continent
        else:
            sync_kwargs.update({
                "country": None,
                "region": None,
                "continent": None,
            })

        sync_place_directory(obj.place, **sync_kwargs)

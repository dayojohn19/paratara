from django.contrib import admin

# Register your models here.
from .models import userPoster,UserCredentials, UserCredentialsBackUP,TourGuide


@admin.register(userPoster)
class UserPosterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "userID",
        "name",
        "contact",
        "mobile_number",
        "address_city",
        "address_country",
        "signedFrom",
    )
    search_fields = (
        "name",
        "contact",
        "mobile_number",
        "address_city",
        "address_country",
    )
    list_filter = ("signedFrom", "address_country", "address_city")


admin.site.register(UserCredentials)
admin.site.register(UserCredentialsBackUP)
admin.site.register(TourGuide)

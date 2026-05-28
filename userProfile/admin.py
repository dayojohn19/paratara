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
        "bank_name",
        "bank_account_name",
        "bank_contact",
        "address_city",
        "address_country",
        "signedFrom",
    )
    search_fields = (
        "name",
        "contact",
        "mobile_number",
        "bank_name",
        "bank_account_name",
        "bank_account_number",
        "bank_contact",
        "address_city",
        "address_country",
    )
    list_filter = ("signedFrom", "bank_name", "address_country", "address_city")


admin.site.register(UserCredentials)
admin.site.register(UserCredentialsBackUP)
admin.site.register(TourGuide)

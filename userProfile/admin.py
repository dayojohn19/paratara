from django.contrib import admin

# Register your models here.
from .models import userPoster,UserCredentials, UserCredentialsBackUP,TourGuide


admin.site.register(userPoster)
admin.site.register(UserCredentials)
admin.site.register(UserCredentialsBackUP)
admin.site.register(TourGuide)


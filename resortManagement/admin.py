from django.contrib import admin

# Register your models here.
from .models import Checkins,CheckinDay,ResortManager


admin.site.register(Checkins)
admin.site.register(CheckinDay)
admin.site.register(ResortManager)


from django.contrib import admin

# Register your models here.
from .models import resortItem, resortPackages, sideImagesURLs, Packages, PackageReview, EventRegistration


admin.site.register(resortItem)
admin.site.register(resortPackages)
admin.site.register(sideImagesURLs)
admin.site.register(Packages)
admin.site.register(PackageReview)
admin.site.register(EventRegistration)

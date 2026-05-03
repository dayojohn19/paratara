from django.contrib.sitemaps import Sitemap
from home.models import allSchedules
from resorts.models import resortItem
from itertools import chain


class allSchedulesSitemap(Sitemap):
    def items(self):
        # return list(chain(allSchedules.objects.all(), resortItem.objects.all()))
        # return allSchedules.objects.all() + resortItem.objects.all()
        return allSchedules.objects.all()

    def lastmod(self, obj):
        return obj.timestamp

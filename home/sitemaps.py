from django.contrib.sitemaps import Sitemap
from .models import Places_v2, allSchedules  # or whatever your blog model is called
from resorts.models import  resortItem
from apis.models import Blogs

class allSchedulesSitemap(Sitemap):
    """Sitemap for all schedules"""
    def items(self):
        return allSchedules.objects.all()

    def lastmod(self, obj):
        return obj.timestamp

class BlogsSitemap(Sitemap): 

    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return Blogs.objects.all()

    def lastmod(self, obj):
        pass 

class Places_v2Sitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5
    protocol = "https"

    def items(self):
        return Places_v2.objects.all()

    def lastmod(self, obj):
        pass 
        # return obj.updated_at  # use your model's update field
        # return obj.updated_at  # use your model's update field

class ResortItemsSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return resortItem.objects.all()
 
    def lastmod(self, obj):
        # return obj.updated_at  # optional
        pass


class StaticViewsSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        # List all your static HTML page URLs (without domain)
        return [
            'siargao/cloud9',          # maps to /cloud9/ in your urls.py
            'siargao/sugba-lagoon',
            'siargao/bucasgrande',
            'other/hat',    # maps to /sugba-lagoon/
            'other/chemtrix'
        ]

    def location(self, item):
        # If your URLs are like /cloud9/ and /sugba-lagoon/
        return f'/pages/blog/{item}/'

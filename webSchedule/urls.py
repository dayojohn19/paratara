"""webSchedule URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import (handler400, handler403, handler404, handler500)
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path, re_path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

from django.conf import settings
from django.conf.urls.static import static

from home import views as home_views
# new TODO https://learndjango.com/tutorials/django-sitemap-tutorial
from django.contrib.sitemaps import GenericSitemap
# new TODO https://learndjango.com/tutorials/django-sitemap-tutorial
from django.contrib.sitemaps.views import sitemap
from home.models import allSchedules
from home.sitemaps import allSchedulesSitemap
from resortManagement import views as resortManagement_views

info_dict = {
    "queryset": allSchedules.objects.all(),
    "date_field": "timestamp",
}


def legacy_resorts_redirect(request, path=""):
    """Redirect legacy /resorts/* URLs to the canonical /est/* prefix.

    Uses HTTP 308 to preserve method/body (important for POST forms).
    """
    target = "/est/" + (path or "")
    response = HttpResponseRedirect(target)
    response.status_code = 308
    return response

urlpatterns = [ 
    path(
        "favicon.ico",
        home_views.favicon,
    ),
    path("paypal/webhook/", resortManagement_views.paypal_webhook, name="paypal_webhook"),
    path('imageapp/', include('imageapp.urls')),
    path('admin/', admin.site.urls),
    # path('app_car/', include('app_Car.urls')),
    path('', include('home.urls')),
    # path('', include('carpool.urls')),
    path('userProfile/', include('userProfile.urls')),
    
    path('resortManagement/', include('resortManagement.urls')),
    # Canonical prefix is /est/. Redirect all legacy /resorts/* URLs (method-preserving).
    re_path(r'^resorts/(?P<path>.*)$', legacy_resorts_redirect),
    re_path(r'^resorts/?$', legacy_resorts_redirect),
    path('est/', include('resorts.urls')),
    # path('social-auth/', include('social_django.urls', namespace='social')),
    path('apis/', include('apis.urls')),
    path('pages/', include('singlepage2.urls')),
    path('calculator/', include('calculator.urls')),
    path('garden/', include('garden.urls')),
    path('subscriptions/', include('subscription.urls')),

    # Friendly resort URLs without the /resorts/ prefix
    path('<slug:place_slug>/<slug:resort_slug>/', home_views.resort_by_slugs, name='resort_by_slugs_friendly'),

    path(
        "sitemap.xml",
        sitemap,
        # {"sitemaps": {"PagesInSiteMap": GenericSitemap(info_dict)}},
        {"sitemaps": {"PagesInSiteMap": allSchedulesSitemap}},
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# handler400 = 'home.views.bad_request'
# handler403 = 'home.views.permission_denied'
# handler404 = 'home.views.page_not_found'
# handler500 = 'home.views.server_error'

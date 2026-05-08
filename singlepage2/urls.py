from django.urls import path
from . import views
from django.views.generic import TemplateView


app_name = "singlepage2" 
urlpatterns = [
    path("blog/", views.blogFunc, name="blogFunc"),
    path("kefir/", views.kefir, name="kefir"),
#   Then register here /apis/blog/
    path('blog/<slug:slug>/<slug:slugSec>/', views.blog_html, name='bloghtmlpost'),
    path('blog/<slug:slug>/<slug:slugSec>//', views.blog_html, name='bloghtmlpost'),
    path('blog/<slug:slug>/<slug:slugSec>', views.blog_html, name='bloghtmlpost'),
    path("blog/<slug:slug>/<slug:slugSec>/<slug:slugName>/", views.blog_html, name="bloghtmlpost_with_name"),
    # path('cloud9/',  TemplateView.as_view(template_name='blogs/siargao/cloud9.html'),  name='cloud9'),
    # path('sugbalagoon/',  TemplateView.as_view(template_name='blogs/siargao/sugbalagoon.html'),  name='cloud9'),
    # path('bucasgrande/',  TemplateView.as_view(template_name='blogs/siargao/bucasgrande.html'),  name='cloud9'),
    
    # path('allpath/<path:pk>', views.get_html, name='get_html'),

    path("chemtrix/", views.chemtrix, name='chemtrix'),
    path("resortgroup/", views.resortgroup, name='resortgroup'),

    path("", views.SinglePageHome, name='singlepagehome'),
    
    path("upploadtheimage/", views.upploadtheimage, name='upploadtheimage'),
#     path('uploadimage/', views.uploadimage, name='uploadimage'),
#     path("upload-form/", views.upload_imgbb, name="upload-imgbb"),
    path('services/' , views.services, name='services'),
    path('cebu/cebucity/find/booking/', views.cebutravelbooking,
         name='getcebutravelbooking'),
    path('cebu/cebucity/find/booking/<csrf_token>/', views.cebutravelbooking,
         name='getcebutravelbooking'),
    # path('<csrf_token>/<path:htmlfile>/', views.get_html_empty, name='get_html'),
    # path('<csrf_token>/<path:htmlfile>/<str:pagetitle>', views.get_html, name='get_html'),
    
]

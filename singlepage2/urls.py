from django.urls import path
from . import views
from django.views.generic import TemplateView
from .htmlwriter_noai import blog_form_view, create_blog_view, get_places_json

  
app_name = "singlepage2" 
urlpatterns = [
    # Blog form and creation (NEW - Non-AI version)
    path('create/', blog_form_view, name='blog_form'),
    path('submit/', create_blog_view, name='create_blog'),
    path('api/places/', get_places_json, name='get_places'),
    
    # Existing blog paths
    path("blog/", views.blogFunc, name="blogFunc"),
    path("blog/manual-generate/", views.generate_manual_blog_page, name="manual_blog_page_generate"),
    path("kefir/", views.kefir, name="kefir"),
    path("blog-edits/save-file/", views.save_blog_paragraph_file_edit, name="save_blog_paragraph_file_edit"),
    path("blog-edits/save/", views.save_blog_paragraph_file_edit, name="save_blog_paragraph_edit"),
    path("api/blog/<slug:place_slug>/tour-guides/", views.blog_tour_guides, name="blog_tour_guides"),
    #   Then register here /apis/blog/
    path('blog/<slug:slug>/assets/<path:asset_name>', views.blog_asset, name='blog_asset'),
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

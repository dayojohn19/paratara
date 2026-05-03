from django.urls import path
from . import views
from django.views.generic import TemplateView
# siargao_links = {
#     'extra_html': '''
#     <style>
#       /* Navigation banner styling */
#       .banner {
#         background-color: #ffffff;  /* white background */
#         padding: 12px 20px;
#         border-bottom: 2px solid #e0e0e0;
#         box-shadow: 0 2px 5px rgba(0,0,0,0.05);
#       }
#       .banner ul {
#         list-style: none;
#         margin: 0;
#         padding: 0;
#         display: flex;
#         flex-wrap: wrap;           /* allow wrapping on small screens */
#         gap: 12px;                 /* spacing between links */
#       }
#       .banner ul li {
#         flex: 1 1 auto;            /* allow links to shrink on small screens */
#       }
#       .banner ul li a {
#         display: block;
#         text-decoration: none;
#         color: #007bff;            /* primary blue */
#         font-weight: 500;
#         text-align: center;
#         padding: 8px 12px;
#         border-radius: 6px;
#         transition: background 0.3s, color 0.3s, transform 0.2s;
#       }
#       .banner ul li a:hover {
#         background-color: #007bff;
#         color: #ffffff;
#         transform: translateY(-2px);  /* subtle hover lift effect */
#       }
#       /* Responsive: smaller font and padding on mobile */
#       @media (max-width: 600px) {
#         .banner ul {
#           gap: 8px;
#         }
#         .banner ul li a {
#           font-size: 14px;
#           padding: 6px 8px;
#         }
#       }
#     </style>

#     <div class="banner">
#       <ul>
#         <li><a href="/pages/cloud9/" >cloud 9</a></li>
#         <li><a href="/pages/bucasgrande/" >bucas grande</a></li>
#         <li><a href="/pages/hat/" >Hat Store</a></li>
#         <li><a href="/pages/sugba-lagoon/" >Sugba Lagoon</a></li>
#       </ul>
#     </div>
#     '''
# }

app_name = "singlepage2" 
urlpatterns = [
    path("blog/", views.blogFunc, name="blogFunc"),
    path("kefir/", views.kefir, name="kefir"),
#   Then register here /apis/blog/
    path('blog/<slug:slug>/<slug:slugSec>/', views.blog_html, name='bloghtmlpost'),
    path("blog/<slug:slug>/<slug:slugSec>/<slug:slugName>/", views.blog_html, name="bloghtmlpost_with_name"),
    # path('cloud9/',  TemplateView.as_view(template_name='blogs/siargao/cloud9.html'),  name='cloud9'),
    # path('sugbalagoon/',  TemplateView.as_view(template_name='blogs/siargao/sugbalagoon.html'),  name='cloud9'),
    # path('bucasgrande/',  TemplateView.as_view(template_name='blogs/siargao/bucasgrande.html'),  name='cloud9'),
    
    # path('allpath/<path:pk>', views.get_html, name='get_html'),

    path("chemtrix/", views.chemtrix, name='chemtrix'),
    path("resortgroup/", views.resortgroup, name='resortgroup'),

    path("", views.SinglePageHome, name='singlepagehome'),
    path('<path:path>', views.SinglePageHome, name='svelte-spa'),
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

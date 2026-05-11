from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from . import views
from django.views.generic import TemplateView

from django.contrib import sitemaps
from django.contrib.sitemaps.views import sitemap
from home.sitemaps import Places_v2Sitemap,ResortItemsSitemap, StaticViewsSitemap,BlogsSitemap




sitemaps = {
    'blogs':BlogsSitemap,
    'places': Places_v2Sitemap,
    'resorts': ResortItemsSitemap,
    'static': StaticViewsSitemap,
}
app_name = "home"
urlpatterns = [
    path('home/fill_tourist_spot_images/', views.fill_tourist_spot_images, name='fill_tourist_spot_images'),
     path('presentation_insights/', views.presentation_insights, name='presentation-insights'),
     path('presentation/', views.presentation, name='presentation'),
     path('presentation/request-page-summary/', views.request_page_summary_charts, name='request-page-summary-charts'),
     path("travel/<str:placenameURL>/", views.place_url, name="geturlplace"),
     path('home/htmltest/', views.htmltest, name="htmltest"),
     path("home/show-calendar/", views.calendar_html, name="give_calendar"),
     path("home/scrape-siargao/", views.getSiargaoEvents, name="scrape_siargao_events"),
     path("home/searchplace/", views.searchplace, name="searchplace"),
     path("home/paypal_html", views.paypal_html, name="paypal_html_name"),
     path("home/event/register/<int:event_id>/", views.register_siargao_event, name="register_siargao_event"),
    path('home/autopopulate/', views.autopopulate, name="autopopulate"),
    path('home/getcarpooljson/', views.carpoolJOSN, name="carpooljson"),
    path("home/carpool/", views.carpool, name="carpool"),
    path("home/rooms/", views.rooms, name="rooms"),
    path("home/newViaje/", views.viaje_v2, name="viaje"),
    path("home/refreshSchedules/", views.refreshSchedules_v2, name="refreshSchedules"),
    path("home/scrape", views.scrappePage, name="scrape"),  # for StandONRUnner.py  
    path("home/surf/", views.surfFacebookPostDirectly, name="surf"),
    path("home/form/", views.viewAllForms, name="homeForm"),

     path("placeslug/<slug:slug>/", views.checkPlace_v2, name="checkPlaceSlug"),
     path("place/<str:place_slug>/on-visit/", views.place_current_visitors, name="place_current_visitors"),
#     path("resort/", views.ResortsDetailView.as_view(), name="resort_details"),
#     path("resort/<int:pk>", views.ResortsDetailView.as_view(),
#          name="resort_details"),     
     path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
     path('robots.txt', views.robots_txt, name='robots_txt'),
     path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
     path('google48bcdfe5ffff5f5a.html', TemplateView.as_view(template_name="google48bcdfe5ffff5f5a.html"), name='google-site-verification'),    
     path('tourist-spot-create/', views.create_tourist_spot, name='create_tourist_spot'),    

     path('place/<int:place_id>/community-bulletin/', views.community_bulletin_list, name='community_bulletin_list'),
     path('place/placename/<str:place_id>/community-bulletin/', views.community_bulletin_list, name='community_bulletin_list'),
     path('place/<int:place_id>/community-bulletin/upload/', views.community_bulletin_upload, name='community_bulletin_upload'),
     path('place/<int:place_id>/community-bulletin/<int:post_id>/delete/', views.community_bulletin_delete, name='community_bulletin_delete'),

     path('home/facebook-posts/', views.facebook_posts, name='facebook_posts'),
#     path('intent' , views.intent, name="intent"),
#     path('payment', views.payment, name='payment'),
#     path('attach', views.attach, name='attach'),
#     path('checkout', views.checkout, name='checkout'),
#     path(''),


    
    path("schedule/addSchedulesAndPlaces/",
         views.addSchedulesAndPlaces, name="addSchedulesAndPlaces"),
    path("schedule/addreviewcounttoall/", views.addReviewstoSchedules,
         name="addreviewcounttoallrandom"),

    re_path(r'^ads\.txt$', views.googleadsense, name='google_adsense'),
    path("", views.home, name='home'),

    # PlaceAddEvent
    # FROM APP CAR
    path("place/json/<int:id>/", views.placeCalendarJSON_v2, name="placeCalendarJSON"),
    path("place/json/<int:id>/<int:month>/<int:year>/", views.placeCalendarJSON_v2, name="placeCalendarJSONMonth"),
     path("place/<int:place_id>/create-schedule/", views.create_schedule_for_place, name="create_schedule_for_place"),
    path("place/<int:id>/<int:currentMonth>/<int:currentYear>/",
         views.place_v2, name="place"),
    path("<str:placenameURL>/place/<int:id>/<int:currentMonth>/<int:currentYear>/", views.place_v2, name="placewithURL"),
    path("places/<slug:place_slug>/<int:year>/<int:month>/", views.place_by_slug, name="place_by_slug_with_date"),
    path("places/<slug:place_slug>/", views.place_by_slug, name="place_by_slug"),

    path("resorts/<int:id>", views.exploreResort, name="exploreResort"),
    # Add review on schedule
    path("addScheduleReview/<int:scheduleID>",
         views.addScheduleReview, name="addScheduleReview"),
    path("commentpost/<int:postID>", views.Comment, name="comment"),
    path("discuss/<int:placeID>", views.discussion, name="discuss"),
    path("resortDB/<int:resortID>", views.resortDB, name="resortDB"),
    # path("scrapeFacebook", views.scrapeFacebook, name="scrapeFacebook"),
    #  path("scrapeFacebook", views.scrapeFacebook, name="scrapeFacebook"),
    # path("nav", views.nav, name="nav"),
    # path("navigation",views.navigation, name="navigation"),
    # path("enc",views.enc, name="enc"),
    # path("editRoute", views.editRoute, name="editRoute"),
    # path("userChartMapl", views.userChartMap, name="userChartMap"),
    # path("alarmAndSensors", views.alarmAndSensors, name="alarmAndSensors"),
    
    path("place/<str:placename>/", views.checkPlace_v2, name="checkPlace"),



    path('record_visit/<slug:place_slug>/<slug:spot_slug>/', views.record_visit, name='record_visit'),
    path('remove_visit/<slug:place_slug>/<slug:spot_slug>/', views.remove_visit, name='remove_visit'),
    path('<slug:place_slug>/visit/<slug:spot_slug>/', views.visit_spot, name='visit_spot'),
    path('api/spot/<slug:place_slug>/<slug:spot_slug>/', views.get_spot_details, name='get_spot_details'),
    path('visitor_stats/<int:spot_id>/', views.get_visitor_stats, name='visitor_stats'),
    path('place/<slug:place_slug>/tourist-spots/', views.tourist_spots, name='tourist_spots'),
    path('all-tourist-spots/', views.all_tourist_spots, name='all_tourist_spots'),
    path('add_tour_guide/', views.add_tour_guide, name='add_tour_guide'),
    path('api/tour_guide/<str:username>/', views.get_tour_guide_info, name='get_tour_guide_info'),
    path('api/place/<slug:place_slug>/latest-visit/', views.get_place_latest_visit_timestamp, name='get_place_latest_visit_timestamp'),
    path('schedule/<int:schedule_id>/join/', views.join_schedule, name='join_schedule'),
     path('schedule/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    path('api/schedule/<int:schedule_id>/joiners/', views.get_schedule_joiners, name='get_schedule_joiners'),

    # Resort URL pattern: /<place-slug>/check/<resort-slug>/
    path('<slug:place_slug>/check/<slug:resort_slug>/', views.resort_by_slugs, name='resort_by_slugs'),
    path('add-facebook-page/', views.add_facebook_page, name='add_facebook_page'),

    # http://treep.today/.well-known/pki-validation/D86D3E0B01797CC0A936E2472CF4FB91.txt

    # Storeproducts management
    path('store/storeproducts/', views.storeproducts_management, name='storeproducts_management'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

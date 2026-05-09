from django.urls import path
from . import views
from . import upload_imbb
from django.http import HttpResponse
app_name = "apis"
urlpatterns = [

    


        path('getPlaceActivities/<int:place_id>/', views.getPlaceActivities, name='get_place_activities'),
        path('getPlaceAccommodations/<int:place_id>/', views.getPlaceAccommodations, name='get_place_accommodations'),
        
    path('upload_to_imbb/', upload_imbb.upload_all_images, name='upload_images_to_imbb'),

    # path('blogs/<int:place_id>/', views.get_blogs, name='get_blogs'),    
    path('getPlaceBlogs/<str:placename>/', views.getPlaceBlogs, name="getbloglist"),
    path('getPlaceCollections/<str:placename>/', views.getPlaceCollections, name="getPlaceCollections"),
    path('getPlaceEvents/<str:placename>/', views.apiEvents, name='apisevents'),
    path('getPlaceSchedules/<str:placename>/', views.getPlaceSchedule, name='apisevents'),

    path('getresortitem/<str:resortName>/', views.getResortItem, name='resort_item'),

    path('schedules/',views.getSchedules),
    path('get_calendar_view/', views.get_calendar_view, name='get_calendar_view'),

    # Email subscription endpoints
    path('subscribe/', views.subscribe_email, name='subscribe_email'),
    path('confirm/<str:token>/', views.confirm_subscription, name='confirm_subscription'),
    path('unsubscribe/<str:token>/', views.unsubscribe, name='unsubscribe'),

    path('health/', lambda request: HttpResponse('OK', content_type='text/plain'), name='health_check'),
    path('',views.getRoutes),
    path('payments/', views.getPayments),
    path('apiTest/', views.apiTest),
    path('payments/create/', views.createPayment),
    path('payments/<str:pk>/update/', views.putPayment),
    path('payments/<str:pk>/',views.getPayment),

    
 
    path("makepayment/<str:pk>/", views.makepayment, name="makepayment"),
    path("confirmTransaction/<str:pk>/", views.confirmTransaction, name="confirmTransaction"),
    path("getBlogger/<int:bloggerID>", views.getBlogger, name="christian_voyager"),
    path("userblog/",views.NewblogUser, name="blog"),
    path("userblog/<str:message>/",views.NewblogUser, name="blog"),
    path("blogsItem/<int:bloggerID>", views.getBlogs, name="blogs_item"),
    path('chatgpt/', views.chatgpt_view, name='chatgpt'),

    # Storeproducts endpoints
    path('storeproducts/', views.get_storeproducts, name='get_storeproducts'),
    path('storeproducts/<int:pk>/', views.get_storeproduct, name='get_storeproduct'),
    path('storeproducts/create/', views.create_storeproduct, name='create_storeproduct'),
    path('storeproducts/<int:pk>/update/', views.update_storeproduct, name='update_storeproduct'),
    path('storeproducts/<int:pk>/delete/', views.delete_storeproduct, name='delete_storeproduct'),

]

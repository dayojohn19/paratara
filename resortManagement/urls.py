from django.urls import path
from . import views
from . import qrcodereceipt
app_name = 'resort_management'
urlpatterns = [
    path("qr/<str:qr_strings>", qrcodereceipt.my_page, name="qr"),
 

    # path("roomAvailability/<int:room_id>", views.room_availability, name="room_availability"),
    # path('roomAvailability/<int:resort_id>/<int:room_id>/<int:month>/<int:year>', views.room_availability, name="room_availability"),
    path("roomList/<int:resortPackage_id>", views.room_list, name="room_list"),

    
    path("roomcheckin", views.room_checkin, name="room_checkin"),
    path("calendar/<int:resort_id>/<int:room_id>/", views.marked_calendar, name='markedcalendarnamed'),

    
        #     'resort_id':1,
        # 'room_id':1,
        # 'room_month':1,
        # 'room_year ':1   

    # resort_id room_id room_month room_year 'previous'
    path("calendar/<int:resort_id>/<int:room_id>/<int:month>/<int:year>/<str:whatstep>/", views.marked_calendar, name='movemarkedcalendarnamed'),

     


    path('ajax-upload/', views.upload_image_ajax, name='ajax_upload'),
    path('guestlists/<int:resort_id>', views.viewGuestlists, name='getguesstlists'),
    path('subscription/<int:resort_id>/', views.subscription_detail, name='subscription_detail'),
    path('subscription/<int:resort_id>/status/', views.subscription_status, name='subscription_status'),
    path('subscription/<int:resort_id>/subscribe/', views.subscription_subscribe, name='subscription_subscribe'),
]

from django.urls import path

from . import views
app_name = "home"
urlpatterns = [
    path("", views.home, name='home'),
    path("form", views.viewAllForms, name="homeForm"),
    path("news", views.news, name="news"),
    # PlaceAddEvent
    # FROM APP CAR

     path("place/<int:id>/", views.placeCalendarJSON_v2, name="placeCalendarJSON"),
    path("place/<int:id>/<int:currentMonth>/<int:currentYear>/", views.place_v2, name="place"),
    path("place/<str:placename>/", views.checkPlace_v2, name="checkPlace"),

    # PlaceAddEvent
     path("newViaje", views.viaje_v2 , name="viaje"),
    path("refreshSchedules", views.refreshSchedules_v2, name="refreshSchedules"),
     # Add review on schedule
     path("addScheduleReview/<int:scheduleID>", views.addScheduleReview, name="addScheduleReview"),
     path("commentpost/<int:postID>",views.Comment,name="comment"),
     path("discuss/<int:placeID>", views.discussion, name="discuss"),
     path("resortDB/<int:resortID>",views.resortDB,name="resortDB")
]

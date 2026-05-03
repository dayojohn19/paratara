from django.urls import path

from . import views
app_name = "userProfile"
urlpatterns = [
    path("show_html", views.show_html, name='showhtml'),
    path("extract", views.extract_Data, name='extractUser'),
    path("", views.profile, name='profile'),
    path("deleteUser", views.deleteUser, name="deleteUser"),
    path("aboutUs", views.aboutUs, name="aboutUs"),
    path("howitwork", views.howitwork, name="howitwork"),
    path("view/<str:csrf_token>/<int:userID>",
         views.gettingUserPoster, name='profileOf'),
    path("register", views.registerUser, name="registerUser"),
    path("login", views.loginUser, name="loginUser"),
    path("loginjson", views.loginUserJSON, name="loginUserJSON"),
    path("logout", views.logoutUser, name="logoutUser"),
    path("registerjson", views.registerUserJSON, name="registerUserJSON"),
    path("logoutjson", views.logoutUserJSON, name="logoutUserJSON"),
    path("uploadPhoto", views.uploadPhoto, name="uploadPhoto"),
    path("privacypolicy", views.privacypolicy, name="privacypolicy"),
    path("termsandconditions", views.termsandconditions, name="termsandconditions"),
    path("Messages_Room", views.Messages_Room, name="Messages_Room"),
    path("changepsw", views.changePassword, name="changepsw"),
    path("tour-guide/<str:place_slug>/register/", views.tour_guide_register, name="tour_guide_register_place"),
    path("tour-guide/register/", views.tour_guide_register, name="tour_guide_register"),
    path("tour-guide/list/", views.tour_guide_list, name="tour_guide_list"),
    path("tour-guide/<int:guide_id>/toggle-status/", views.toggle_tour_guide_status, name="toggle_tour_guide_status"),
    path("tour-guide/find/<str:username>/", views.tour_guide_profile, name="tour_guide_profile"),
]

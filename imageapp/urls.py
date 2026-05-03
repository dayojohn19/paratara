from django.urls import path
from . import views
from django.http import HttpResponse
app_name = "imageapp"
urlpatterns = [
    # path('blogs/<int:place_id>/', views.get_blogs, name='get_blogs'),    
    path('upload', views.uploadimage, name="uploadimage"),
    path('images/<str:placename>/',views.getimages , name="getallimage")
]


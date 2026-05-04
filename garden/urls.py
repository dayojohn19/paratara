from django.urls import path
from . import views
from . import addingCollection

app_name = 'garden'
urlpatterns = [
    path('assets/<path:path>', views.sveltepageforgarden, name='svelte-spa'),
    
    path('add-collection/', addingCollection.update_all_collection_place_direct , name="add_collection"),
    path("map/<str:placeName>", views.get_map, name="getMap"),
    path("qr/<slug:code>/", views.qr_entry, name="qr_entry"),
    path("secret-page/", views.secret_page, name="secret_page"),    
    path('home/<str:collectionStr>', views.index, name='index'),
    path('api/collections/', views.collection_list_api, name='collection_list_api'),
    path('allplace', views.showAllPlaces, name='showAllPlaces'),
    path('placeresort/', views.placeResorts, name='placeResortsByIDdata'),
    path('placeresort/<int:placeID>/', views.placeResorts, name='placeResortsByID'),

    path('', views.viewPlaces),
    path('look/<str:collectionStr>/', views.look),
    path('look/<str:collectionStr>', views.look),
    path('look/', views.lookPlace),
    path('look', views.lookPlace),
    path('visitor/', views.visitorModel),
    path('check_visitor/', views.check_visitor, name='check_visitor'),
    path('registrationPage/', views.registrationPage, name='registrationpage'),
    path('register-from-image-bank/', views.registerAllImage, name='registerImagesFromImageBank'),
    path('upload_images/', views.upload_images, name='upload_images'),
    path('qrcode', views.CreateQRCode),
    path('collections',views.viewCollection),
    path('generate_a4_collage/', views.generate_a4_collage, name='generate_a4_collage'),
    path('list_a4_collages/', views.list_a4_collages, name='list_a4_collages'),
    # path('qrimages', views.seeAllImages),
    
]

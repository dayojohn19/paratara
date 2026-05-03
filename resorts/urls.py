from django.urls import path
from . import views
app_name = 'resorts'
urlpatterns = [
     path("event/registrations/<int:package_id>/", views.view_package_registrations, name="view_package_registrations"),
     path("accommodation/guestlist/<int:resort_id>/", views.view_accommodation_guestlist, name="view_accommodation_guestlist"),
     path("update-amenity/<int:resort_id>/", views.update_amenity, name="update_amenity"),
     path("update-contacts/<int:resort_id>/", views.update_contacts, name="update_contacts"),
     path("ocr-upload/", views.ocr_upload, name="ocr_upload"),
     path("ocr-process-openai/", views.ocr_process_openai, name="ocr_process_openai"),
     path("ocr-save-menu/", views.ocr_save_menu, name="ocr_save_menu"),
     path("<str:placeName>/", views.showresort, name="getResort2"),
    
    path("show/<str:placeName>/", views.getResort, name="showresort"),

    path("<str:placeName>/", views.showresort, name="getResort"),

    path("uploadResortGalleryImage/<int:resortID>", views.uploadResortGalleryImage, name="uploadResortGalleryImage"),
    path("deleteGalleryImage/<int:imageID>", views.deleteGalleryImage, name="deleteGalleryImage"),
 
    path("autopopulateResort", views.autopopulateResort, name="autopopulateResort"),
#     path("", views.sampleResort, name="sampleResort"),
    path("uploadUphotoTry", views.uploadUphotoTry, name="uploadUphotoTry"),
    # path("<str:placeName>/<str:ResortID>", views.getResort, name="getResort"),
    path("resort/createnewresort", views.registerResort, name="registerResort"),
    path("resort/<int:resortID>/", views.getResortwithID, name="getResortID"),
    path("<str:placeName>/json", views.getResortInJSON, name="getResortInJSON"),
    path("matterResort/<int:resortID>", views.matterResort, name="matterResort"),
    # (?P<job_number>\w+)


    path("createPackage/<int:resortID>/",
         views.createResortPackage, name="createResortPackage"),
    path("removeResortPackage/<int:resortPackageID>",
         views.removeResortPackage, name="removeResortPackage"),
    path("removeResortSubPackage/<int:resortSubPackageID>",
         views.removeResortSubPackage, name="removeResortSubPackage"),
    path("edit-package-item/<int:itemId>/",
         views.editPackageItem, name="editPackageItem"),
    path("delete-package-image/<int:imageId>/",
         views.deletePackageImage, name="deletePackageImage"),
    path("toggle-package-availability/<int:itemId>/",
         views.togglePackageAvailability, name="togglePackageAvailability"),

    path("resort", views.createPackages, name="createPackaged"),

    path("resort/sub/Image", views.createSubPackageImage, name="createImage"),
     path("event/register/<int:package_id>/", views.register_event, name="registerEvent"),
    path("putplace", views.putPlace, name="putPlace"),
    path("text/test-sms/", views.test_sms, name="test_sms"),
    path("text/test-sms-twilio/", views.test_sms_twilio, name="test_sms_twilio"),
    path("text/send-resort-sms/<int:resort_id>/", views.send_resort_sms_view, name="send_resort_sms"),
    path("text/send-resort-sms-twilio/<int:resort_id>/", views.send_resort_sms_twilio_view, name="send_resort_sms_twilio"),
    path("reactivate-resort/", views.reactivate_resort_view, name="reactivate_resort"),

]



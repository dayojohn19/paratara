# Postcard App Config (.md)

Update values below to change app behavior.

API_BASE_URL: /garden/look/
UPLOAD_API_URL: /garden/upload_images/
<!-- 
API_BASE_URL: https://www.ourblueearth.online/garden/look/
UPLOAD_API_URL: https://www.ourblueearth.online/garden/upload_images/ -->




UPLOAD_IMAGE_FIELD:
API_USERNAME:
API_USER_ID:
LOCAL_STORAGE_USERNAME_KEY: postcard_username
LOCAL_STORAGE_USER_ID_KEY: postcard_user_id
LOADING_DELAY_MS: 500
MAIN_IMAGE_URL: https://placehold.co/960x540/png
COLLECTION_1_URL: https://placehold.co/640x400/png?text=Postcard+1
COLLECTION_2_URL: https://placehold.co/640x400/png?text=Postcard+2
COLLECTION_3_URL: https://placehold.co/640x400/png?text=Postcard+3
COLLECTION_4_URL: https://placehold.co/640x400/png?text=Postcard+4

Functions used:
- fetchLookPlaceData()
- getPostcardMemories()
- formatCollectedDate(value)
- uploadImages(files)
- handleUploadSelection(event)

Behavior:
- On app load, it checks localStorage for username and userID.
- If saved values exist, they are used automatically for fetch and upload requests.
- If no saved values exist, a credentials form is shown first.
- `collectionUniqueID` is auto-derived from the last segment of `API_BASE_URL`.

## Migrations Error

 ## API REFRESHING 
 https://developers.facebook.com/tools/explorer/?method=GET&path=me%2Faccounts&version=v24.0

Meta App (right side)
USER or Page (click Page)
  then access 
 GET me/accounts

       "access_token": "",
      "category": "Business service",
      "category_list": [

        get the access token then 
        https://developers.facebook.com/tools/debug/accesstoken
        then extend the token


 then get the REFRESH IG_TOKEN
 just use User Access Token

## Creating Collections
Collections will be saved on garden/assets/collection
url is 
garden/registrationPage




Inca No .DS_Store in Directory Run this
find . -name "*.DS_Store" -type f -delete



# How To Run the Application

1.  Open Terminal to File Folder where manage.py is ```cd``` drag the file folder ```code .``` to open vsc
2.  to activate environment python

        source env/bin/actvate
3.  get local IP lan network ```ipconfig``` or ```ifconfig``` look for <o>'en0' 192.168.X.X:8000</o>

        python3 manage.py runserver 192.168.X.X:8000


# Basics of Application
1.  <g>home </g> folder is the base url Please see all urls.py
## Resorts
>   <r>http://192.168.101.69:8000/resorts/<o>NameOfResort</o></r>

>

# Create new Card
>   http://127.0.0.1:8000/garden/registrationPage/
  - Here Write new Card

>   <r>http://192.168.101.69:8000/resorts/shangrilacebu JSON</r>
resort Page

   ### Resorts Stand Alone
> [SinglePage](resorts/templates/resort/resort_onConstruction.html) 

<g>resorts/templates/resort/resort_onConstruction.html</g>

 ### Register New Resort

> http://192.168.101.69:8000/resorts/new/register

#### 1. Upload Photo
 Go to <o>https://imgbb.com</o> then sign up with <r>repapaka20@gmail.com</r> @Aa09.......... <o>https://jc-dy.imgbb.com</o>
<li> Upload and Get Image can be done with phone</li>

#### 2. Upload API 
>   <r>http://192.168.101.69:8000/resorts/shangrilacebu/json JSON</r>
will give you JSON data of the resort


 <o>https://jsonbin.io/app/bins</o> sign in with google <r>repapaka20@gmail.com</r>

<li> Create Bin -> Copy Bin ID -> on JavaScript</li>


```
  let req = new XMLHttpRequest();
  // https://jsonbin.io/app/bins
  // to Use change the last  https://api.jsonbin.io/v3/b/<BIN_ID>
    req.open("GET", "https://api.jsonbin.io/v3/b/6707f0d0e41b4d34e4406955", true);
    req.setRequestHeader("Content-Type", "application/json");
    req.setRequestHeader("X-Access-Key", "$2a$10$0DnmOTXD4FH6pg/Ww0EcvOgU5TufJYVYizT0G0B1wLaocr99G8iUS");
    req.send();
    req.onreadystatechange = () => {
    if (req.readyState == XMLHttpRequest.DONE) {
      data = JSON.parse(req.response)
      }
    };
```
Read for more info:  https://jsonbin.io/api-reference/xlbins/read


# Auto-Post to Facebook + Instagram

This project includes a Django management command that can publish to a **Facebook Page** and/or **Instagram (Business/Creator)** using Meta Graph API.

## Required Environment Variables

- `GRAPH_API_VERSION` (optional, default: `v19.0`)

Facebook Page posting:
- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`

Instagram publishing:
- `IG_USER_ID`
- `IG_ACCESS_TOKEN`

Notes:
- Instagram publishing requires a **public** `--image-url` (Instagram does not support text-only posts via this API).
- `IG_ACCESS_TOKEN` must be a **Facebook Graph API** access token (often starts with `EA...`) with Instagram permissions. Tokens that start with `IG...` are usually **Instagram Basic Display** tokens and will fail for publishing.
- Tokens/IDs must come from your Meta app setup (Facebook Login + required permissions). This repo does not generate tokens for you.

## Examples

Post to BOTH Facebook + Instagram:

  python3 manage.py post_social --message "Hello from Django" --image-url "https://example.com/my-image.jpg"

Facebook only (text post):

  python3 manage.py post_social --facebook-only --message "New update" --link "https://paratara.com"

Instagram only:

  python3 manage.py post_social --instagram-only --message "New post" --image-url "https://example.com/my-image.jpg"

Simple post to BOTH (message + image):

  # image can be a public URL
  python3 manage.py post_both "Hello from Django" "https://example.com/my-image.jpg"

  # OR a local file (auto-uploads to ImgBB for Instagram)
  # Requires IMGBB_API_KEY in .env
  python3 manage.py post_both "Hello from Django" "/absolute/path/to/image.jpg"

Post to BOTH with multiple images (FB multi-photo post + IG carousel):

  python3 manage.py post_both "Carousel test" \
    --image-url "https://via.placeholder.com/1080.jpg" \
    --image-url "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Ishihara_9.svg/250px-Ishihara_9.svg.png"

If Instagram fails with "Only photo or video can be accepted", the image host is likely blocking hotlinking.
Use `--rehost-ig` to re-upload the URLs to ImgBB before posting (requires `IMGBB_API_KEY` in `.env`):

  python3 manage.py post_both "Carousel test" --rehost-ig \
    --image-url "https://free-images.com/lg/3b8f/dalmatiner_schw_braun.jpg" \
    --image-url "https://free-images.com/lg/269b/bry.jpg"

Dry run (no network calls):

  python3 manage.py post_social --message "test" --dry-run














<style>
r { color: Red }
o { color: Orange }
g { color: Green }
</style>
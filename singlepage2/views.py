from django.utils.text import slugify
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from .forms import UserImageForm
from django.conf import settings
from openai import OpenAI
import re
import os
from typing import Optional

# Create your views here.
from django.views.decorators.csrf import csrf_exempt

def kefir(request):
    return render(request, 'singlepage2/kefir.html')
def _strip_html_tags(html: str) -> str:
    return re.sub('<[^<]+?>', '', html or '')


def ensure_blog_page_and_url(
    request: HttpRequest,
    blog_obj,
    *,
    body_html: str,
    cover_image_url: Optional[str] = None,
):
    """Generate the blog HTML file using generate_blog_page and ensure localurlpath is set.

    Designed to be reused by both the admin blog creator (blogFunc) and automated blog creation.
    """
    place = blog_obj.blogplace
    if not place:
        raise ValueError('blog_obj.blogplace is required')

    place_slug = slugify(getattr(place, 'slug', '') or getattr(place, 'placename', '') or str(place))
    title_slug = slugify(getattr(blog_obj, 'title', '') or 'blog-post')

    base_dir = os.path.dirname(os.path.abspath(__file__))
    blog_folder = os.path.join(base_dir, 'templates', 'blogs', place_slug)
    os.makedirs(blog_folder, exist_ok=True)
    file_path = os.path.join(blog_folder, f"{title_slug}.html")

    from .htmlwriter import generate_blog_page
 
    cover_image_url_to_use = cover_image_url or getattr(place, 'placePhoto', None) or "https://www.paratara.com/static/images/sugbalagoon-cover.jpg"
    htmlvalue = generate_blog_page(
        request,
        place_name=str(place_slug),
        title=str(getattr(blog_obj, 'title', '') or 'Travel Guide'),
        body_text=body_html,
        cover_image_url=str(cover_image_url_to_use),
        faq_entries=[
            {
                "@type": "Question",
                "name": f"What to know about {getattr(place, 'placename', place_slug)}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": str(getattr(blog_obj, 'summarize', '') or f"Guide to {getattr(place, 'placename', place_slug)}")
                }
            },
        ]
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(htmlvalue)

    desired_url = f"/pages/blog/{place_slug}/{title_slug}/"
    if getattr(blog_obj, 'localurlpath', '') != desired_url:
        blog_obj.localurlpath = desired_url
        blog_obj.save(update_fields=['localurlpath'])

    return blog_obj


def create_blog_from_user_request(
    request: HttpRequest,
    *,
    place,
    title: str,
    body_html: str,
    summary: Optional[str] = None,
    category: str = 'Guide',
    cover_image_url: Optional[str] = None,
):
    """Create a new blog record + page if a matching title doesn't already exist for the place."""
    from apis.models import Blogs

    title = (title or '').strip() or f"Guide to {getattr(place, 'placename', 'this place')}"
    title_slug = slugify(title)

    # Prevent duplicates by comparing slugified titles within the place.
    existing = list(place.blog.all())
    for b in existing:
        if slugify(getattr(b, 'title', '') or '') == title_slug:
            return b

    text_content = _strip_html_tags(body_html)
    word_count = len(text_content.split())
    read_time = max(1, round(word_count / 200))

    blog_obj = Blogs.objects.create(
        blogplace=place,
        title=title[:64],
        category=category,
        summarize=(summary or text_content[:140] or f"Guide to {getattr(place, 'placename', title)}")[:400],
        readtime=read_time,
    )

    # Link to place (ManyToMany)
    place.blog.add(blog_obj)

    ensure_blog_page_and_url(
        request,
        blog_obj,
        body_html=body_html,
        cover_image_url=cover_image_url,
    )
    return blog_obj

def generate_blog_metadata(html_content):
    """Use OpenAI to generate title, summary, and estimated read time from HTML content"""
    client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
    
    # Strip HTML tags for word count
    text_content = _strip_html_tags(html_content)
    word_count = len(text_content.split())
    read_time = max(1, round(word_count / 200))  # 200 words per minute
    
    try:
        response = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a travel blog editor. Generate concise, engaging titles and summaries for travel blog posts."},
                {"role": "user", "content": f"""Based on this blog content, generate:
1. A catchy, SEO-friendly title (max 60 characters)
2. A compelling summary/excerpt (max 160 characters)

Content:
{text_content[:3000]}

Respond in JSON format:
{{
  "title": "your title here",
  "summary": "your summary here"
}}"""}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return {
            'title': result.get('title', 'Untitled Blog Post')[:64],
            'summary': result.get('summary', 'Read more about this travel destination.')[:400],
            'read_time': read_time
        }
    except Exception as e:
        print(f"OpenAI Error: {e}")
        # Fallback to basic extraction
        first_h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE)
        title = first_h1.group(1) if first_h1 else 'Travel Guide'
        return {
            'title': title[:64],
            'summary': text_content[:160] if text_content else 'A travel guide.',
            'read_time': read_time
        }


def blogFunc(request):
    # class Places_v2(models.Model):
    # blog = models.ManyToManyField('apis.Blogs', blank=True, related_name="bloglists")
    from home.models import Places_v2
    from apis.models import Blogs
    from apis.forms import BlogsForm
    if request.method == "POST":
        html_content = request.POST.get('htmlelements', '')
        
        # Generate metadata using OpenAI
        print("🤖 Generating blog metadata with OpenAI...")
        metadata = generate_blog_metadata(html_content)
        
        form = BlogsForm(request.POST, request.FILES)
        if form.is_valid():
            blog_instance = form.save(commit=False)
            
            # Auto-fill title, summary, and read time if not provided
            if not blog_instance.title or blog_instance.title.strip() == '':
                blog_instance.title = metadata['title']
            
            # Always use OpenAI-generated summary, or if existing summary starts with "Learn more about"
            if (not blog_instance.summarize or 
                blog_instance.summarize.strip() == '' or 
                blog_instance.summarize.startswith('Learn more about')):
                blog_instance.summarize = metadata['summary']
            
            blog_instance.readtime = metadata['read_time']
            
            blog_instance.save()
            form.instance.blogplace.blog.add(blog_instance)

            ensure_blog_page_and_url(
                request,
                blog_instance,
                body_html=html_content,
                cover_image_url="https://www.paratara.com/static/images/sugbalagoon-cover.jpg",
            )
            
            print(f"✅ Blog created: {blog_instance.title}")
            print(f"📊 Summary: {blog_instance.summarize}")
            print(f"⏱️  Read time: {blog_instance.readtime} min")
            print(f"🔗 URL: {blog_instance.localurlpath}")



            context = {
                'message': f'✅ Blog "{blog_instance.title}" posted successfully!',
                'blogform': BlogsForm(),
                'last_blog': blog_instance
            }
            return render(request, 'apis/blog.html', context)
            # return redirect("blogFunc")  # redirect to same page after saving
    else:
        form = BlogsForm()

    
    
    context = {
        'blogform':form,
        'places':Places_v2.objects.all()
    }
    return render(request, 'apis/blog.html',context)



def blog_html(request, slug,slugSec, slugName=None):    
    if slugName:
        from home.models import TouristSpot
        spot = TouristSpot.objects.filter(slug=slugName).first()
        print('\n\n SPOT:', spot)
        if spot:
            return render(request, f'blogs/{slug}/{slugSec}.html', {
                'tourguide' : spot.tourguide.filter(is_active=True)
            })

    # path('bucasgrande/',TemplateView.as_view(template_name='blogs/siargao/bucasgrande.html',extra_context=siargao_links), name='bucasgrande'),

    return render(request, f'blogs/{slug}/{slugSec}.html')



def chemtrix(request):
    # return render(request, "blogs/other/chemtrix.html ")
    return render(request, 'blogs/other/chemtrix.html'    )

def resortgroup(request):
    
    # "paypal_client_id": settings.PAYPAL_CLIENT_ID,             
    return render(request, 'singlepage2/resortgroup.html', {"paypal_client_id": settings.PAYPAL_CLIENT_ID,             })

def upploadtheimage(request):
    if request.method == 'POST':
        import time
        from imageapp.imageuploader import Upload_and_get_URL
        print('Uploading Started\n\n')
        time.sleep(2)
        # form = ImageForm(request.POST, request.FILES)
        # if form.is_valid():
        urls = Upload_and_get_URL(request)
        print('Successfully Uploaded: ',urls)
        return render(request, 'singlepage2/services.html',{ 'renderedimage':urls})

    elif request.method == 'GET':
        from singlepage2.forms import ImgUploadForm
        form = ImgUploadForm()
        from imageapp.imageuploader import Upload_and_get_URL, ImageForm
        from imageapp.forms import ImageForm
        return render(request, 'singlepage2/services.html',{ 'imageform':ImageForm})

# @csrf_exempt  # remove this if you're using {% csrf_token %} in form
# def upload_imgbb(request):
#     if request.method == "GET":
#         from singlepage2.forms import ImgUploadForm
#         form = ImgUploadForm()
#         from imageapp.imageuploader import Upload_and_get_URL, ImageForm
#         from imageapp.forms import ImageForm
#         return render(request, 'singlepage2/uploadimage.html',{'form': form, 'imageform':ImageForm})

#     elif request.method == "POST":
#         form = UserImageForm(request.POST, request.FILES)
#         file_obj = request.FILES.get("image")
#         if form.is_valid():
#             file_obj = request.FILES["image"]
#             # from ..webSchedule.utils import upload_to_imgbb
#             # from ..webSchedule.utils import upload_to_imgbb
#             from webSchedule.utils import upload_to_imgbb
#             image_url = upload_to_imgbb(file_obj)
#             print("\n\n IMAGE URL: ", image_url)
#             form.save()
#             return render(request, 'singlepage2/uploadimage.html', {'form': form, 'image_url': image_url})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def SinglePageHome(request, path=''):
    from django.http import HttpResponse
    import os
    
    # Serve Svelte app assets or fallback to index.html for SPA routing
    dist_dir = os.path.join(settings.BASE_DIR, 'singlepage2/static/svelte test  v1.2/dist')
    if path:
        asset_path = os.path.join(dist_dir, path.replace('/pages/', '').lstrip('/'))
    else:
        asset_path = os.path.join(dist_dir, 'index.html')
    
    if os.path.exists(asset_path) and os.path.isfile(asset_path):
        with open(asset_path, 'rb') as f:
            content = f.read()
        if asset_path.endswith('.html'):
            mime_type = 'text/html'
        elif asset_path.endswith('.css'):
            mime_type = 'text/css'
        elif asset_path.endswith('.js'):
            mime_type = 'application/javascript'
        elif asset_path.endswith('.png'):
            mime_type = 'image/png'
        elif asset_path.endswith('.jpg') or asset_path.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif asset_path.endswith('.gif'):
            mime_type = 'image/gif'
        elif asset_path.endswith('.svg'):
            mime_type = 'image/svg+xml'
        elif asset_path.endswith('.ico'):
            mime_type = 'image/x-icon'
        elif asset_path.endswith('.woff'):
            mime_type = 'font/woff'
        elif asset_path.endswith('.woff2'):
            mime_type = 'font/woff2'
        else:
            mime_type = 'application/octet-stream'
        print(f"Serving asset: {asset_path} (MIME: {mime_type})")
        return HttpResponse(content, content_type=mime_type)
    else:
        print(f"Serving index.html fallback for path: {path}")
        index_path = os.path.join(dist_dir, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content)

def services(request):
    return render(request, 'singlepage2/services.html')
    
# def home(request):
#     from SinglePage.views import SinglePageHome
#     return SinglePageHome(request)



def cebutravelbooking(request, csrf_token=None):
    print("\n CSRF: ", csrf_token)
    if csrf_token is not None:
        data = {
            "with_csrf": "CSRF with"
        }
    else:
        data = {

        }
    # AMBsnN7BbDvbubEyl5E5u7vDppNUUBNk6ZIbG8NGLXyfLxecTmZc4P3bP1dv3CeS
    return render(request, 'SinglePage/travel/philippines/cebu/cebucity/travelbooking.html', data)


# def get_html_empty(request, csrf_token, htmlfile, pagetitle=None):

#     return get_html(request, csrf_token, htmlfile, pagetitle=None)


# def get_html(request, csrf_token, htmlfile, pagetitle=None):

#     print('GET TRAVEL\n\n\n')
#     try:
#         from .models import TravelPages2
#         bodytag = TravelPages2.objects.get(html_title=pagetitle)
#         print('\n\n', bodytag)
#         data = {
#             "html_object": bodytag
#         }
#         return render(request, htmlfile, data)
#     except:
#         return render(request, htmlfile)

# def get_html(request: HttpRequest, pk=None) -> HttpResponse:
#     return render(request, 'index.html')

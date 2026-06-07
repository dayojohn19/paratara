from django.utils.text import slugify
from django.shortcuts import render
from django.http import HttpResponse, HttpRequest, JsonResponse
from .forms import UserImageForm
from django.conf import settings
from openai import OpenAI
from bs4 import BeautifulSoup
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST
import re
import os
import json
import stat
from ipaddress import ip_address
from typing import Optional
from urllib.parse import urlparse
from html import unescape
from mimetypes import guess_type

try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
except ImportError:
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None

try:
    import torch
except ImportError:
    torch = None

# Create your views here.
from django.views.decorators.csrf import csrf_exempt

def kefir(request):
    return render(request, 'singlepage2/kefir.html')
def _strip_html_tags(html: str) -> str:
    return re.sub('<[^<]+?>', '', html or '')


BLOG_EDIT_ALLOWED_TAGS = {
    "a",
    "b",
    "br",
    "code",
    "em",
    "i",
    "img",
    "mark",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "u",
}
BLOG_EDIT_DROP_TAGS = {
    "button",
    "embed",
    "form",
    "iframe",
    "input",
    "link",
    "meta",
    "object",
    "option",
    "script",
    "select",
    "style",
    "svg",
    "textarea",
}
BLOG_EDIT_ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding", "class"},
    "span": {"class"},
}

_GRAMMAR_MODEL = None
_GRAMMAR_TOKENIZER = None


def _load_grammar_model():
    global _GRAMMAR_MODEL, _GRAMMAR_TOKENIZER
    if _GRAMMAR_MODEL is not None and _GRAMMAR_TOKENIZER is not None:
        return True

    if AutoModelForSeq2SeqLM is None or AutoTokenizer is None:
        return False

    model_source = getattr(settings, "GRAMMAR_MODEL_PATH", None) or getattr(settings, "GRAMMAR_MODEL_NAME", None)
    if not model_source:
        model_source = "vennify/t5-base-grammar-correction"

    try:
        _GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained(model_source, local_files_only=True)
        _GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_source, local_files_only=True)
        if torch is not None and torch.cuda.is_available():
            _GRAMMAR_MODEL.to(torch.device("cuda"))
        return True
    except Exception as exc:
        print(f"Local grammar model load failed: {exc}")

    try:
        _GRAMMAR_TOKENIZER = AutoTokenizer.from_pretrained(model_source, local_files_only=False)
        _GRAMMAR_MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_source, local_files_only=False)
        if torch is not None and torch.cuda.is_available():
            _GRAMMAR_MODEL.to(torch.device("cuda"))
        return True
    except Exception as exc:
        print(f"Grammar model load failed: {exc}")
        _GRAMMAR_MODEL = None
        _GRAMMAR_TOKENIZER = None
        return False


def _correct_grammar_text(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    if not _load_grammar_model():
        return text

    prompt_prefix = getattr(settings, "GRAMMAR_MODEL_PROMPT_PREFIX", "fix grammar: ")
    prompt = f"{prompt_prefix}{text}"

    try:
        inputs = _GRAMMAR_TOKENIZER(prompt, return_tensors="pt", truncation=True, max_length=1024)
        if torch is not None and torch.cuda.is_available():
            inputs = {k: v.to(torch.device("cuda")) for k, v in inputs.items()}

        outputs = _GRAMMAR_MODEL.generate(
            **inputs,
            max_length=1024,
            num_beams=3,
            early_stopping=True,
        )
        corrected = _GRAMMAR_TOKENIZER.decode(outputs[0], skip_special_tokens=True)
        return corrected.strip() or text
    except Exception as exc:
        print(f"Grammar correction failed: {exc}")
        return text


def _correct_html_text_nodes(html: str) -> str:
    fragment = BeautifulSoup(html or "", "html.parser")
    for text_node in fragment.find_all(string=True):
        if text_node.parent.name in {"script", "style"}:
            continue
        original = str(text_node).strip()
        if not original:
            continue
        corrected = _correct_grammar_text(original)
        if corrected != original:
            text_node.replace_with(corrected)
    return str(fragment)


def _is_allowed_blog_edit_url(value, *, image=False):
    value = (value or "").strip()
    if not value:
        return False

    if value.startswith(("/", "./", "../", "#")):
        return not image or not value.startswith("#")

    parsed = urlparse(value)
    if image:
        return parsed.scheme in {"http", "https"}

    return parsed.scheme in {"http", "https", "mailto", "tel"}


def _sanitize_blog_edit_html(html):
    fragment = BeautifulSoup(unescape(html or ""), "html.parser")

    for tag in list(fragment.find_all(True)):
        tag.name = tag.name.lower()

        if tag.name in BLOG_EDIT_DROP_TAGS:
            tag.decompose()
            continue

        if tag.name not in BLOG_EDIT_ALLOWED_TAGS:
            tag.unwrap()
            continue

        allowed_attrs = BLOG_EDIT_ALLOWED_ATTRS.get(tag.name, set())
        for attr_name in list(tag.attrs):
            attr_key = attr_name.lower()
            attr_value = tag.attrs.get(attr_name)

            if attr_key.startswith("on") or attr_key not in allowed_attrs:
                del tag.attrs[attr_name]
                continue

            if attr_key in {"href", "src"}:
                is_image = tag.name == "img" and attr_key == "src"
                if not _is_allowed_blog_edit_url(str(attr_value), image=is_image):
                    del tag.attrs[attr_name]
                    continue
                tag.attrs[attr_name] = str(attr_value).strip()

            if attr_key in {"width", "height"} and not str(attr_value).strip().isdigit():
                del tag.attrs[attr_name]

        if tag.name == "img":
            if not tag.get("src"):
                tag.decompose()
                continue

            tag["loading"] = tag.get("loading") or "lazy"
            tag["decoding"] = tag.get("decoding") or "async"
            tag["alt"] = tag.get("alt") or "Blog content image"
            classes = tag.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            if "editable-blog-image" not in classes:
                classes.append("editable-blog-image")
            tag["class"] = classes

        if tag.name == "a":
            if not tag.get("href"):
                tag.unwrap()
                continue
            if tag.get("target") == "_blank":
                tag["rel"] = "noopener noreferrer"

    return str(fragment).strip()


def _blog_edit_html_has_visible_content(html):
    fragment = BeautifulSoup(html or "", "html.parser")
    return bool(fragment.get_text(strip=True) or fragment.find("img", src=True))


def _extract_blog_slugs_from_path(path):
    parts = [part for part in (path or "").split("/") if part]
    if len(parts) >= 4 and parts[0] == "pages" and parts[1] == "blog":
        return parts[2], parts[3]
    return "", ""


def _blog_edit_slugs(place_slug="", title_slug="", page_url=""):
    page_path = urlparse(page_url).path if page_url and "://" in page_url else page_url
    parsed_place_slug, parsed_title_slug = _extract_blog_slugs_from_path(page_path)
    place_slug = place_slug or parsed_place_slug
    title_slug = title_slug or parsed_title_slug

    place_slug = slugify(place_slug or "")
    title_slug = slugify(title_slug or "")
    return place_slug, title_slug


def _blog_template_file_path(place_slug="", title_slug="", page_url=""):
    place_slug, title_slug = _blog_edit_slugs(place_slug, title_slug, page_url)
    if not place_slug or not title_slug:
        return None

    blogs_root = os.path.abspath(os.path.join(settings.BASE_DIR, "singlepage2", "templates", "blogs"))
    file_path = os.path.abspath(os.path.join(blogs_root, place_slug, f"{title_slug}.html"))

    if os.path.commonpath([blogs_root, file_path]) != blogs_root:
        return None

    return file_path


def _candidate_blog_paths(place_slug, title_slug, page_url=""):
    paths = set()
    raw_paths = []

    if page_url:
        raw_paths.append(urlparse(page_url).path if "://" in page_url else page_url)

    if place_slug and title_slug:
        raw_paths.append(f"/pages/blog/{place_slug}/{title_slug}/")

    for raw_path in raw_paths:
        if not raw_path:
            continue
        path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
        paths.add(path)
        paths.add(path.rstrip("/"))
        paths.add(path if path.endswith("/") else f"{path}/")

    return paths


def _find_blog_for_edit(place_slug="", title_slug="", page_url=""):
    from apis.models import Blogs

    place_slug, title_slug = _blog_edit_slugs(place_slug, title_slug, page_url)
    paths = _candidate_blog_paths(place_slug, title_slug, page_url)
    if paths:
        blog = Blogs.objects.filter(localurlpath__in=paths).first()
        if blog:
            return blog

    if not place_slug or not title_slug:
        return None

    place_name = place_slug.replace("-", " ")
    candidates = Blogs.objects.select_related("blogplace").filter(
        Q(blogplace__slug=place_slug) | Q(blogplace__placename__iexact=place_name)
    )
    for blog in candidates:
        if slugify(blog.title or "") == title_slug:
            return blog
    return None


def _format_blog_datetime(value):
    value = value or timezone.now()
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    display = value.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")
    return value.isoformat(), display


def _get_request_ip(request):
    raw_ip = (
        (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        or (request.META.get("HTTP_X_REAL_IP") or "").strip()
        or (request.META.get("REMOTE_ADDR") or "").strip()
    )
    if not raw_ip:
        return None

    try:
        return str(ip_address(raw_ip))
    except ValueError:
        return None


def _update_article_schema_modified_date(soup, updated_at):
    date_modified = timezone.localtime(updated_at).date().isoformat()

    def update_article(data):
        changed = False
        if isinstance(data, dict):
            schema_type = data.get("@type")
            is_article = schema_type == "Article" or (
                isinstance(schema_type, list) and "Article" in schema_type
            )
            if is_article:
                data["dateModified"] = date_modified
                changed = True
            graph = data.get("@graph")
            if isinstance(graph, list):
                changed = update_article(graph) or changed
        elif isinstance(data, list):
            for item in data:
                changed = update_article(item) or changed
        return changed

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text() or "{}")
        except json.JSONDecodeError:
            continue
        if update_article(data):
            script.string = json.dumps(data, indent=2)


def _ensure_blog_template_write_permission(file_path):
    directory = os.path.dirname(file_path)

    try:
        directory_mode = os.stat(directory).st_mode
        if not directory_mode & stat.S_IWUSR:
            os.chmod(directory, directory_mode | stat.S_IWUSR | stat.S_IXUSR)

        file_mode = os.stat(file_path).st_mode
        if not file_mode & stat.S_IWUSR:
            os.chmod(file_path, file_mode | stat.S_IWUSR)
    except OSError as exc:
        return False, f"Could not set write permission for template file: {exc}"

    if not os.access(file_path, os.W_OK):
        return False, "Template file is not writable by the web app user"
    if not os.access(directory, os.W_OK):
        return False, "Template directory is not writable by the web app user"

    return True, ""


def _update_last_updated_marker(soup, updated_at):
    updated_iso, updated_display = _format_blog_datetime(updated_at)
    meta_style = (
        "display:flex;flex-wrap:wrap;gap:0.5rem 1rem;margin:0 0 1.5rem;"
        "padding-bottom:0.9rem;color:#65736d;font-size:0.92rem;"
        "border-bottom:1px solid #d8ded7;"
    )
    time_style = "color:#27332f;font-weight:650;"
    time_tag = soup.find(id="blog-last-updated")

    if time_tag:
        meta = time_tag.find_parent(class_="blog-date-meta")
        if meta and not meta.get("style"):
            meta["style"] = meta_style
        if not time_tag.get("style"):
            time_tag["style"] = time_style
        time_tag["datetime"] = updated_iso
        time_tag.clear()
        time_tag.append(updated_display)
        return

    meta = soup.new_tag("p", attrs={"class": "blog-date-meta", "style": meta_style})
    span = soup.new_tag("span")
    span.append("Last updated ")
    time_tag = soup.new_tag("time", attrs={
        "id": "blog-last-updated",
        "datetime": updated_iso,
        "style": time_style,
    })
    time_tag.append(updated_display)
    span.append(time_tag)
    meta.append(span)

    editable_body = soup.find(id="blog-editable-body")
    body_contents = soup.find(id="body-contents")
    if editable_body:
        editable_body.insert_before(meta)
    elif body_contents:
        body_contents.insert(0, meta)


def _patch_blog_template_file(paragraph_index, edited_html, editable_tag="", place_slug="", title_slug="", page_url="", updated_at=None):
    file_path = _blog_template_file_path(place_slug, title_slug, page_url)
    if not file_path or not os.path.exists(file_path):
        return False, file_path, "Template file not found"

    can_write, permission_error = _ensure_blog_template_write_permission(file_path)
    if not can_write:
        return False, file_path, permission_error

    try:
        with open(file_path, "r", encoding="utf-8") as template_file:
            html = template_file.read()
    except OSError as exc:
        return False, file_path, f"Could not read template file: {exc}"

    soup = BeautifulSoup(html, "html.parser")
    editable_body = soup.find(id="blog-editable-body")
    if not editable_body:
        return False, file_path, "Editable blog body not found"

    editable_tag = (editable_tag or "").lower()
    allowed_editable_tags = {"h2", "p"}
    if editable_tag and editable_tag not in allowed_editable_tags:
        return False, file_path, "Unsupported editable section"

    selector = f'{editable_tag}[data-blog-edit-index="{paragraph_index}"]' if editable_tag else f'[data-blog-edit-index="{paragraph_index}"]'
    target = editable_body.select_one(selector)
    if not target:
        paragraphs = editable_body.find_all("p", attrs={"data-blog-edit-index": True})
        if paragraph_index >= len(paragraphs):
            return False, file_path, "Editable section not found"
        target = paragraphs[paragraph_index]

    if target.name not in allowed_editable_tags:
        return False, file_path, "Unsupported editable section"

    target.clear()
    fragment = BeautifulSoup(edited_html, "html.parser")
    for child in list(fragment.contents):
        target.append(child)
    edited_at = updated_at or timezone.now()
    _update_last_updated_marker(soup, edited_at)
    _update_article_schema_modified_date(soup, edited_at)

    try:
        with open(file_path, "w", encoding="utf-8") as template_file:
            template_file.write(str(soup))
    except OSError as exc:
        return False, file_path, f"Could not write template file: {exc}"

    return True, file_path, ""


@require_POST
def save_blog_paragraph_file_edit(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    place_slug = (payload.get("place_slug") or "").strip()
    title_slug = (payload.get("title_slug") or "").strip()
    page_url = (payload.get("page_url") or "").strip()
    editable_tag = (payload.get("editable_tag") or "").strip().lower()
    raw_edited_html = payload.get("edited_html")
    if raw_edited_html is None:
        raw_edited_html = payload.get("edited_text") or ""
    edited_html = _sanitize_blog_edit_html(raw_edited_html).strip()
    edited_html = _correct_html_text_nodes(edited_html).strip()
    edited_text = _strip_html_tags(edited_html).strip()

    try:
        paragraph_index = int(payload.get("paragraph_index"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "Invalid editable section index"}, status=400)

    if paragraph_index < 0:
        return JsonResponse({"ok": False, "error": "Invalid editable section index"}, status=400)
    if not _blog_edit_html_has_visible_content(edited_html):
        return JsonResponse({"ok": False, "error": "Section cannot be empty"}, status=400)
    if len(edited_html) > 12000:
        return JsonResponse({"ok": False, "error": "Section is too long"}, status=400)

    edited_at = timezone.now()
    edited_ip = _get_request_ip(request)
    blog = _find_blog_for_edit(place_slug, title_slug, page_url)

    file_updated, file_path, file_error = _patch_blog_template_file(
        paragraph_index,
        edited_html,
        editable_tag=editable_tag,
        place_slug=place_slug,
        title_slug=title_slug,
        page_url=page_url,
        updated_at=edited_at,
    )
    if not file_updated:
        error_status = 500 if "permission" in (file_error or "").lower() or "write" in (file_error or "").lower() else 404
        return JsonResponse({
            "ok": False,
            "error": file_error or "Could not update template file",
            "file_path": file_path or "",
        }, status=error_status)

    blog_updated = False
    if blog:
        type(blog).objects.filter(pk=blog.pk).update(
            updated_at=edited_at,
            last_updated_ip=edited_ip,
        )
        blog_updated = True

    updated_at_iso, updated_at_display = _format_blog_datetime(edited_at)
    return JsonResponse({
        "ok": True,
        "blog_id": blog.id if blog else None,
        "blog_updated": blog_updated,
        "paragraph_index": paragraph_index,
        "editable_tag": editable_tag,
        "edited_text": edited_text,
        "edited_html": edited_html,
        "updated_at": updated_at_iso,
        "updated_at_display": updated_at_display,
        "last_updated_ip": edited_ip,
        "file_updated": file_updated,
        "file_path": file_path or "",
    })


def ensure_blog_page_and_url(request: HttpRequest,blog_obj = None,*,body_html: str,cover_image_url: Optional[str] = None,):
    print('Not Used: ensure_blog_page_and_url - changed to generate_blog_object')
    return
    """Generate the blog HTML file using generate_blog_page and ensure localurlpath is set.

    Designed to be reused by both the admin blog creator (blogFunc) and automated blog creation.
    """
    # place = blog_obj.blogplace
    # if not place:
    #     raise ValueError('blog_obj.blogplace is required')

    # place_slug = slugify(getattr(place, 'slug', '') or getattr(place, 'placename', '') or str(place))
    # title_slug = slugify(getattr(blog_obj, 'title', '') or 'blog-post')

    # base_dir = os.path.dirname(os.path.abspath(__file__))
    # blog_folder = os.path.join(base_dir, 'templates', 'blogs', place_slug)
    # os.makedirs(blog_folder, exist_ok=True)
    # file_path = os.path.join(blog_folder, f"{title_slug}.html")

    from .htmlwriter import generate_blog_object
  
    # cover_image_url_to_use = cover_image_url or getattr(place, 'placePhoto', None) or "https://www.paratara.com/static/images/sugbalagoon-cover.jpg"
    # print('Generating blog page with cover image:', cover_image_url_to_use)
    print('Blog title:', getattr(blog_obj, 'title', 'No title'))
    print('-----cover image-----')
    print('----------')
    print('----------')
    htmlvalue = generate_blog_object(
        request,
        place_name=str(place_slug),
        title=str(getattr(blog_obj, 'title', '') or 'Travel Guide'),
        body_text=body_html,
        cover_image_url=str(cover_image_url_to_use),
    )


    return blog_obj


def create_blog_from_user_request(request: HttpRequest,*,place,title: str,body_html: str,summary: Optional[str] = None,category: str = 'Guide',cover_image_url: Optional[str] = None,):
    print('Not Used: create_blog_from_user_request - changed to generate_blog_object')
    return
    # """Create a new blog record + page if a matching title doesn't already exist for the place."""
    # from apis.models import Blogs

    # title = (title or '').strip() or f"{category} to {getattr(place, 'placename', 'this place')}"
    # title_slug = slugify(title)

    # Prevent duplicates by comparing slugified titles within the place.
    # existing = list(place.blog.all())
    # for b in existing:
    #     if slugify(getattr(b, 'title', '') or '') == title_slug:
    #         print('place existing')
    #         return b


    # text_content = _strip_html_tags(body_html)
    # print('')
    # print('')
    # # print('Word count for blog content:', len(text_content.split()))
    # # print('type of text_content:', type(text_content))
    # print('')
    # print('')


    # blog_obj = Blogs.objects.create(
    #     blogplace=place,
    #     title=title[:64],
    #     category=category,
    #     summarize=(summary or text_content[:140] or f"Guide to {getattr(place, 'placename', title)}")[:400],
    #     textContent=text_content,
    #     readtime=read_time,
    # )

    # # Link to place (ManyToMany)
    # place.blog.add(blog_obj)

    ensure_blog_page_and_url(
        request,

        body_html=body_html,
        cover_image_url=cover_image_url,
    )
    return blog_obj
# NOT USED
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

# NOT USED
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


def blog_asset(request, slug, asset_name):
    place_slug = slugify(slug or "")
    safe_asset_name = os.path.basename(asset_name or "")
    if not place_slug or not safe_asset_name:
        return HttpResponse("Not found", status=404)

    blogs_root = os.path.abspath(os.path.join(settings.BASE_DIR, "singlepage2", "templates", "blogs"))
    asset_path = os.path.abspath(os.path.join(blogs_root, place_slug, "assets", safe_asset_name))

    if os.path.commonpath([blogs_root, asset_path]) != blogs_root or not os.path.isfile(asset_path):
        return HttpResponse("Not found", status=404)

    content_type = guess_type(asset_path)[0] or "application/octet-stream"
    with open(asset_path, "rb") as asset_file:
        return HttpResponse(asset_file.read(), content_type=content_type)



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

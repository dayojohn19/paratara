"""
Non-AI version of htmlwriter.py functions
Handles blog creation without requiring Grok AI client
"""

import os
import re
import json
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse

from html import escape
from bs4 import BeautifulSoup

from garden.models import Collection, CollectionGroup
from home.models import Places_v2
from apis.models import Blogs


def clean_blog_metadata(value):
    """Remove HTML tags and extra whitespace from metadata"""
    value = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', str(value or ''), flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def normalize_blog_category(category):
    """Ensure category is one of the valid choices"""
    VALID_CATEGORIES = {'Guide', 'Story', 'Tip and Trick', 'Explore', 'Product'}
    category = clean_blog_metadata(category).strip("'\"")
    return category if category in VALID_CATEGORIES else 'Guide'


def mark_editable_blog_body(body_html):
    """Mark blog body sections as editable"""
    soup = BeautifulSoup(body_html or "", "html.parser")
    
    for container in soup.find_all(["section", "aside", "footer"]):
        if not container.get('id'):
            container['id'] = f"editable-{slugify(container.name)}-{id(container)}"
        container['data-blog-edit-scope'] = 'body'
        container['data-blog-edit-tag'] = container.name
    
    for idx, editable_block in enumerate(soup.find_all(["h2", "p"])):
        editable_block['data-blog-edit-index'] = str(idx)
        editable_block['data-blog-edit-scope'] = 'body'
        editable_block['data-blog-edit-tag'] = editable_block.name
    
    for image in soup.find_all("img"):
        image['data-blog-edit-scope'] = 'image'
        image['data-blog-edit-tag'] = 'img'
    
    return str(soup)


def format_blog_datetime(value):
    """Format datetime for display"""
    value = value or timezone.now()
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    
    published_iso = value.isoformat()
    display = value.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")
    return published_iso, display


def render_faq_section(faq_entries):
    """Render FAQ section HTML"""
    rows = []
    
    for faq_index, entry in enumerate(faq_entries or []):
        if isinstance(entry, dict):
            question = entry.get('question', '')
            answer = entry.get('answer', '')
        else:
            continue
        
        if not question or not answer:
            continue
        
        row_html = f"""
        <div class="faq-item" data-faq-index="{faq_index}">
            <h3 data-blog-edit-index="{faq_index}" data-blog-edit-scope="faq" data-blog-edit-tag="h3">{escape(question)}</h3>
            <p data-blog-edit-index="{faq_index}" data-blog-edit-scope="faq_answer" data-blog-edit-tag="p">{escape(answer)}</p>
        </div>
        """
        rows.append(row_html)
    
    if not rows:
        return ""
    
    return f"""
    <section class="faq-section" aria-labelledby="faq-heading">
        <h2 id="faq-heading" data-blog-edit-index="0" data-blog-edit-scope="faq" data-blog-edit-tag="h2">Frequently Asked Questions</h2>
        <div class="faq-list">
            {''.join(rows)}
        </div>
    </section>
    """


def generate_blog_object(place_name, title, category='Guide', summary='No Summary Provided', 
                         text_content='', cover_image_url='', meta_description='', 
                         searchable_keywords='', seo_title='', longitude='', latitude='', 
                         faq_entries=None):
    """
    Create a blog object in the database without AI
    """
    place = Places_v2.objects.filter(placename__iexact=place_name).first()
    if not place:
        raise ValueError(f"Place '{place_name}' not found in database")
    
    category = normalize_blog_category(category)
    summary = clean_blog_metadata(summary)[:400] or 'No Summary Provided'
    title = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', title, flags=re.IGNORECASE | re.DOTALL)
    
    # Calculate read time from plain text
    plain_text_content = re.sub('<[^<]+?>', '', text_content or '')
    readtime = max(1, len(plain_text_content.split()) // 185) if plain_text_content else 5
    
    # Check for duplicates
    existing = Blogs.objects.filter(title__iexact=title, blogplace=place).first()
    if existing:
        raise ValueError(f"A blog with title '{title}' already exists for this place")
    
    # Create blog object
    blog_item = Blogs.objects.create(
        category=category,
        blogplace=place,
        title=title,
        textContent=plain_text_content,
        summarize=summary,
        readtime=readtime,
        cover_image_url=cover_image_url or '',
        meta_description=meta_description or '',
        searchable_keywords=searchable_keywords or '',
        seo_title=seo_title or title,
        longitude=longitude or '',
        latitude=latitude or '',
        faq_entries=faq_entries or []
    )
    
    place.blog.add(blog_item)
    return blog_item


def generate_blog_page(request, place_name, title, body_text, cover_image_url=None, 
                       faq_entries=None, meta_description=None, category=None, 
                       searchable_keywords=None):
    """
    Generate optimized blog HTML page without AI
    """
    category = normalize_blog_category(category)
    
    place_slug = slugify(place_name)
    title_slug = slugify(title)
    
    # Define folder path
    folder_path = os.path.join(
        settings.BASE_DIR,
        "singlepage2", "templates", "blogs", place_slug
    )
    
    # Create folder if missing
    try:
        os.makedirs(folder_path, exist_ok=True)
    except OSError:
        pass
    
    # The final HTML file location
    file_path = os.path.join(folder_path, f"{title_slug}.html")
    
    # The canonical full URL on your live site
    canonical_url = f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"
    editable_body_text = mark_editable_blog_body(body_text)
    generated_at = timezone.now()
    published_iso, published_display = format_blog_datetime(generated_at)
    modified_iso, modified_display = format_blog_datetime(generated_at)
    schema_date = timezone.localtime(generated_at).date().isoformat()
    
    csrf_token = ""
    if request is not None:
        csrf_token = get_token(request)
    
    upload_url = reverse("imageapp:uploadimage")
    subscribe_url = reverse("apis:subscribe_email")
    blog_edit_save_url = reverse("singlepage2:save_blog_paragraph_file_edit")
    
    # Build FAQ Schema
    faq_schema = ""
    if faq_entries:
        faq_items = []
        for entry in faq_entries:
            if isinstance(entry, dict):
                faq_items.append({
                    "@type": "Question",
                    "name": entry.get('question', ''),
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": entry.get('answer', '')
                    }
                })
        
        if faq_items:
            faq_schema_dict = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": faq_items
            }
            faq_schema = f"""
                        <script type="application/ld+json">
                        {json.dumps(faq_schema_dict, indent=2)}
                        </script>
                    """
    
    faq_html = render_faq_section(faq_entries)
    
    # Article schema for SEO
    article_schema_dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"{title} — {place_name}",
        "description": meta_description or f"Guide to {title} in {place_name}",
        "image": cover_image_url or "",
        "author": {
            "@type": "Organization",
            "name": "Foreign Travel Steps",
            "url": "https://foreigntravelsteps.com"
        },
        "datePublished": schema_date,
        "dateModified": schema_date,
        "url": canonical_url
    }
    article_schema = f"""
                        <script type="application/ld+json">
                        {json.dumps(article_schema_dict, indent=2)}
                        </script>
                    """
    
    # Full SEO HTML Page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} — {escape(place_name)}</title>
    <meta name="description" content="{escape(meta_description or f'Guide to {title} in {place_name}')}">
    <meta name="keywords" content="{escape(searchable_keywords or f'{title}, {place_name}')}">
    <link rel="canonical" href="{escape(canonical_url)}">
    
    <meta property="og:title" content="{escape(title)}">
    <meta property="og:description" content="{escape(meta_description or f'Guide to {title} in {place_name}')}">
    <meta property="og:image" content="{escape(cover_image_url or '')}">
    <meta property="og:url" content="{escape(canonical_url)}">
    <meta property="og:type" content="article">
    
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{escape(title)}">
    <meta name="twitter:description" content="{escape(meta_description or f'Guide to {title} in {place_name}')}">
    <meta name="twitter:image" content="{escape(cover_image_url or '')}">
    
    {article_schema}
    {faq_schema}
</head>
<body>
    <article>
        <header>
            <h1>{escape(title)}</h1>
            <time datetime="{published_iso}">{published_display}</time>
        </header>
        
        <div class="blog-cover">
            <img src="{escape(cover_image_url or '')}" alt="{escape(title)}" loading="lazy">
        </div>
        
        <div class="blog-body">
            {editable_body_text}
        </div>
        
        {faq_html}
    </article>
    
    <footer>
        <p>Last updated: <time datetime="{modified_iso}">{modified_display}</time></p>
    </footer>
</body>
</html>
"""
    
    # Write to file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return file_path
    except Exception as e:
        raise Exception(f"Failed to write blog file: {str(e)}")


@login_required
def blog_form_view(request):
    """Display the blog creation form"""
    places = Places_v2.objects.all().values_list('placename', flat=True).distinct()
    
    context = {
        'places': places
    }
    
    return render(request, 'singlepage2/blog_form.html', context)


@login_required
def create_blog_view(request):
    """Handle blog form submission and create blog post"""
    if request.method != 'POST':
        return redirect('singlepage2:blog_form')
    
    try:
        # Get form data
        place_name = request.POST.get('place_name', '').strip()
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'Guide')
        summary = request.POST.get('summary', '').strip()
        textContent = request.POST.get('textContent', '').strip()
        cover_image_url = request.POST.get('cover_image_url', '').strip()
        meta_description = request.POST.get('meta_description', '').strip()
        searchable_keywords = request.POST.get('searchable_keywords', '').strip()
        seo_title = request.POST.get('seo_title', '').strip()
        longitude = request.POST.get('longitude', '').strip()
        latitude = request.POST.get('latitude', '').strip()
        readtime = request.POST.get('readtime', '5')
        faq_json_data = request.POST.get('faq_json_data', '[]')
        
        # Validate required fields
        if not place_name or not title:
            messages.error(request, 'Place name and title are required.')
            return redirect('singlepage2:blog_form')
        
        # Parse FAQ data
        try:
            faq_entries = json.loads(faq_json_data) if faq_json_data else []
        except json.JSONDecodeError:
            faq_entries = []
        
        # Create blog object
        blog_obj = generate_blog_object(
            place_name=place_name,
            title=title,
            category=category,
            summary=summary,
            text_content=textContent,
            cover_image_url=cover_image_url,
            meta_description=meta_description,
            searchable_keywords=searchable_keywords,
            seo_title=seo_title,
            longitude=longitude,
            latitude=latitude,
            faq_entries=faq_entries
        )
        
        # Generate blog page
        generate_blog_page(
            request,
            place_name=place_name,
            title=title,
            body_text=textContent,
            cover_image_url=cover_image_url,
            faq_entries=faq_entries,
            meta_description=meta_description,
            category=category,
            searchable_keywords=searchable_keywords
        )
        
        messages.success(request, f'✅ Blog post "{title}" created successfully!')
        return redirect('singlepage2:blog_form')
    
    except ValueError as ve:
        messages.error(request, f'❌ {str(ve)}')
        return redirect('singlepage2:blog_form')
    
    except Exception as e:
        messages.error(request, f'❌ An error occurred: {str(e)}')
        return redirect('singlepage2:blog_form')


def get_places_json(request):
    """API endpoint to get places for autocomplete"""
    places = list(Places_v2.objects.all().values_list('placename', flat=True).distinct())
    return JsonResponse({'places': places})

from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils import timezone
import os
from django.utils.text import slugify
from django.conf import settings
import json
from garden.models import Collection, CollectionGroup
from openai import OpenAI
import ast
from home.models import Places_v2
from apis.models import Blogs
from singlepage2.pyhtmlopt import optimize_file
import re
from html import escape
from bs4 import BeautifulSoup
client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
BLOG_CATEGORY_VALUES = {choice[0] for choice in Blogs.category_choices}
DEFAULT_SUMMARY_VALUES = {"", "No Summary Provided", "Discover more about this destination"}
FAQ_QUESTIONS_BY_CATEGORY = {
    "Guide": [
        "What is the best time to visit?",
        "How much is the entrance fee or total cost?",
        "How do I get there?",
        "What should I bring for the trip?",
        "Is it safe to visit and what travel tips should I know?",
    ],
    "Story": [
        "What is the main story or experience about?",
        "What can readers learn from this experience?",
        "Who is this story most useful for?",
        "What local details or moments should readers notice?",
        "How can readers plan a similar experience?",
    ],
    "Tip and Trick": [
        "What are the most important tips to know first?",
        "What common mistakes should readers avoid?",
        "How can readers save time, money, or effort?",
        "What should readers prepare before they start?",
        "What is the safest or smartest way to do this?",
    ],
    "Explore": [
        "What are the best things to do nearby?",
        "How much time should visitors plan for this experience?",
        "What places, activities, or stops should be prioritized?",
        "How do visitors get there or move around locally?",
        "What should visitors check before going?",
    ],
    "Product": [
        "What is the best product to buy in 2026?",
        "Where is the best place to buy it?",
        "How much does it currently cost?",
        "What are the top alternatives or competitors?",
        "Is it worth buying in 2026?",
    ],
}


def clean_blog_metadata(value):
    value = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', str(value or ''), flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def normalize_blog_category(category):
    category = clean_blog_metadata(category).strip("'\"")
    return category if category in BLOG_CATEGORY_VALUES else 'Guide'


def mark_editable_blog_body(body_html):
    soup = BeautifulSoup(body_html or "", "html.parser")
    for idx, editable_block in enumerate(soup.find_all(["h2", "p"])):
        editable_block["data-blog-edit-index"] = str(idx)
        editable_block["data-blog-edit-tag"] = editable_block.name
    return str(soup)


def format_blog_datetime(value):
    value = value or timezone.now()
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    display = value.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")
    return value.isoformat(), display


def render_faq_section(faq_entries):
    rows = []
    for entry in faq_entries or []:
        if not isinstance(entry, dict):
            continue

        question = (entry.get("name") or "").strip()
        accepted_answer = entry.get("acceptedAnswer") or {}
        if isinstance(accepted_answer, dict):
            answer = (accepted_answer.get("text") or "").strip()
        else:
            answer = str(accepted_answer).strip()

        if not question or not answer:
            continue

        rows.append(f"""
        <details class="faq-item">
            <summary>{escape(question)}</summary>
            <p>{escape(answer)}</p>
        </details>
        """)

    if not rows:
        return ""

    return f"""
    <section class="faq-section" aria-labelledby="faq-heading">
        <h2 id="faq-heading">Frequently Asked Questions</h2>
        <div class="faq-list">
            {''.join(rows)}
        </div>
    </section>
    """

# USES call htmlwriter then calls generate_blog_object to save the blog in the database, then generates the html page with SEO optimizations, FAQ schema, and article schema for better search engine visibility. The generated HTML is saved in the appropriate folder structure for serving as a static page on the site.
def generate_blog_object(request, place_name, title, category='Guide', summary='No Summary Provided', text_content=''):
    place = Places_v2.objects.filter(placename__iexact=place_name).first()    
    category = normalize_blog_category(category)
    summary = clean_blog_metadata(summary)[:400] or 'No Summary Provided'
    title_slug = slugify(title)
    plain_text_content = re.sub('<[^<]+?>', '', text_content or '')
    readtime = max(1, len(plain_text_content.split()) // 185) if plain_text_content else 5

    place_blog_list = list(place.blog.all())
    for b in place_blog_list:
        if slugify(getattr(b, 'title', '') or '') == title_slug:
            update_fields = []
            existing_category = getattr(b, 'category', '') or ''
            if category != existing_category and (category != 'Guide' or existing_category in ('', 'Guide')):
                b.category = category
                update_fields.append('category')

            existing_summary = clean_blog_metadata(getattr(b, 'summarize', '') or '')
            if summary not in DEFAULT_SUMMARY_VALUES and summary != existing_summary:
                b.summarize = summary
                update_fields.append('summarize')

            if update_fields:
                b.save(update_fields=update_fields)

            return b    
    title = re.sub(r'<a\b[^>]*>(.*?)</a>',r'\1',title,flags=re.IGNORECASE | re.DOTALL)            
    blog_item = Blogs.objects.create(
        category=category,
        blogplace=place,
        title=title,
        textContent=plain_text_content,
        summarize=summary,
        readtime=readtime,
    )
    generate_blog_page(request, place_name, title, text_content, category=category)
    place.blog.add(blog_item)

def generate_blog_page(request, place_name, title, body_text, cover_image_url=None, faq_entries=None, blog_searchable_keys_description=None, category=None):
    category = normalize_blog_category(category)
    def _get_image_cover(place_name, title):
        from imageapp.imageuploader import getTitlePhoto
        togen = f"{title} {place_name} travel guide cover photo, vibrant and eye-catching, showcasing the essence of the destination with iconic landmarks or scenic views, optimized for web display."
        image_url = getTitlePhoto(request, togen)
        return image_url
        

    def _strip_html_tags(html: str) -> str:
        return re.sub('<[^<]+?>', '', html or '')
    def create_blog_searchable_keys_description(title, place_name, category):
        try:
            meta_prompt = f'''Create an SEO-friendly meta description for a {category} blog titled "{title}" in "{place_name}". 
                            with like these keywords: {title}, {place_name}, {category}, things to do, entrance fee, tips, festivals and best time to visit.
                            Keep it under 160 characters and make it enticing for travelers searching online.'''
            meta_res = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": meta_prompt}],
                max_tokens=200
            )
            _blog_searchable = meta_res.choices[0].message.content.strip().strip('"')
            return _blog_searchable
        except Exception:
            _blog_searchable = f"Things to do {title} in {place_name}: Complete travel guide with directions, top activities, entrance fees, insider tips, and best times to visit for an unforgettable experience."
        
        return _blog_searchable
    
    # if cover_image_url is None:
    #     return _get_image_cover(place_name, title)
    if blog_searchable_keys_description is None:
        create_blog_searchable_keys_description = create_blog_searchable_keys_description(title, place_name, category)
    title = (title or '').strip() or f"{category} to {place_name}"
    text_content = _strip_html_tags(body_text)

    """Generate optimized blog HTML page with SEO and performance enhancements."""
    # Print FAQ entries and searchable keys with 0.5s delays
    # blog_obj = generate_blog_object(request, place_name, title, category=category, summary=blog_searchable_keys_description or "", text_content=body_text)

    
    csrf_token = ""
    if request is not None:
        try:
            csrf_token = get_token(request)
        except Exception:
            pass
    upload_url = reverse("imageapp:uploadimage")
    subscribe_url = reverse("apis:subscribe_email")
    blog_edit_save_url = reverse("singlepage2:save_blog_paragraph_file_edit")
# def generate_blog_page(place_name, title, body_text, cover_image_url="/static/images/default-cover.jpg", faq_list=None):

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
        raise

    # The final HTML file location
    file_path = os.path.join(folder_path, f"{title_slug}.html")

    # The canonical full URL on your live site
    canonical_url = f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"
    editable_body_text = mark_editable_blog_body(body_text)
    generated_at = timezone.now()
    published_iso, published_display = format_blog_datetime(generated_at)
    modified_iso, modified_display = format_blog_datetime(generated_at)
    schema_date = timezone.localtime(generated_at).date().isoformat()

    collections_html = f'''
                        <div id="collections-header">
                            <h2>📱 Local Collections & QR Experiences</h2>
                            <p id="collections-loading">Things to do interactive collections nearby. Scan QR codes for memories! Loading...</p>
                            <div id="dynamic-collections" class="collection-section">
                            </div>
                        </div>
                        '''

    # Build FAQ Schema and Article Schema
    try:
        faq_entries = []
        faq_questions = FAQ_QUESTIONS_BY_CATEGORY.get(category, FAQ_QUESTIONS_BY_CATEGORY["Guide"])

        faq_prompt = f'''Generate 5 most searched words and FAQs about "{title}" in "{place_name}".
        
                        Return ONLY a valid JSON array with no markdown formatting. Format:
                        [
                        {{"@type": "Question", "@id": "{canonical_url}#[question name]", "name": "Question?", "acceptedAnswer": {{"@type": "Answer", "text": "Answer text."}}}},
                        ... 
                        ]
                        Use the page URL "{canonical_url}" in all "@id" fields (question name1, question name2, question name3, etc.)
                        Questions should cover: {faq_questions}
                        Keep answers concise (1-2 sentences).'''
        res = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[{"role": "user", "content": faq_prompt}],
            max_tokens=1000
        )
        faq_text = res.choices[0].message.content.strip()
    
        # Try to parse as JSON
        faq_entries = ast.literal_eval(faq_text) if faq_text.startswith('[') else []
        
        # Post-process: ensure all @id fields use the canonical URL
        for entry in faq_entries:
            if isinstance(entry, dict):
                entry["@id"] = f"{canonical_url}#{slugify(entry['name'])}"
        
    except Exception:
        faq_entries = []
    
    faq_schema = ""
    if faq_entries:
                faq_schema = f"""
                    <script type="application/ld+json">
                    {json.dumps({
                        "@context": "https://schema.org",
                        "@type": "FAQPage",
                        "mainEntity": faq_entries
                    }, indent=2)}
                    </script>
                """
    faq_html = render_faq_section(faq_entries)
    
    # Article schema for SEO
    article_schema_dict = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": f"{title} — {place_name}",
            "description": blog_searchable_keys_description or f"How {title} in {place_name}",
            "image": cover_image_url,
            "author": {
                "@type": "Organization",
                "name": "Foreign Travel Steps",
                "url": "https://foreigntravelsteps.com"
            },
            "datePublished": schema_date,
            "dateModified": schema_date,
            "url": f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"
        }
    article_schema = f"""
                        <script type="application/ld+json">
                        {json.dumps(article_schema_dict, indent=2)}
                        </script>
                    """
        



    # Full SEO HTML Page
    html_content = f"""
    <!DOCTYPE html>
        <html lang="en">
        <head>
                                            {faq_schema}
                                            {article_schema}
                                            <!-- Performance: DNS prefetch and preconnect -->
                                            <link rel="dns-prefetch" href="//www.googletagmanager.com">
                                            <link rel="dns-prefetch" href="//pagead2.googlesyndication.com">
                                            <!-- Google tag (gtag.js) -->
                                            <script> window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}} gtag('js', new Date()); gtag('config', 'G-BR63L5YLJD'); </script>
                                            <meta name="google-site-verification" content="8jqO-yxHVkp0mIbnh_nvbfA0N21q0QcCR4aDkFbb8rc" />
                                            <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4843007524416588" crossorigin="anonymous"></script>
                                            <meta name="google-adsense-account" content="ca-pub-4843007524416588">

                                            <!-- Google Tag Manager -->
                                            <script>
                                            (function(w,d,s,l,i){{ 
                                                w[l] = w[l] || []; 
                                                w[l].push({{ 'gtm.start': new Date().getTime(), event: 'gtm.js' }}); 
                                                var f = d.getElementsByTagName(s)[0],
                                                    j = d.createElement(s),
                                                    dl = l != 'dataLayer' ? '&l=' + l : ''; 
                                                j.async = true; 
                                                j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl; 
                                                f.parentNode.insertBefore(j, f); 
                                            }})(window, document, 'script', 'dataLayer', 'GTM-MNDNQVRF');
                                            </script>
                                            <!-- End Google Tag Manager -->
                                                <meta charset="UTF-8">

                                                <title>{title} — {place_name} Travel Guide</title>

                                                <meta name="description" content="{blog_searchable_keys_description if blog_searchable_keys_description else f'{title} in {place_name}. Learn how to visit, travel tips, prices, and the best time to explore.'}">

                                                <!-- Canonical -->
                                                <link rel="canonical" href="{canonical_url}">

                                                <!-- Open Graph -->
                                                <meta property="og:title" content="{title} — {place_name}">
                                                <meta property="og:description" content="{blog_searchable_keys_description if blog_searchable_keys_description else f'Things to {title} in {place_name}: Complete travel guide with directions, top activities, entrance fees, insider tips, and best times to visit for an unforgettable experience.'}">
                                                <meta property="og:type" content="article">
                                                <meta property="og:url" content="{canonical_url}">
                                                <meta property="og:image" content="{cover_image_url}">

                                                <!-- Twitter -->
                                                <meta name="twitter:card" content="summary_large_image">
                                                <meta name="twitter:title" content="{title} — {place_name}">
                                                <meta name="twitter:description" content="A helpful travel guide for {place_name}.">
                                                <meta name="twitter:image" content="{cover_image_url}">

                                                <!-- Mobile Responsive -->
                                                <meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,500;0,9..144,700;1,9..144,300;1,9..144,400;1,9..144,500&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@272&display=swap');
:root {{
    --surface: #fffaf2;
    --surface-alt: #edf7f2;
    --page-bg: #f7f5ec;
    --accent: #2f7d68;
    --accent-dark: #17584b;
    --accent-light: #d97a45;
    --accent-blue: #2f6fb3;
    --text: #27332f;
    --text-muted: #65736d;
    --border: #d8ded7;
    --white: #ffffff;
}}

* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}

body {{
    min-height: 100vh;

    font-family: "Source Sans 3", Arial, sans-serif;
    font-size: 17px;
    line-height: 1.7;
    color: var(--text);
    background: linear-gradient(to bottom right, rgb(242, 242, 242), rgb(224, 224, 224) 52%, rgb(216, 216, 216));
}}

.white-color{{
    color: wheat;
}}
h2,
h3 {{
    line-height: 1.25;
    color: var(--text);
}}

h1 {{
    font-size: clamp(2rem, 4vw, 2.75rem);
    font-weight: 700;
    margin-bottom: 1rem;
      font-family: "Fraunces",Georgia,serif;
  font-style: italic;
  font-weight: 300;
  font-size: clamp(36px,5vw,72px);
  line-height: 1;
  letter-spacing: 0.02em;
  max-width: 14ch;
}}

h2 {{
    font-size: clamp(1.45rem, 3vw, 1.9rem);
    font-weight: 700;
    color: var(--accent-dark);
    margin: 2.25rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);

    font-family: "Roboto Mono", monospace;
  font-optical-sizing: auto;
  font-weight: 272;
  font-style: normal;
}}

h3 {{
    font-size: clamp(1.12rem, 2vw, 1.32rem);
    font-weight: 650;
    color: var(--accent);
    margin: 1.5rem 0 0.75rem;
}}

p {{
    margin-bottom: 1.1rem;
    font-size: clamp(1.05rem, 2.5vw, 1.25rem);
}}

li {{
    margin-bottom: 0.55rem;
}}

a {{
    color: var(--accent-blue);
}}

strong {{
    font-weight: 650;
}}

img {{
    width: 100%;
    height: auto;
    margin: 1.4rem 0;
}}

#blog-editable-body img,
#blog-editable-body .editable-blog-image {{
    display: block;
    width: min(100%, 860px);
    max-width: 100%;
    height: auto;
    margin: 1.35rem auto;
}}

#blog-editable-body [data-editing="true"] img {{
    cursor: default;
}}

.navbar {{
    position: sticky;
    top: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 1.25rem;
    background: #ffffff;
    border-bottom: 1px solid var(--border);
}}

.navbar-brand-row {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.logo {{
    font-size: 1.2rem;
    font-weight: 800;
    color: var(--accent-dark);
}}

.hamburger {{
    display: block;
    width: 32px;
    height: 30px;
    padding: 6px;
    cursor: pointer;
}}

.hamburger span {{
    display: block;
    width: 100%;
    height: 3px;
    margin-top: 4px;
    border-radius: 3px;
    background: cadetblue;
}}

.hamburger span:first-child {{
    margin-top: 0;
}}

.hamburger.open span:nth-child(2) {{
    opacity: 0.35;
}}

.nav-links {{
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    display: none;
    overflow-y: auto;
    max-height: 70vh;
    background: #ffffff;
    border-bottom: 1px solid var(--border);
}}

.nav-links.open {{
    display: block;
}}

.nav-links a {{
    text-decoration: none;
}}

.dropdown {{
    position: relative;
}}

.dropdown-menu {{
    display: none;
    width: 100%;
    list-style: none;
    background: #ffffff;
}}

.dropdown.open .dropdown-menu {{
    display: block;
}}

#blog-list {{
    width: 100%;
    max-width: 920px;
    max-height: 70vh;
    margin: 0 auto;
    overflow-y: auto;
    list-style: none;
    background: #ffffff;
}}

#blog-list li {{
    margin: 0;
    padding: 0.35rem 1rem;
    border-bottom: 1px solid #edf0ee;
}}

#blog-list a {{
    display: block;
    padding: 0.55rem 0;
    color: var(--text-muted);
    font-size: 0.9rem;
}}

#blog-list a:hover {{
    color: var(--accent-dark);
}}

#body-contents {{
    margin: 1.5rem auto 0;
    border-bottom: 0;
}}

.blog-date-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1rem;
    margin: 0 0 1.5rem;
    padding-bottom: 0.9rem;
    color: var(--text-muted);
    font-size: 0.92rem;
    border-bottom: 1px solid var(--border);
}}

.blog-date-meta time {{
    color: var(--text);
    font-weight: 650;
}}

.intro-section,
.cta-section {{
    padding: clamp(1.5rem, 4vw, 2.5rem);
    margin: 2rem 0;
    background: linear-gradient(135deg, var(--accent-dark), var(--accent-blue));

}}

.intro-section h2,
.cta-section h2 {{
    color: var(--white);
    border: 0;
    margin-top: 0;
}}

.cta-section h1 {{
    color: var(--white);
    border: 0;
    margin-top: 0;
}}
.intro-section p,
.cta-section p {{
    color: rgba(241, 241, 241, 0.92);
    font-size: clamp(1.05rem, 2.5vw, 1.25rem);
}}

.content-section {{
    margin-bottom: 2.5rem;
}}

.highlight-box,
.tip-box,
.mindset-box {{
    padding: 1.5rem;



    border-left: 5px solid var(--accent);

}}

.tip-box {{
    border-left-color: var(--accent-light);
}}

.mindset-box {{
    background: var(--surface);
}}

.collection-section,
#dynamic-collections {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}}

.collection-item,
.collection-section .collection-card {{
    padding: 1rem;
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 10px;
}}

.collection-item img,
.collection-section .collection-card img {{
    height: 180px;
    object-fit: cover;
    margin: 0 0 0.85rem;
}}

.collection-item h4,
.collection-section .collection-card h4 {{
    color: var(--accent-dark);
    font-weight: 650;
}}

.collection-link,
.collection-section .collection-link {{
    display: inline-block;
    padding: 0.7rem 1rem;
    color: #ffffff;
    text-decoration: none;
    font-weight: 650;
    background: var(--accent);
    border-radius: 8px;
}}

.directions-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    margin-top: 0.5rem;
    color: var(--accent-blue);
    font-weight: 700;
}}

.tour-guide-card {{
    max-width: 920px;
    margin: 0 auto;
    text-align: left;
}}

.tour-guide-card input {{
    width: 100%;
    margin-top: 0.75rem;
    padding: 0.8rem 0.95rem;
    color: #ffffff;
    font: inherit;
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.12);
}}

footer {{
    padding: clamp(2rem, 5vw, 3.5rem) 1.25rem;
    color: var(--white);
    text-align: center;
    background: linear-gradient(135deg, #17584b, #202c3d);
}}

footer h1 {{
    max-width: 860px;
    margin: 1.5rem auto 0.75rem;
    color: var(--white);
    font-size: clamp(1.4rem, 3vw, 1.9rem);
}}

footer p {{
    max-width: 820px;
    margin-left: auto;
    margin-right: auto;
    color: rgba(255, 255, 255, 0.9);
}}

footer a {{
    color: #ffffff;
}}

#subscribeForm,
#imageform {{
    max-width: 760px;
    margin: 0 auto 1.5rem;
    padding: 1rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 12px;
}}

#imageform {{
    margin-top: 2rem;
    justify-content: center;
}}

#subscribeForm input[type="email"],
#subscribeForm input[type="text"],
#imageform input[type="file"] {{
    flex: 1 1 220px;
    min-height: 44px;
    padding: 0.75rem 0.9rem;
    color: var(--text);
    font: inherit;
    border: 1px solid #d9dfdc;
    border-radius: 8px;
    background: #ffffff;
}}

#subscribeForm input:focus,
#imageform input[type="file"]:focus {{
    border-color: var(--accent-light);
    outline: 2px solid rgba(217, 122, 69, 0.28);
    outline-offset: 1px;
}}

#subscribeForm button,
#imageform button,
footer button {{
    min-height: 44px;
    padding: 0.75rem 1.2rem;
    color: #ffffff;
    font: inherit;
    font-weight: 700;
    border: 0;
    border-radius: 8px;
    background: var(--accent-light);
    cursor: pointer;
}}

#blog-editable-body [data-blog-edit-index] {{
    position: relative;
    padding: 1rem;
    font-weight:300;
    word-spacing:0.1rem
}}

#blog-editable-body [data-editing="true"] {{
    padding: 0.75rem 1rem;
    background: #f7f7f7;
    border: 1px solid #cbd5e1;
    border-radius: 8px;

    outline: none;

    transition:
        background-color 0.15s ease,
        border-color 0.15s ease,
        box-shadow 0.15s ease;

    box-shadow:
        0 1px 2px rgba(0,0,0,0.04),
        0 0 0 3px rgba(37, 99, 235, 0.12);
}}

.blog-edit-button {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    margin-left: 0.45rem;
    font: inherit;
    font-size: 0.9rem;

    border: none;


    cursor: pointer;
    vertical-align: middle;
    color: rgba(0, 0, 0, 0.63);
    background: rgba(97, 76, 76, 0);
}}

.blog-edit-button:hover {{
    color: #ffffff;
    background: var(--accent);
    border-color: var(--accent);
}}

.blog-paragraph-tools {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: -0.55rem 0 1.1rem;
}}

.blog-paragraph-tools button {{
    min-height: 36px;
    padding: 0.45rem 0.85rem;
    font: inherit;
    font-weight: 700;
    border-radius: 8px;
    cursor: pointer;
}}

.blog-save-button {{
    color: #ffffff;
    border: 0;
    background: rebeccapurple;
}}

.blog-cancel-button {{
    color: var(--text);
    border: 1px solid var(--border);
    background: #ffffff;
}}

.blog-image-upload-button {{
    color: var(--accent-dark);
    border: 1px solid rgba(47, 125, 104, 0.35);
    background: #edf7f2;
}}

.blog-url-button {{
    color: #1d4ed8;
    border: 1px solid rgba(37, 99, 235, 0.35);
    background: #eff6ff;
}}

.blog-url-input {{
    flex: 1 1 260px;
    min-height: 36px;
    min-width: 220px;
    padding: 0.45rem 0.7rem;
    color: var(--text);
    font: inherit;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #ffffff;
}}

.blog-url-input:focus {{
    border-color: #2563eb;
    outline: 2px solid rgba(37, 99, 235, 0.18);
    outline-offset: 1px;
}}

.blog-image-name-input {{
    flex: 1 1 220px;
    min-height: 36px;
    min-width: 200px;
    padding: 0.45rem 0.7rem;
    color: var(--text);
    font: inherit;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #ffffff;
}}

.blog-image-name-input:focus {{
    border-color: rgba(47, 125, 104, 0.72);
    outline: 2px solid rgba(47, 125, 104, 0.18);
    outline-offset: 1px;
}}

.blog-image-upload-button:disabled {{
    cursor: wait;
    opacity: 0.7;
}}

.blog-image-upload-input {{
    display: none;
}}

.blog-edit-status {{
    color: var(--text-muted);
    font-size: 0.9rem;
}}

.blog-edit-status.error {{
    color: #b42318;
}}

.faq-section {{
    margin: 2.75rem 0 0;
}}

.faq-list {{
    display: grid;
    gap: 0.75rem;
}}

.faq-item {{
    border: 1px solid var(--border);
}}

.faq-item summary {{
    padding: 0.95rem 1rem;
    color: var(--accent-dark);
    cursor: pointer;
}}

.faq-item p {{
    margin: 0;
    padding: 0 1rem 1rem;
    color: var(--text-muted);
}}

@media (max-width: 768px) {{
    .blog-save-button {{
    width: 100%;
}}
.blog-paragraph-tools button {{
border-radius: 0;
}}
    body {{
        font-size: 15.5px;
    }}

    #body-contents {{
        margin-top: 0;

        border-left: 0;
        border-right: 0;
    }}

    .navbar {{
        padding: 0.8rem 1rem;
    }}

    #subscribeForm button,
    #imageform button {{
        width: 100%;
    }}
}}
</style>

    
</head>
<body>
                                                                        <!-- Google Tag Manager (noscript) -->
                                                                        <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-MNDNQVRF"
                                                                        height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
                                                                        <!-- End Google Tag Manager (noscript) -->



<nav class="navbar">
    <div class="navbar-brand-row">
         <div class="hamburger" id="hamburgerBtn" onclick="toggleMenu()">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="logo">ParaTara</div>
    </div>

    <div class="nav-links" id="navLinks">
        <ul class="" id="blog-list">
        </ul>
    </div>
</nav>                                                                
<script>
function toggleMenu() {{
    const navLinks = document.getElementById('navLinks');
    const hamburger = document.getElementById('hamburgerBtn');
    navLinks.classList.toggle('open');
    if (hamburger) {{
        hamburger.classList.toggle('open');
    }}
}}

function toggleDropdown(e) {{
    e.preventDefault();
    const dropdown = e.target.closest('#dropdowntoogle');
    if (!dropdown) return;
    dropdown.classList.toggle('open');
}}
</script>


  <article id="body-contents">
    {collections_html}
    <p class="blog-date-meta">
        <span>Published <time id="blog-published-at" datetime="{published_iso}">{published_display}</time></span>
        <span>Last updated <time id="blog-last-updated" datetime="{modified_iso}">{modified_display}</time></span>
    </p>
    <div id="blog-editable-body" data-place-slug="{place_slug}" data-title-slug="{title_slug}">
    {editable_body_text}
    </div>
    {faq_html}
  </article>
  


 

<script>

var place_name = "{place_name}";
var placename = "{place_name}";
var blogPlaceSlug = "{place_slug}";
var blogTitleSlug = "{title_slug}";
var blogParagraphSaveUrl = "{blog_edit_save_url}";
var blogImageUploadUrl = "{upload_url}";

// Fisher-Yates shuffle algorithm for proper randomization
function shuffleArray(array) {{
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {{
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }}
    return shuffled;
}}

async function fetchAndInsertImages() {{
    try {{
        // Fetch images from Django
        const response = await fetch(`/imageapp/images/${{placename}}/`);
        const data = await response.json();

        const images = data.images.map(img => img.imbbURL); // array of URLs

        // Shuffle array to pick random images using Fisher-Yates
        const shuffled = shuffleArray(images);

        // Find all possible insertion points: content-sections, after h2/h3, after paragraphs
        const bodyContents = document.querySelector("#body-contents");
        if (!bodyContents) return;

        // Get all content sections and other potential insertion points
        const contentSections = Array.from(bodyContents.querySelectorAll('.content-section, .intro-section'));
        
        // If no sections found, fall back to direct body-contents
        const insertionPoints = contentSections.length > 0 ? contentSections : [bodyContents];
        
        let count = 0;
        const maxImages = 3;

        shuffled.slice(0, maxImages).forEach((imgUrl, index) => {{
            if (count >= maxImages) return;
            count++;

            const img = document.createElement("img");
            img.src = imgUrl;
            img.loading = "lazy";
            img.alt = "Blog content image";
            img.className = "dynamic-blog-image";

            // Pick a random section to insert into
            const randomSection = insertionPoints[Math.floor(Math.random() * insertionPoints.length)];
            
            // Find all child elements within the section
            const children = Array.from(randomSection.children);
            
            if (children.length > 0) {{
                // Insert after a random child element
                const randomIndex = Math.floor(Math.random() * children.length);
                const targetElement = children[randomIndex];
                targetElement.insertAdjacentElement('afterend', img);
            }} else {{
                // If no children, append to the section
                randomSection.appendChild(img);
            }}
        }});

    }} catch (err) {{
        console.error("Error fetching images:", err);
    }}
}}












// Consolidated fetch function with error handling
async function fetchData(endpoint, elementId, templateFn, errorMsg, onEmpty) {{
    const csrftoken = getCookie('csrftoken');
    try {{
        const response = await fetch(`/apis/${{endpoint}}/`, {{
            method: 'GET',
            headers: {{
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrftoken,
            }}
        }});
        
        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const data = await response.json();
        
        if (!data || !data.length) {{
            if (typeof onEmpty === 'function') {{
                onEmpty();
                return;
            }}
            const element = document.getElementById(elementId);
            if (element) element.textContent = errorMsg;
            return;
        }}
        
        templateFn(data);
    }} catch (err) {{
        console.error(`Error fetching ${{endpoint}}:`, err);
        const element = document.getElementById(elementId);
        if (element) element.textContent = `Failed to load ${{endpoint}}`;
    }}
}}

    function getBlogLists() {{
        fetchData('getPlaceBlogs/' + placename, 'blog-list', (data) => {{
            const blogList = document.getElementById('blog-list');
            const fragment = document.createDocumentFragment();
            
            data.forEach(blog => {{
                const item = document.createElement('li');
                const link = document.createElement('a');
                link.href = blog.localurlpath;
                link.textContent = blog.title.replace(/<\\/?a[^>]*>/g, '');
                item.appendChild(link);
                fragment.appendChild(item);
            }});
            
            blogList.appendChild(fragment);
        }}, 'No blogs found for this place.');
    }}

    function fetchCollections() {{
        fetchData(
            'getPlaceCollections/' + placename,
            'collections-loading',
            (data) => {{
                const collectionsDiv = document.querySelector('#dynamic-collections');
                const fragment = document.createDocumentFragment();

                data.forEach(col => {{
                    const div = document.createElement('div');
                    div.className = 'collection-item';
                    
                    if (col.collectionPicture) {{
                        const img = document.createElement('img');
                        img.src = col.collectionPicture;
                        img.alt = col.collectionName || 'Collection image';
                        img.loading = 'lazy';
                        div.appendChild(img);
                    }}
                    
                    const h4 = document.createElement('h4');
                    h4.textContent = col.name || '';
                    div.appendChild(h4);
                    
                    if (col.address || col.collectionDescription) {{
                        const p = document.createElement('p');
                        p.textContent = (col.collectionDescription || '').substring(0, 130) + '...';
                        div.appendChild(p);
                    }}

                    // Add Directions link with icon
                    const address = col.address || col.name || '';
                    if (address) {{
                        const directionsLink = document.createElement('a');
                        directionsLink.href = `https://www.google.com/maps/search/?api=1&query=${{encodeURIComponent(address)}}`;
                        directionsLink.target = '_blank';
                        directionsLink.rel = 'noopener noreferrer';
                        directionsLink.className = 'directions-link';

                        // SVG icon for directions (Google Maps style)
                        const svgIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                        svgIcon.setAttribute('width', '20');
                        svgIcon.setAttribute('height', '20');
                        svgIcon.setAttribute('viewBox', '0 0 24 24');
                        svgIcon.setAttribute('fill', 'none');
                        svgIcon.setAttribute('stroke', '#2563eb');
                        svgIcon.setAttribute('stroke-width', '2');
                        svgIcon.setAttribute('stroke-linecap', 'round');
                        svgIcon.setAttribute('stroke-linejoin', 'round');
                        svgIcon.innerHTML = `<path d="M21.71 11.29l-9-9a1 1 0 0 0-1.42 0l-9 9a1 1 0 0 0 0 1.42l9 9a1 1 0 0 0 1.42 0l9-9a1 1 0 0 0 0-1.42z"/><circle cx="12" cy="12" r="3"/>`;

                        directionsLink.appendChild(svgIcon);
                        const span = document.createElement('span');
                        span.textContent = 'Directions';
                        directionsLink.appendChild(span);
                        div.appendChild(directionsLink);
                    }}

                    fragment.appendChild(div);
                }});

                collectionsDiv.appendChild(fragment);
                document.getElementById('collections-loading').style.display = 'none';
            }}, 'No local collections found nearby.', () => {{
                const collectionsHeader = document.querySelector('#collections-header');
                if (collectionsHeader) {{
                    collectionsHeader.style.display = 'none';
                }}
                const loading = document.getElementById('collections-loading');
                if (loading) {{
                    loading.style.display = 'none';
                }}
            }});
    }}

    function getParagraphCleanText(paragraph) {{
        const clone = paragraph.cloneNode(true);
        clone.querySelectorAll('.blog-edit-button, .blog-paragraph-tools').forEach(el => el.remove());
        return clone.textContent.trim();
    }}

    function getParagraphCleanHTML(paragraph) {{
        const clone = paragraph.cloneNode(true);
        clone.querySelectorAll('.blog-edit-button, .blog-paragraph-tools').forEach(el => el.remove());
        return clone.innerHTML;
    }}

    function paragraphHasVisibleContent(paragraph) {{
        const clone = paragraph.cloneNode(true);
        clone.querySelectorAll('.blog-edit-button, .blog-paragraph-tools').forEach(el => el.remove());
        return Boolean(clone.textContent.trim() || clone.querySelector('img[src]'));
    }}

	    function insertUploadedImageIntoSection(paragraph, imageUrl) {{
	        if (!imageUrl) return;

	        function getImageAltFromUrl(rawUrl) {{
	            if (!rawUrl || typeof rawUrl !== 'string') return '';
	            try {{
	                const parsed = new URL(rawUrl, window.location.href);
	                const baseName = (parsed.pathname || '').split('/').filter(Boolean).pop() || '';
	                return decodeURIComponent(baseName);
	            }} catch {{}}
	            const withoutQuery = rawUrl.split('#')[0].split('?')[0];
	            const baseName = withoutQuery.split('/').filter(Boolean).pop() || '';
	            try {{
	                return decodeURIComponent(baseName);
	            }} catch {{
	                return baseName;
	            }}
	        }}

	        const isUrlOrFilePath = (() => {{
	            // Check for valid URL
	            try {{
	                new URL(imageUrl);
	                return true;
            }} catch {{}}
            // Check for file path patterns: starts with '/', './', '../', or 'file:'
            if (
                typeof imageUrl === 'string' && (
                    imageUrl.startsWith('/') ||
                    imageUrl.startsWith('./') ||
                    imageUrl.startsWith('../') ||
                    imageUrl.startsWith('file:')
                )
            ) {{
                return true;
            }}
            return false;
        }})();

	        let toadd = imageUrl;
	        if (isUrlOrFilePath) {{
	            const img = document.createElement('img');
	            img.src = imageUrl;
	            img.alt = getImageAltFromUrl(imageUrl) || 'Image';
	            img.loading = 'lazy';
	            img.decoding = 'async';
	            img.className = 'editable-blog-image';
	            toadd = img;
	        }} else {{
            console.log("It's plain text");
        }}



        const selection = window.getSelection();
        if (selection && selection.rangeCount) {{
            const range = selection.getRangeAt(0);
            if (paragraph.contains(range.commonAncestorContainer)) {{
                range.deleteContents();
                let nodeToInsert = toadd;
                if (typeof toadd === 'string') {{
                    nodeToInsert = document.createTextNode(toadd);
                }}
                range.insertNode(nodeToInsert);
                range.setStartAfter(nodeToInsert);
                range.collapse(true);
                selection.removeAllRanges();
                selection.addRange(range);
                return;
            }}
        }}

        if (typeof toadd === 'string') {{
            paragraph.appendChild(document.createTextNode(toadd));
        }} else {{
            paragraph.appendChild(toadd);
        }}
        placeCaretAtEnd(paragraph);
    }}

    function getParagraphSelection(paragraph) {{
        const selection = window.getSelection();
        if (!selection || !selection.rangeCount) return null;

        const range = selection.getRangeAt(0);
        if (!paragraph.contains(range.commonAncestorContainer)) return null;

        return {{
            range: range.cloneRange(),
            text: selection.toString().trim(),
        }};
    }}

    function insertLinkIntoSection(paragraph, rawUrl, rawText, savedRange) {{
        let url = (rawUrl || '').trim();
        if (!url) return false;

        if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) {{
            url = 'https://' + url;
        }}

        let parsedUrl;
        try {{
            parsedUrl = new URL(url);
        }} catch (err) {{
            return false;
        }}

        if (!['http:', 'https:', 'mailto:', 'tel:'].includes(parsedUrl.protocol)) {{
            return false;
        }}

        const link = document.createElement('a');
        link.href = parsedUrl.href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';

        const linkText = ` ${{(rawText || '').trim()}} `;
        const paragraphSelection = getParagraphSelection(paragraph);
        const selectedText = paragraphSelection ? paragraphSelection.text : '';
        link.textContent = linkText || selectedText || parsedUrl.href;

        if (savedRange && paragraph.contains(savedRange.commonAncestorContainer)) {{
            savedRange.deleteContents();
            savedRange.insertNode(link);
            savedRange.setStartAfter(link);
            savedRange.collapse(true);
            const activeSelection = window.getSelection();
            activeSelection.removeAllRanges();
            activeSelection.addRange(savedRange);
            return true;
        }}

        if (paragraphSelection) {{
            const range = paragraphSelection.range;
            if (paragraph.contains(range.commonAncestorContainer)) {{
                range.deleteContents();
                range.insertNode(link);
                range.setStartAfter(link);
                range.collapse(true);
                const activeSelection = window.getSelection();
                activeSelection.removeAllRanges();
                activeSelection.addRange(range);
                return true;
            }}
        }}

        paragraph.appendChild(document.createTextNode(' '));
        paragraph.appendChild(link);
        placeCaretAtEnd(paragraph);
        return true;
    }}

    async function uploadImageIntoSection(paragraph, imageInput, imageNameInput, uploadButton, status) {{
        const file = imageInput.files && imageInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('image', file);
        formData.append('image_name', imageNameInput.value.trim());
        formData.append('imageclassID', place_name);
        formData.append('blog_place_slug', blogPlaceSlug);
        formData.append('blog_title_slug', blogTitleSlug);
        formData.append('source', 'blog_inline_editor');

        uploadButton.disabled = true;
        status.textContent = 'Uploading image...';
        status.classList.remove('error');

        try {{
            const response = await fetch(blogImageUploadUrl, {{
                method: 'POST',
                body: formData,
                headers: {{
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie('csrftoken'),
                }}
            }});

            const data = await response.json();
            if (!response.ok || data.status !== 'success' || !data.image_url) {{
                throw new Error(data.error || `HTTP ${{response.status}}`);
            }}

            insertUploadedImageIntoSection(paragraph, data.image_url);
            status.textContent = 'Image inserted. Click Save to keep it.';
            imageNameInput.value = '';
        }} catch (err) {{
            console.error("Error uploading image:", err);
            status.textContent = 'Image upload failed. Please try again.';
            status.classList.add('error');
        }} finally {{
            uploadButton.disabled = false;
            imageInput.value = '';
        }}
    }}

    function placeCaretAtEnd(element) {{
        const range = document.createRange();
        range.selectNodeContents(element);
        range.collapse(false);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }}

    function attachParagraphEditButton(paragraph) {{
        if (paragraph.querySelector('.blog-edit-button')) return;

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'blog-edit-button';
        button.innerHTML = '&#9998;';
        button.title = 'Edit section';
        button.setAttribute('aria-label', 'Edit section');
        button.addEventListener('click', () => startParagraphEdit(paragraph));
        paragraph.appendChild(button);
    }}

    function setupEditableParagraphs() {{
        const body = document.getElementById('blog-editable-body');
        if (!body) return;

        body.querySelectorAll('h2[data-blog-edit-index], p[data-blog-edit-index]').forEach(paragraph => {{
            attachParagraphEditButton(paragraph);
        }});
    }}

    function updateVisibleLastUpdated(data) {{
        if (!data || !data.updated_at_display) return;

        let lastUpdated = document.getElementById('blog-last-updated');
        if (!lastUpdated) {{
            const body = document.getElementById('blog-editable-body');
            if (!body || !body.parentNode) return;

            const meta = document.createElement('p');
            meta.className = 'blog-date-meta';
            const span = document.createElement('span');
            span.appendChild(document.createTextNode('Last updated '));
            lastUpdated = document.createElement('time');
            lastUpdated.id = 'blog-last-updated';
            span.appendChild(lastUpdated);
            meta.appendChild(span);
            body.parentNode.insertBefore(meta, body);
        }}

        if (data.updated_at) {{
            lastUpdated.setAttribute('datetime', data.updated_at);
        }}
        lastUpdated.textContent = data.updated_at_display;
    }}

    function finishParagraphEdit(paragraph, tools, replacementHTML) {{
        paragraph.contentEditable = 'false';
        delete paragraph.dataset.editing;

        if (replacementHTML !== null) {{
            paragraph.innerHTML = replacementHTML;
        }}

        if (tools) tools.remove();
        attachParagraphEditButton(paragraph);
    }}

    
    
    function startParagraphEdit(paragraph) {{
        if (paragraph.dataset.editing === 'true') return;


        

        let originalHTML = getParagraphCleanHTML(paragraph);
        let editButton = paragraph.querySelector('.blog-edit-button');
        if (editButton) editButton.remove();
        paragraph.dataset.editing = 'true';
        paragraph.contentEditable = 'true';
        paragraph.focus();
        placeCaretAtEnd(paragraph);

        let tools = document.createElement('div');
        tools.className = 'blog-paragraph-tools';

        let saveButton = document.createElement('button');
        saveButton.type = 'button';
        saveButton.className = 'blog-save-button';
        saveButton.textContent = 'Save';

        let cancelButton = document.createElement('button');
        cancelButton.type = 'button';
        cancelButton.className = 'blog-cancel-button';
        cancelButton.textContent = 'Cancel';

        let imageUploadButton = document.createElement('button');
        imageUploadButton.type = 'button';
        imageUploadButton.className = 'blog-image-upload-button';
        imageUploadButton.textContent = 'Upload image';

        let imageNameInput = document.createElement('input');
        imageNameInput.type = 'text';
        imageNameInput.className = 'blog-image-name-input';
        imageNameInput.placeholder = 'Image name';

        let imageUploadInput = document.createElement('input');
        imageUploadInput.type = 'file';
        imageUploadInput.accept = 'image/*';
        imageUploadInput.className = 'blog-image-upload-input';

        let addUrlButton = document.createElement('button');
        addUrlButton.type = 'button';
        addUrlButton.className = 'blog-url-button';
        addUrlButton.textContent = 'Add URL';

        let linkTextInput = document.createElement('input');
        linkTextInput.type = 'text';
        linkTextInput.className = 'blog-url-input';
        linkTextInput.placeholder = 'Link text';
        linkTextInput.style.display = 'none';

        let urlInput = document.createElement('input');
        urlInput.type = 'url';
        urlInput.className = 'blog-url-input';
        urlInput.placeholder = 'https://example.com';
        urlInput.style.display = 'none';
        let pendingLinkRange = null;

        let startRecognitionButton = document.createElement('button');
        startRecognitionButton.type = 'button';
        startRecognitionButton.textContent = 'Voice input';
        startRecognitionButton.className = 'blog-voice-button';
        startRecognitionButton.value = '';
        startRecognitionButton.id = 'start-voice-btn';

        startRecognitionButton.style.background = '#2563eb';
        startRecognitionButton.style.color = '#ffffff';
        startRecognitionButton.style.border = 'none';
        startRecognitionButton.style.borderRadius = '7px';
        startRecognitionButton.style.padding = '0.6em 1em';
        startRecognitionButton.style.fontSize = '1rem';
        startRecognitionButton.style.fontWeight = '600';
        startRecognitionButton.style.cursor = 'pointer';
        startRecognitionButton.style.margin = '0.5em 0';
        startRecognitionButton.style.boxSizing = 'border-box';
        let SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let recognitionActive = false;
        let manuallyStopped = false;
        let finalTranscript = "";
        let stopRecognitionButton = document.createElement('button');

        stopRecognitionButton.type = 'button';
        stopRecognitionButton.className = 'blog-voice-button';
        stopRecognitionButton.textContent = 'Stop';
        stopRecognitionButton.style.background = '#b42318';
        stopRecognitionButton.style.color = '#ffffff';
        stopRecognitionButton.style.border = 'none';
        stopRecognitionButton.style.borderRadius = '7px';
        stopRecognitionButton.style.padding = '0.6em 1em';
        stopRecognitionButton.style.fontSize = '1rem';
        stopRecognitionButton.style.fontWeight = '600';
        stopRecognitionButton.style.cursor = 'pointer';
        stopRecognitionButton.style.margin = '0.5em 0';
        stopRecognitionButton.style.boxSizing = 'border-box';
        stopRecognitionButton.id = 'stop-voice-btn';
        stopRecognitionButton.style.display = 'none';

        let copyRecognitionButton = document.createElement('button');
        copyRecognitionButton.type = 'button';
        copyRecognitionButton.className = 'blog-voice-button';
        copyRecognitionButton.textContent = 'Copy';
        copyRecognitionButton.style.background = '#0f766e';
        copyRecognitionButton.style.color = '#ffffff';
        copyRecognitionButton.style.border = 'none';
        copyRecognitionButton.style.borderRadius = '7px';
        copyRecognitionButton.style.padding = '0.6em 1em';
        copyRecognitionButton.style.fontSize = '1rem';
        copyRecognitionButton.style.fontWeight = '600';
        copyRecognitionButton.style.cursor = 'pointer';
        copyRecognitionButton.style.margin = '0.5em 0';
        copyRecognitionButton.style.boxSizing = 'border-box';
        copyRecognitionButton.style.display = 'none';

        function updateLiveText(text) {{
            liveTextRecognition.value = text;
            liveTextRecognition.style.height = 'auto';
            liveTextRecognition.style.height = liveTextRecognition.scrollHeight + 'px';
            copyRecognitionButton.style.display = text.trim() ? 'block' : 'none';
        }}

        function copyLiveTextValue() {{
            let text = liveTextRecognition.value;
            if (!text.trim()) return;

            let markCopied = () => {{
                copyRecognitionButton.textContent = 'Copied';
                setTimeout(() => {{
                    copyRecognitionButton.textContent = 'Copy';
                }}, 1200);
            }};

            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(text).then(markCopied).catch((err) => {{
                    console.error("Could not copy live text:", err);
                }});
                return;
            }}

            liveTextRecognition.focus();
            liveTextRecognition.select();

            try {{
                document.execCommand('copy');
                markCopied();
            }} catch (err) {{
                console.error("Could not copy live text:", err);
            }}
        }}

        startRecognitionButton.addEventListener('click', () => {{
            if (!SpeechRecognition) {{
                alert("Speech Recognition is not supported in this browser.");
                return;
            }}

            if (!recognition) {{
                recognition = new SpeechRecognition();

                recognition.lang = "en-US";

                // Android Chrome does not reliably support continuous recognition.
                recognition.continuous = false;

                recognition.interimResults = true;

                recognition.onstart = () => {{
                    recognitionActive = true;
                    manuallyStopped = false;

                    startRecognitionButton.disabled = true;
                    startRecognitionButton.textContent = 'Listening...';
                    startRecognitionButton.style.background = '#94a3b8';
                    startRecognitionButton.style.cursor = 'not-allowed';
                    startRecognitionButton.style.opacity = '0.8';
                    startRecognitionButton.style.boxShadow = 'none';

                    liveTextRecognition.style.display = 'block';
                    stopRecognitionButton.style.display = 'block';
                    copyRecognitionButton.style.display = liveTextRecognition.value.trim() ? 'block' : 'none';
                }};

                recognition.onresult = (event) => {{
                    let interimTranscript = "";

                    for (let i = event.resultIndex; i < event.results.length; i++) {{
                        let transcript = event.results[i][0].transcript;

                        if (event.results[i].isFinal) {{
                            finalTranscript += transcript + " ";
                        }} else {{
                            interimTranscript += transcript;
                        }}
                    }}

                    updateLiveText(finalTranscript + interimTranscript);
                }};

                recognition.onerror = (event) => {{
                    console.error("Speech recognition error:", event.error);
                    recognitionActive = false;

                    if (['not-allowed', 'service-not-allowed', 'audio-capture'].includes(event.error)) {{
                        manuallyStopped = true;
                    }}

                    startRecognitionButton.disabled = false;
                    startRecognitionButton.textContent = 'Voice input';
                    startRecognitionButton.style.background = '#2563eb';
                    startRecognitionButton.style.cursor = 'pointer';
                    startRecognitionButton.style.opacity = '1';

                    stopRecognitionButton.style.display = 'none';
                    copyRecognitionButton.style.display = liveTextRecognition.value.trim() ? 'block' : 'none';
                }};

                recognition.onend = () => {{
                    recognitionActive = false;

                    if (!manuallyStopped) {{
                        startRecognitionButton.disabled = true;
                        startRecognitionButton.textContent = 'Listening...';
                        startRecognitionButton.style.background = '#94a3b8';
                        startRecognitionButton.style.cursor = 'not-allowed';
                        startRecognitionButton.style.opacity = '0.8';
                        startRecognitionButton.style.boxShadow = 'none';

                        stopRecognitionButton.style.display = 'block';
                        copyRecognitionButton.style.display = liveTextRecognition.value.trim() ? 'block' : 'none';

                        setTimeout(() => {{
                            if (manuallyStopped || !recognition) return;

                            try {{
                                recognition.start();
                            }} catch (err) {{
                                console.error("Could not restart recognition:", err);
                                recognitionActive = false;

                                startRecognitionButton.disabled = false;
                                startRecognitionButton.textContent = 'Voice input';
                                startRecognitionButton.style.background = '#2563eb';
                                startRecognitionButton.style.cursor = 'pointer';
                                startRecognitionButton.style.opacity = '1';
                                startRecognitionButton.style.boxShadow = '0 2px 6px rgba(37, 99, 235, 0.25)';

                                stopRecognitionButton.style.display = 'none';
                            }}
                        }}, 300);

                        return;
                    }}

                    startRecognitionButton.disabled = false;
                    startRecognitionButton.textContent = 'Voice input';
                    startRecognitionButton.style.background = '#2563eb';
                    startRecognitionButton.style.cursor = 'pointer';
                    startRecognitionButton.style.opacity = '1';
                    startRecognitionButton.style.boxShadow = '0 2px 6px rgba(37, 99, 235, 0.25)';

                    stopRecognitionButton.style.display = 'none';
                    copyRecognitionButton.style.display = liveTextRecognition.value.trim() ? 'block' : 'none';
                }};
            }}

            if (!recognitionActive) {{
                finalTranscript = "";
                fixedTextRecognition.value = "";
                copyRecognitionButton.style.display = 'none';

                try {{
                    recognition.start();
                }} catch (err) {{
                    console.error("Could not start recognition:", err);
                }}
            }}
        }});

        stopRecognitionButton.addEventListener('click', () => {{
            manuallyStopped = true;

            if (recognition && recognitionActive) {{
                recognition.stop();
            }}

            recognitionActive = false;

            if (liveTextRecognition.value.trim()) {{
                insertUploadedImageIntoSection(paragraph, liveTextRecognition.value.trim() + ' ');
                liveTextRecognition.value = '';
                liveTextRecognition.style.display = 'none';
                copyRecognitionButton.style.display = 'none';
            }}

            startRecognitionButton.disabled = false;
            startRecognitionButton.textContent = 'Voice input';
            stopRecognitionButton.style.display = 'none';
            
        }});

        copyRecognitionButton.addEventListener('click', copyLiveTextValue);





        let liveTextRecognition = document.createElement('textarea');

        liveTextRecognition.style.display = 'none';
        liveTextRecognition.id = 'liveText';
        liveTextRecognition.rows = 2;

        liveTextRecognition.style.width = '100%';
        liveTextRecognition.style.minWidth = '320px';
        liveTextRecognition.style.maxWidth = '100%';
        liveTextRecognition.style.fontSize = '1.15rem';
        liveTextRecognition.style.padding = '0.5em 0.7em';
        liveTextRecognition.style.margin = '0.5em 0';
        liveTextRecognition.style.boxSizing = 'border-box';
        liveTextRecognition.style.borderRadius = '7px';
        liveTextRecognition.style.border = '1.5px solid #2563eb';
        liveTextRecognition.style.background = '#f7faff';
        liveTextRecognition.style.color = '#27332f';

        /* Important for auto-expanding */
        liveTextRecognition.style.resize = 'none';
        liveTextRecognition.style.overflow = 'hidden';
        liveTextRecognition.style.minHeight = '3em';


        function autoResizeTextarea(textarea) {{

            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }}

        liveTextRecognition.addEventListener('input', () => {{
            autoResizeTextarea(liveTextRecognition);
            finalTranscript = liveTextRecognition.value;
        }});


        let fixedTextRecognition = document.createElement('input');
        fixedTextRecognition.type = 'hidden';
        fixedTextRecognition.id = 'fixedText';

        let status = document.createElement('span');
        status.className = 'blog-edit-status';

        saveButton.addEventListener('click', () => saveParagraphEdit(paragraph, tools));
        cancelButton.addEventListener('click', () => finishParagraphEdit(paragraph, tools, originalHTML));
        imageUploadButton.addEventListener('click', () => imageUploadInput.click());
        imageUploadInput.addEventListener('change', () => uploadImageIntoSection(paragraph, imageUploadInput, imageNameInput, imageUploadButton, status));
        addUrlButton.addEventListener('click', () => {{
            if (urlInput.style.display === 'none') {{
                const selectedLink = getParagraphSelection(paragraph);
                pendingLinkRange = selectedLink ? selectedLink.range : null;
                linkTextInput.value = selectedLink ? selectedLink.text : '';
                linkTextInput.style.display = 'block';
                urlInput.style.display = 'block';
                linkTextInput.focus();
                return;
            }}

            if (insertLinkIntoSection(paragraph, urlInput.value, linkTextInput.value, pendingLinkRange)) {{
                status.textContent = 'URL inserted. Click Save to keep it.';
                status.classList.remove('error');
                linkTextInput.value = '';
                urlInput.value = '';
                linkTextInput.style.display = 'none';
                urlInput.style.display = 'none';
                pendingLinkRange = null;
            }} else {{
                status.textContent = 'Please enter a valid URL.';
                status.classList.add('error');
                urlInput.focus();
            }}
        }});
        const handleUrlInputKeydown = (event) => {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                if (event.target === linkTextInput && !urlInput.value.trim()) {{
                    urlInput.focus();
                    return;
                }}
                addUrlButton.click();
            }}

            if (event.key === 'Escape') {{
                linkTextInput.value = '';
                urlInput.value = '';
                linkTextInput.style.display = 'none';
                urlInput.style.display = 'none';
                pendingLinkRange = null;
                status.textContent = '';
                status.classList.remove('error');
                paragraph.focus();
            }}
        }};
        linkTextInput.addEventListener('keydown', handleUrlInputKeydown);
        urlInput.addEventListener('keydown', handleUrlInputKeydown);

        tools.appendChild(saveButton);
        tools.appendChild(cancelButton);
        tools.appendChild(status);
        tools.appendChild(startRecognitionButton);
        tools.appendChild(stopRecognitionButton);
        tools.appendChild(copyRecognitionButton);
        tools.appendChild(liveTextRecognition);
        tools.appendChild(fixedTextRecognition);
        tools.appendChild(imageNameInput);
        tools.appendChild(imageUploadButton);
        tools.appendChild(imageUploadInput);
        tools.appendChild(urlInput);
        tools.appendChild(linkTextInput);
        tools.appendChild(addUrlButton);
        
        
        paragraph.insertAdjacentElement('afterend', tools);

    }} //startParagraphedit(paragraph)



    




async function saveParagraphEdit(paragraph, tools) {{
    let status = tools.querySelector('.blog-edit-status');
    let saveButton = tools.querySelector('.blog-save-button');
    let editedHTML = getParagraphCleanHTML(paragraph).trim();

    if (!paragraphHasVisibleContent(paragraph)) {{
        status.textContent = 'Section cannot be empty.';
        status.classList.add('error');
        return;
    }}

    saveButton.disabled = true;
    status.textContent = 'Saving...';
    status.classList.remove('error');
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;

    try {{
        let response = await fetch(blogParagraphSaveUrl, {{
            method: 'POST',
            headers: {{
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCookie('csrftoken'),
            }},
            body: JSON.stringify({{
                place_slug: blogPlaceSlug,
                title_slug: blogTitleSlug,
                page_url: window.location.pathname,
                paragraph_index: Number(paragraph.dataset.blogEditIndex),
                editable_tag: paragraph.dataset.blogEditTag || paragraph.tagName.toLowerCase(),
                edited_html: editedHTML
            }})
        }});

        const data = await response.json();
        if (!response.ok || !data.ok) {{
            throw new Error(data.error || `HTTP ${{response.status}}`);
        }}
        saveButton.textContent = 'Saved';
        saveButton.disabled = false;
        updateVisibleLastUpdated(data);
        finishParagraphEdit(paragraph, tools, data.edited_html || editedHTML);
    }} catch (err) {{
        console.error("Error saving paragraph:", err);
        saveButton.disabled = false;
        status.textContent = `Save failed: ${{err.message || 'Please try again.'}}`;
        status.classList.add('error');
        saveButton.textContent = 'Save Again';
        saveButton.disabled = false;
    }}
}}




function getCookie(name) {{
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {{
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {{
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {{
                cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                break;
            }}
        }}
    }}
    return cookieValue;
}}
csrftoken = getCookie('csrftoken');

document.addEventListener("DOMContentLoaded", () => {{
    const form = document.querySelector("#imageform");
    if (form) {{
        form.addEventListener("submit", function(e) {{
            e.preventDefault();
            const formData = new FormData(form);
            fetch("{upload_url}", {{
                method: "POST",
                body: formData,
                headers: {{
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": csrftoken,
                }}
            }})
            .then(response => response.json())
            .then(data => console.log("Success:"))
            .catch(err => console.error(err));
        }});
    }}

    setupEditableParagraphs();
    fetchAndInsertImages();
    getBlogLists();
    fetchCollections();


    
let bottomTriggered = false;






}});
  

// Close dropdown when clicking outside (desktop & mobile)
document.addEventListener('click', (ev) => {{
    const dropdown = document.getElementById('dropdowntoogle');
    if (!dropdown) return;
    const trigger = dropdown.querySelector('a');
    const menu = dropdown.querySelector('.dropdown-menu');
    if (dropdown.classList.contains('open') && !dropdown.contains(ev.target)) {{
        dropdown.classList.remove('open');
    }}
}});

// Close on Escape key
document.addEventListener('keydown', (ev) => {{
    if (ev.key === 'Escape') {{
        const dropdown = document.getElementById('dropdowntoogle');
        if (dropdown) dropdown.classList.remove('open');
    }}
}});
  
// Close dropdown when a blog link is clicked
document.addEventListener('click', (ev) => {{
    const dropdown = document.getElementById('dropdowntoogle');
    if (!dropdown) return;
    const menu = dropdown.querySelector('.dropdown-menu');
    if (menu && menu.contains(ev.target) && ev.target.tagName === 'A') {{
        dropdown.classList.remove('open');
    }}
}});
  

</script>
    <section class="cta-section tour-guide-card">
        <h2>Tour Guide Contacts</h2>
        <p>Save a local contact before you go so it is easier to plan the day.</p>
        {{% for tg in tourguide %}}
        <input type="text" value="{{{{ tg.mobile_number }}}}" readonly aria-label="Tour guide mobile number">
        {{% endfor %}}

    </section>
  <footer>
  <form method="post" action="{subscribe_url}" id="subscribeForm">
    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    <input type="email" name="email" placeholder="Your email" required>
    <input type="text" name="name" placeholder="Name (optional)" type="text">
    <input type="hidden" name="source" value="blog_footer">
    <button type="submit">Subscribe</button>
</form>
    <h1>{title}</h1>
  <p><strong>Location:</strong> {place_name}</p>


    <p>Written by <strong><a href="https://foreigntravelsteps.com">Foreign Travel Steps</a></strong> | Contact Me at <a href="#">foreigntravelsteps@paratara.com</a> </p>
  
  





<form id="imageform" action="{upload_url}" method="POST" enctype="multipart/form-data">
    {{% csrf_token %}}

    <input type="hidden" value="{place_name}" name="imageclassID" required>
    <input type="file" name="image" required>
    <button type="submit">Share your {place_name} Pictures</button>
</form>
</footer>
</body>
</html>
"""
    





    folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "singlepage2", "templates", "blogs", place_slug
    )
    os.makedirs(folder, exist_ok=True)

    blog_slug = slugify(title)
    file_path = os.path.join(folder, f"{blog_slug}.html")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        optimize_file(file_path)
    except Exception:
        pass


    return html_content

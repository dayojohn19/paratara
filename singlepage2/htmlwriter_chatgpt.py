from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils import timezone
import os
from django.utils.text import slugify
from django.conf import settings
import json
from garden.models import Collection, CollectionGroup
import ast
from home.models import Places_v2
from apis.models import Blogs
from singlepage2.pyhtmlopt import optimize_file
import re
from html import escape
from bs4 import BeautifulSoup, NavigableString
client = settings.GROK_CLIENT
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


def parse_llm_json_array(raw_text):
    """Robustly parse a JSON array from an LLM response.

    Handles:
    - Raw JSON arrays
    - Markdown-fenced JSON (```json ... ```)
    - Preamble / trailing text around the array
    - Python-style literals (True/False/None) via ast.literal_eval fallback
    """
    if not raw_text:
        return []

    cleaned = str(raw_text).strip()

    # Strip leading/trailing markdown code fences
    cleaned = re.sub(r"^```(?:json|JSON|python)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    # Extract the first [...] block
    start = cleaned.find('[')
    end = cleaned.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return []

    payload = cleaned[start:end + 1]

    for parser in (json.loads, ast.literal_eval):
        try:
            result = parser(payload)
            if isinstance(result, list):
                return result
        except Exception:
            continue

    return []


def mark_editable_blog_body(body_html):
    soup = BeautifulSoup(body_html or "", "html.parser")
    for container in soup.find_all(["section", "aside", "footer"]):
        for child in list(container.contents):
            if isinstance(child, NavigableString) and child.strip():
                paragraph = soup.new_tag("p")
                paragraph.string = re.sub(r"\s+", " ", str(child)).strip()
                child.replace_with(paragraph)

        direct_paragraphs = container.find_all("p", recursive=False)
        if len(direct_paragraphs) > 1:
            primary_paragraph = direct_paragraphs[0]
            for extra_paragraph in direct_paragraphs[1:]:
                if primary_paragraph.contents and extra_paragraph.contents:
                    primary_paragraph.append(" ")
                for node in list(extra_paragraph.contents):
                    primary_paragraph.append(node.extract())
                extra_paragraph.decompose()

    for idx, editable_block in enumerate(soup.find_all(["h2", "p"])):
        editable_block["data-blog-edit-index"] = str(idx)
        editable_block["data-blog-edit-tag"] = editable_block.name
    for image in soup.find_all("img"):
        image["loading"] = "lazy"
        image["decoding"] = "async"
        image["fetchpriority"] = "low"
    return str(soup)


def format_blog_datetime(value):
    value = value or timezone.now()
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    display = value.strftime("%B %d, %Y at %I:%M %p").replace(" 0", " ")
    return value.isoformat(), display


def render_faq_section(faq_entries):
    rows = []
    for faq_index, entry in enumerate(faq_entries or []):
        if not isinstance(entry, dict):
            continue

        question = (
            entry.get("name")
            or entry.get("question")
            or entry.get("text")
            or ""
        ).strip()

        accepted_answer = (
            entry.get("acceptedAnswer")
            or entry.get("accepted_answer")
            or entry.get("answer")
            or {}
        )
        if isinstance(accepted_answer, dict):
            answer = (
                accepted_answer.get("text")
                or accepted_answer.get("answer")
                or ""
            ).strip()
        else:
            answer = str(accepted_answer).strip()

        if not question or not answer:
            continue

        rows.append(f"""
        <details class="faq-item">
            <summary data-blog-edit-index="{faq_index * 2 + 1}" data-blog-edit-scope="faq" data-blog-edit-tag="summary">{escape(question)}</summary>
            <p data-blog-edit-index="{faq_index * 2 + 2}" data-blog-edit-scope="faq" data-blog-edit-tag="p">{escape(answer)}</p>
        </details>
        """)

    if not rows:
        return ""

    return f"""
    <section class="faq-section" aria-labelledby="faq-heading">
        <h2 id="faq-heading" data-blog-edit-index="0" data-blog-edit-scope="faq" data-blog-edit-tag="h2">Frequently Asked Questions</h2>
        <div class="faq-list">{''.join(rows)}</div>
    </section>
    """


# USES call htmlwriter then calls generate_blog_object to save the blog in the database, then generates the html page with SEO optimizations, FAQ schema, and article schema for better search engine visibility. The generated HTML is saved in the appropriate folder structure for serving as a static page on the site.
def generate_blog_object(request, place_name, title, category='Guide', summary='No Summary Provided', text_content=''):
    place = Places_v2.objects.filter(placename__iexact=place_name).first()
    if not place:
        raise ValueError(f"Place not found: {place_name!r}")
    category = normalize_blog_category(category)
    candidate_summary = clean_blog_metadata(summary)[:400].strip()
    if candidate_summary in DEFAULT_SUMMARY_VALUES:
        candidate_summary = ''
    persisted_summary = candidate_summary or 'No Summary Provided'
    title_slug = slugify(title)
    plain_text_content = BeautifulSoup(text_content or '', 'html.parser').get_text(' ', strip=True)
    readtime = max(1, round(len(plain_text_content.split()) / 185)) if plain_text_content else 5

    place_blog_list = list(place.blog.all())
    for b in place_blog_list:
        if slugify(getattr(b, 'title', '') or '') == title_slug:
            update_fields = []
            existing_category = getattr(b, 'category', '') or ''
            if category != existing_category and (category != 'Guide' or existing_category in ('', 'Guide')):
                b.category = category
                update_fields.append('category')

            existing_summary = clean_blog_metadata(getattr(b, 'summarize', '') or '')
            if candidate_summary and candidate_summary != existing_summary:
                b.summarize = candidate_summary
                update_fields.append('summarize')

            if clean_blog_metadata(getattr(b, 'textContent', '') or '') != plain_text_content:
                b.textContent = plain_text_content
                update_fields.append('textContent')
            if getattr(b, 'readtime', None) != readtime:
                b.readtime = readtime
                update_fields.append('readtime')
            if update_fields:
                b.save(update_fields=list(dict.fromkeys(update_fields)))

            # Regenerate the static page when a blog with the same slug is regenerated.
            generate_blog_page(request, place_name, title, text_content, category=category)
            if not place.blog.filter(pk=b.pk).exists():
                place.blog.add(b)
            return b
    title = re.sub(r'<a\b[^>]*>(.*?)</a>',r'\1',title,flags=re.IGNORECASE | re.DOTALL)
    blog_item = Blogs.objects.create(
        category=category,
        blogplace=place,
        title=title,
        textContent=plain_text_content,
        summarize=persisted_summary,
        readtime=readtime,
    )
    generate_blog_page(request, place_name, title, text_content, category=category)
    place.blog.add(blog_item)
    return blog_item


def generate_blog_page(request, place_name, title, body_text, cover_image_url=None, faq_entries=None, blog_searchable_keys_description=None, category=None):
    category = normalize_blog_category(category)
    def _get_image_cover(place_name, title):
        from imageapp.imageuploader import getTitlePhoto
        togen = f"Travel guide cover photo for {title} in {place_name}. Show the destination clearly with natural colors and simple composition."
        image_url = getTitlePhoto(request, togen)
        return image_url
        

    def _strip_html_tags(html: str) -> str:
        return BeautifulSoup(html or '', 'html.parser').get_text(' ', strip=True)
    def create_blog_searchable_keys_description(title, place_name, category):
        try:
            meta_prompt = f'''Write one meta "{title}" about "{place_name}".

Rules:
- Under 150 characters.
- Plain, factual, and direct.
- No flowery words, no hype, no superlatives, no clickbait.
- If it fits naturally, mention {place_name} and practical details like tips or best time to visit.
- Return only the meta description text, nothing else.'''
            meta_res = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": meta_prompt}],
                max_tokens=200
            )
            _blog_searchable = meta_res.choices[0].message.content.strip().strip('"')
            return _blog_searchable
        except Exception:
            _blog_searchable = f"{title} in {place_name}: directions, entrance fee, practical tips, and best time to visit."
        
        return _blog_searchable

    # if cover_image_url is None:
    #     return _get_image_cover(place_name, title)
    if blog_searchable_keys_description is None:
        blog_searchable_keys_description = create_blog_searchable_keys_description(title, place_name, category)
    title = (title or '').strip() or f"{category} to {place_name}"
    text_content = _strip_html_tags(body_text)
    cover_image_url = cover_image_url or ''

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
    try:
        place_page_url = reverse("home:place_by_slug", kwargs={"place_slug": place_slug})
    except Exception:
        place_page_url = f"/places/{place_slug}/"
    editable_body_text = mark_editable_blog_body(body_text)
    generated_at = timezone.now()
    published_iso, published_display = format_blog_datetime(generated_at)
    modified_iso, modified_display = format_blog_datetime(generated_at)
    schema_date = timezone.localtime(generated_at).date().isoformat()

    collections_html = f'''
                        <div id="collections-header">
                            <h2>Local Collections &amp; QR Experiences</h2>
                            <p id="collections-loading">Discover interactive collections nearby. Scan QR codes to save memories. Loading...</p>
                            <div id="dynamic-collections" class="collection-section"></div>
                        </div>
                        '''

    # Build FAQ Schema and Article Schema
    faq_entries = []
    try:
        faq_questions = FAQ_QUESTIONS_BY_CATEGORY.get(category, FAQ_QUESTIONS_BY_CATEGORY["Guide"])

        faq_prompt = f'''Write 5 short, factual FAQs about "{title}" in "{place_name}".

Return ONLY a raw JSON array with no markdown, no code fences, and no explanation text before or after.

Each item must use exactly this shape:
{{"@type": "Question", "@id": "{canonical_url}#short-question-slug", "name": "<Question?>", "acceptedAnswer": {{"@type": "Answer", "text": "<Answer text.>"}}}}

Rules:
- Keep questions direct and specific.
- Keep answers plain, factual, and short (1 to 2 sentences).
- Do not use flowery words, hype, superlatives, or marketing tone.
- Do not invent prices, opening hours, or facts you are not sure about.
- If unsure about a specific fact, answer with a practical general guideline instead.
- Use the canonical URL "{canonical_url}" in every "@id" field.
- Cover these angles: {faq_questions}
- Start the array with [ and end with ].
'''
        res = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[{"role": "user", "content": faq_prompt}],
            max_tokens=1200
        )
        faq_text = res.choices[0].message.content.strip()

        # Robust parse: handles markdown fences, preamble text, Python literals
        parsed_faqs = parse_llm_json_array(faq_text)
        for entry in parsed_faqs:
            if not isinstance(entry, dict):
                continue
            # Normalize keys so downstream rendering is consistent
            question_name = entry.get("name") or entry.get("question") or ""
            accepted = entry.get("acceptedAnswer") or entry.get("accepted_answer") or {}
            if isinstance(accepted, dict):
                answer_text = accepted.get("text") or accepted.get("answer") or ""
            else:
                answer_text = str(accepted)

            if not question_name or not answer_text:
                continue

            faq_entries.append({
                "@type": "Question",
                "@id": f"{canonical_url}#{slugify(question_name)}",
                "name": question_name.strip(),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer_text.strip(),
                },
            })

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
                                            <link rel="preconnect" href="https://fonts.googleapis.com">
                                            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                                            <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;0,9..144,700;1,9..144,400&amp;family=Inter:wght@400;500;600;700;800&amp;family=Roboto+Mono:wght@400;500&amp;display=swap">
                                            <!-- Google tag (gtag.js) -->
                                            <script> window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}} gtag('js', new Date()); gtag('config', 'G-BR63L5YLJD'); </script>
                                            <meta name="google-site-verification" content="8jqO-yxHVkp0mIbnh_nvbfA0N21q0QcCR4aDkFbb8rc" />
                                            <meta name="blog-image-layout-version" content="2">
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
                                                <meta property="og:description" content="{blog_searchable_keys_description if blog_searchable_keys_description else f'{title} in {place_name}: directions, entrance fee, practical tips, and best time to visit.'}">
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
:root {{
    --ink: #14211d;
    --ink-soft: #33463f;
    --ink-muted: #6b7d76;
    --brand: #0f766e;
    --brand-dark: #0b544e;
    --brand-soft: #e6f4f1;
    --accent: #d97706;
    --accent-dark: #b45309;
    --accent-soft: #fff5e6;
    --link: #1d4ed8;
    --page: #f5f7f5;
    --surface: #ffffff;
    --surface-soft: #f8fbf9;
    --surface-warm: #fdfaf5;
    --border: #e5ebe7;
    --border-strong: #d1dad4;
    --shadow-xs: 0 1px 2px rgba(20, 33, 29, 0.05);
    --shadow-sm: 0 2px 6px rgba(20, 33, 29, 0.06);
    --shadow-md: 0 10px 30px rgba(20, 33, 29, 0.08);
    --shadow-lg: 0 24px 50px rgba(20, 33, 29, 0.10);
    --radius-xs: 6px;
    --radius-sm: 10px;
    --radius: 16px;
    --radius-lg: 22px;
    --radius-xl: 32px;
    --font-body: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --font-display: "Fraunces", Georgia, "Times New Roman", serif;
    --font-mono: "Roboto Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    --container: 1120px;
}}

*, *::before, *::after {{ box-sizing: border-box; }}
* {{ margin: 0; padding: 0; }}

html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }}

body {{
    min-height: 100vh;
    background:
        radial-gradient(900px 500px at 8% -10%, rgba(15, 118, 110, 0.07), transparent 60%),
        radial-gradient(700px 420px at 100% 0%, rgba(217, 119, 6, 0.05), transparent 60%),
        var(--page);
    color: var(--ink);
    font-family: var(--font-body);
    font-size: 17px;
    line-height: 1.75;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

/* ============ TYPOGRAPHY ============ */
h1, h2, h3, h4 {{
    color: var(--ink);
    font-family: var(--font-display);
    font-weight: 600;
    line-height: 1.2;
    letter-spacing: -0.01em;
}}

h1 {{
    font-size: clamp(2rem, 4.4vw, 3.15rem);
    font-weight: 600;
    font-style: italic;
    margin-bottom: 0.85rem;
    letter-spacing: -0.02em;
}}

h2 {{
    font-family: var(--font-display);
    font-size: clamp(1.5rem, 2.6vw, 2rem);
    font-weight: 600;
    font-style: normal;
    color: var(--ink);
    margin: 2.5rem 0 1.1rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid var(--border);
    position: relative;
}}
h2::after {{
    content: "";
    position: absolute;
    left: 0;
    bottom: -1px;
    width: 56px;
    height: 3px;
    background: var(--accent);
    border-radius: 3px;
}}

h3 {{
    font-size: clamp(1.15rem, 1.9vw, 1.35rem);
    font-weight: 600;
    color: var(--brand-dark);
    margin: 1.8rem 0 0.7rem;
}}

p {{
    margin-bottom: 1.15rem;
    font-size: 1.05rem;
    color: var(--ink-soft);
}}

li {{ margin-bottom: 0.55rem; color: var(--ink-soft); }}

a {{
    color: var(--link);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s ease, color 0.2s ease;
}}
a:hover {{ border-bottom-color: currentColor; }}

strong {{ font-weight: 700; color: var(--ink); }}
em {{ font-style: italic; }}

img {{
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
    object-position: center;
}}

#blog-editable-body img,
#blog-editable-body .editable-blog-image {{
    display: block;
    width: min(100%, 900px);
    max-width: 100%;
    height: auto;
    max-height: min(70vh, 720px);
    object-fit: cover;
    margin: 1.6rem auto;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
}}
#blog-editable-body img[data-blog-source-image="true"] {{ display: none; }}
#blog-editable-body [data-editing="true"] img {{ cursor: default; }}
#blog-editable-body img:not([data-blog-source-image="true"]) {{ cursor: zoom-in; }}

/* ============ LIGHTBOX ============ */
.blog-image-lightbox {{
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(10, 20, 18, 0.94);
    backdrop-filter: blur(6px);
    cursor: zoom-out;
}}
.blog-image-lightbox.open {{ display: flex; }}
.blog-image-lightbox img {{
    width: auto;
    max-width: 96vw;
    max-height: 94vh;
    max-height: 94svh;
    margin: 0;
    object-fit: contain;
    box-shadow: var(--shadow-lg);
    border-radius: var(--radius-sm);
}}
.blog-image-lightbox button {{
    position: absolute;
    top: 0.9rem;
    right: 0.9rem;
    width: 46px;
    height: 46px;
    color: #ffffff;
    font-size: 1.9rem;
    line-height: 1;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.2s ease;
}}
.blog-image-lightbox button:hover {{ background: rgba(255,255,255,0.18); }}

/* ============ NAVBAR ============ */
.navbar {{
    position: sticky;
    top: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem clamp(1rem, 3vw, 2rem);
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: saturate(180%) blur(14px);
    -webkit-backdrop-filter: saturate(180%) blur(14px);
    border-bottom: 1px solid var(--border);
}}
.navbar-brand-row {{
    display: flex;
    align-items: center;
    gap: 14px;
}}
.logo {{
    display: inline-flex;
    align-items: center;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 700;
    font-style: italic;
    letter-spacing: -0.01em;
    color: var(--brand-dark);
    text-decoration: none;
    border-bottom: none;
}}
.logo:hover {{ color: var(--brand); border-bottom: none; }}

/* --- Animated hamburger --- */
.hamburger {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: stretch;
    gap: 5px;
    width: 38px;
    height: 38px;
    padding: 9px;
    border-radius: 10px;
    cursor: pointer;
    background: transparent;
    transition: background 0.2s ease;
}}
.hamburger:hover {{ background: var(--brand-soft); }}
.hamburger span {{
    display: block;
    width: 100%;
    height: 2px;
    border-radius: 2px;
    background: var(--brand-dark);
    transform-origin: center;
    transition:
        transform 0.4s cubic-bezier(0.68, -0.55, 0.27, 1.55),
        opacity 0.22s ease,
        width 0.3s ease,
        background 0.2s ease;
}}
.hamburger.open {{
    background: var(--brand-soft);
}}
.hamburger.open span:nth-child(1) {{
    transform: translateY(7px) rotate(45deg);
    background: var(--brand);
}}
.hamburger.open span:nth-child(2) {{
    opacity: 0;
    transform: scaleX(0.2);
}}
.hamburger.open span:nth-child(3) {{
    transform: translateY(-7px) rotate(-45deg);
    background: var(--brand);
}}

.nav-links {{
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    display: none;
    overflow: hidden;
    max-height: 0;
    background: #ffffff;
    border-bottom: 1px solid transparent;
    box-shadow: none;
    transition: max-height 0.35s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.25s ease,
                border-color 0.25s ease;
}}
.nav-links.open {{
    display: block;
    max-height: 70vh;
    overflow-y: auto;
    border-bottom-color: var(--border);
    box-shadow: var(--shadow-md);
    animation: navSlideDown 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}}
@keyframes navSlideDown {{
    from {{ opacity: 0; transform: translateY(-8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.nav-links a {{ text-decoration: none; border-bottom: none; }}

.dropdown {{ position: relative; }}
.dropdown-menu {{ display: none; width: 100%; list-style: none; background: #ffffff; }}
.dropdown.open .dropdown-menu {{ display: block; }}

#blog-list {{
    width: 100%;
    max-height: 70vh;
    margin: 0 auto;
    overflow-y: auto;
    list-style: none;
    background: #ffffff;
}}
#blog-list li {{ margin: 0; padding: 0.35rem 1.5rem; border-bottom: 1px solid var(--border); }}
#blog-list li:last-child {{ border-bottom: none; }}
#blog-list a {{
    display: block;
    padding: 0.65rem 0;
    color: var(--ink-soft);
    font-size: 0.95rem;
    font-weight: 500;
    transition: color 0.15s ease, padding 0.15s ease;
}}
#blog-list a:hover {{ color: var(--brand-dark); padding-left: 6px; }}

.place-page-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.7rem 1.15rem;
    color: #ffffff;
    font-weight: 600;
    font-size: 0.92rem;
    letter-spacing: 0.01em;
    text-decoration: none;
    border-radius: 999px;
    border-bottom: none;
    background: linear-gradient(135deg, var(--brand-dark), var(--brand));
    box-shadow: 0 6px 18px rgba(15, 118, 110, 0.22);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}}
.place-page-link:hover {{
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(15, 118, 110, 0.28);
    border-bottom: none;
}}
.place-page-link::after {{ content: "→"; font-weight: 500; }}
.place-page-link.place-page-link-nav {{ margin-top: 0; padding: 0.5rem 0.95rem; font-size: 0.85rem; }}

/* ============ LAYOUT ============ */
.blog-shell {{
    width: min(var(--container), 100% - 2rem);
    margin: 1.75rem auto 3rem;
}}

#body-contents {{
    padding: clamp(1.5rem, 3.5vw, 3rem);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
}}

/* ============ HERO ============ */
.blog-hero {{
    margin-bottom: 2rem;
    padding: clamp(1.25rem, 3vw, 2rem) 0 clamp(1rem, 3vw, 1.5rem);
    border-bottom: 1px solid var(--border);
    position: relative;
}}
.blog-kicker {{
    display: inline-block;
    margin-bottom: 1rem;
    padding: 0.35rem 0.85rem;
    color: var(--brand-dark);
    background: var(--brand-soft);
    border-radius: 999px;
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}
.blog-hero h1 {{
    margin-bottom: 1.35rem;
    color: var(--ink);
}}

/* ============ DATE META ============ */
.blog-date-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    padding: 0.85rem 0 1.5rem;
    margin: 0;
    color: var(--ink-muted);
    font-size: 0.88rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}}
.blog-date-meta time {{
    color: var(--ink);
    font-weight: 600;
}}

/* ============ SECTION CONTENT ============ */
.content-section,
.content-block {{ margin-bottom: 2.5rem; }}

.intro-section,
.cta-section {{
    position: relative;
    padding: clamp(1.75rem, 4vw, 2.75rem);
    margin: 2.5rem 0;
    color: #ffffff;
    border-radius: var(--radius-lg);
    background: linear-gradient(135deg, var(--brand-dark) 0%, var(--brand) 55%, #1b8a80 100%);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}}
.intro-section::before,
.cta-section::before {{
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(600px 240px at 100% 100%, rgba(217, 119, 6, 0.18), transparent 60%);
    pointer-events: none;
}}
.intro-section > *,
.cta-section > * {{ position: relative; z-index: 1; }}

.intro-section h2,
.cta-section h2,
.intro-section h1,
.cta-section h1 {{
    color: #ffffff;
    border: 0;
    margin-top: 0;
}}
.intro-section h2::after,
.cta-section h2::after {{ background: var(--accent); }}
.intro-section p,
.cta-section p {{ color: rgba(255, 255, 255, 0.92); font-size: 1.05rem; }}

.highlight-box,
.tip-box,
.mindset-box {{
    padding: 1.35rem 1.5rem;
    margin: 1.75rem 0;
    background: var(--surface-soft);
    border-left: 4px solid var(--brand);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}}
.tip-box {{ border-left-color: var(--accent); background: var(--accent-soft); }}
.mindset-box {{ background: var(--surface-warm); border-left-color: var(--brand); }}

/* ============ GRID IMAGE LAYOUT ============ */
@media (min-width: 769px) {{
    #blog-editable-body section[data-blog-image-layout="true"] {{
        display: grid;
        grid-template-columns: minmax(260px, 0.95fr) minmax(0, 1.05fr);
        column-gap: clamp(1.75rem, 4vw, 3rem);
        row-gap: 0.85rem;
        align-items: start;
        margin: 2rem 0;
    }}
    #blog-editable-body section[data-blog-image-layout="true"] > h2 {{
        grid-column: 1 / -1;
        grid-row: 1;
        margin-bottom: 0.35rem;
    }}
    #blog-editable-body section[data-blog-image-layout="true"] > img {{
        grid-column: 1;
        grid-row: 2;
        width: 100%;
        max-width: 100%;
        height: auto;
        max-height: min(70vh, 720px);
        margin: 0 0 1.25rem;
        object-fit: cover;
        border-radius: var(--radius);
        box-shadow: var(--shadow-sm);
    }}
    #blog-editable-body section[data-blog-image-layout="true"] > img:first-of-type {{ grid-row: 2; }}
    #blog-editable-body section[data-blog-image-layout="true"] > p {{
        grid-column: 2;
        grid-row: 2;
        min-width: 0;
        margin-top: 0;
    }}
    #blog-editable-body section[data-blog-image-layout="true"] > :not(h2):not(img):not(p) {{
        grid-column: 1 / -1;
    }}
}}

/* ============ COLLECTIONS ============ */
#collections-header {{ margin-top: 2.5rem; }}
#collections-header h2 {{ margin-top: 0; }}
#collections-loading {{ color: var(--ink-muted); font-size: 0.95rem; }}

.collection-section,
#dynamic-collections {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.25rem;
    margin-top: 1.35rem;
}}
.collection-item,
.collection-section .collection-card {{
    display: flex;
    flex-direction: column;
    padding: 1.15rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-xs);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}}
.collection-item:hover,
.collection-section .collection-card:hover {{
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
    border-color: var(--border-strong);
}}
.collection-item img,
.collection-section .collection-card img {{
    height: 180px;
    object-fit: cover;
    margin: 0 0 0.9rem;
    border-radius: var(--radius-sm);
}}
.collection-item h4,
.collection-section .collection-card h4 {{
    color: var(--brand-dark);
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}}
.collection-item p,
.collection-section .collection-card p {{
    color: var(--ink-muted);
    font-size: 0.92rem;
    line-height: 1.55;
    margin-bottom: 0.75rem;
}}
.collection-link,
.collection-section .collection-link {{
    display: inline-block;
    align-self: flex-start;
    margin-top: auto;
    padding: 0.55rem 0.95rem;
    color: #ffffff;
    font-weight: 600;
    font-size: 0.88rem;
    text-decoration: none;
    border-bottom: none;
    border-radius: 999px;
    background: var(--brand);
    transition: background 0.15s ease, transform 0.15s ease;
}}
.collection-link:hover {{ background: var(--brand-dark); border-bottom: none; }}

.directions-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    margin-top: 0.5rem;
    color: var(--link);
    font-weight: 600;
    font-size: 0.9rem;
    border-bottom: none;
}}
.directions-link:hover {{ border-bottom: none; text-decoration: underline; }}

/* ============ TOUR GUIDE CARD ============ */
.tour-guide-card {{ max-width: 640px; margin-left: auto; margin-right: auto; text-align: left; }}
.tour-guide-card input {{
    width: 100%;
    margin-top: 0.75rem;
    padding: 0.8rem 0.95rem;
    color: #ffffff;
    font: inherit;
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.12);
}}

/* ============ PROFESSIONAL FOOTER ============ */
.site-footer {{
    position: relative;
    margin-top: 4rem;
    padding: clamp(2.75rem, 5vw, 4rem) clamp(1rem, 3vw, 2rem) 2rem;
    color: rgba(255, 255, 255, 0.78);
    background: linear-gradient(180deg, #0b2420 0%, #0a1a17 100%);
    overflow: hidden;
}}
.site-footer::before {{
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(700px 300px at 12% 0%, rgba(20, 184, 166, 0.12), transparent 60%),
        radial-gradient(700px 300px at 88% 100%, rgba(217, 119, 6, 0.08), transparent 60%);
    pointer-events: none;
}}
.site-footer > * {{ position: relative; z-index: 1; }}

.footer-inner {{ max-width: 1120px; margin: 0 auto; }}

.footer-top {{
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr 1.6fr;
    gap: 2.5rem;
    padding-bottom: 2.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
}}
@media (max-width: 900px) {{
    .footer-top {{ grid-template-columns: 1fr 1fr; gap: 2rem; }}
}}
@media (max-width: 560px) {{
    .footer-top {{ grid-template-columns: 1fr; }}
}}

.footer-brand .footer-logo {{
    display: inline-block;
    font-family: var(--font-display);
    font-size: 1.65rem;
    font-weight: 700;
    font-style: italic;
    letter-spacing: -0.01em;
    color: #ffffff;
    text-decoration: none;
    border-bottom: none;
    margin-bottom: 0.75rem;
}}
.footer-brand .footer-tagline {{
    color: rgba(255, 255, 255, 0.66);
    font-size: 0.95rem;
    line-height: 1.65;
    max-width: 320px;
    margin: 0;
}}

.footer-col h3 {{
    margin: 0 0 1rem;
    color: #ffffff;
    font-family: var(--font-body);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}
.footer-col ul {{
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    gap: 0.55rem;
}}
.footer-col a {{
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.95rem;
    text-decoration: none;
    border-bottom: none;
    transition: color 0.15s ease, transform 0.15s ease;
    display: inline-block;
}}
.footer-col a:hover {{
    color: #ffffff;
    border-bottom: none;
    transform: translateX(2px);
}}

.footer-newsletter p {{
    color: rgba(255, 255, 255, 0.66);
    font-size: 0.95rem;
    margin: 0 0 0.85rem;
    line-height: 1.6;
}}

#subscribeForm {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0;
    margin: 0;
    max-width: 100%;
    background: transparent;
    border: 0;
    backdrop-filter: none;
}}
#subscribeForm input[type="email"],
#subscribeForm input[type="text"] {{
    flex: 1 1 140px;
    min-height: 44px;
    padding: 0.65rem 0.85rem;
    color: #ffffff;
    font: inherit;
    font-size: 0.92rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.06);
    transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}}
#subscribeForm input::placeholder {{ color: rgba(255, 255, 255, 0.45); }}
#subscribeForm input:focus {{
    outline: none;
    border-color: rgba(20, 184, 166, 0.65);
    background: rgba(255, 255, 255, 0.10);
    box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.18);
}}
#subscribeForm button {{
    min-height: 44px;
    padding: 0.65rem 1.15rem;
    color: #0b2420;
    font: inherit;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    border: 0;
    border-radius: var(--radius-sm);
    background: linear-gradient(135deg, #34d399, #10b981);
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
    box-shadow: 0 6px 16px rgba(16, 185, 129, 0.22);
}}
#subscribeForm button:hover {{
    transform: translateY(-1px);
    filter: brightness(1.04);
}}

.footer-share {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1rem;
    padding: 1.75rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
}}
.footer-share p {{
    margin: 0;
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.95rem;
    white-space: nowrap;
}}
#imageform {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin: 0;
    padding: 0;
    background: transparent;
    border: 0;
    backdrop-filter: none;
    flex: 1 1 auto;
}}
#imageform input[type="file"] {{
    flex: 1 1 220px;
    min-height: 40px;
    padding: 0.5rem 0.75rem;
    color: rgba(255, 255, 255, 0.85);
    font: inherit;
    font-size: 0.88rem;
    border: 1px dashed rgba(255, 255, 255, 0.25);
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
}}
#imageform input[type="file"]::file-selector-button {{
    margin-right: 0.6rem;
    padding: 0.4rem 0.75rem;
    color: #ffffff;
    background: rgba(255, 255, 255, 0.10);
    border: 0;
    border-radius: var(--radius-xs);
    cursor: pointer;
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
}}
#imageform button {{
    min-height: 40px;
    padding: 0.55rem 1rem;
    color: #ffffff;
    font: inherit;
    font-size: 0.88rem;
    font-weight: 700;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.08);
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}}
#imageform button:hover {{
    background: rgba(255, 255, 255, 0.14);
    border-color: rgba(255, 255, 255, 0.35);
    transform: translateY(-1px);
}}

.footer-bottom {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem 1.5rem;
    padding-top: 1.75rem;
    color: rgba(255, 255, 255, 0.55);
    font-size: 0.85rem;
}}
.footer-bottom p {{ margin: 0; color: inherit; font-size: inherit; }}
.footer-bottom a {{
    color: rgba(255, 255, 255, 0.78);
    text-decoration: none;
    border-bottom: none;
}}
.footer-bottom a:hover {{ color: #ffffff; border-bottom: none; }}
.footer-meta {{
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
}}
.footer-meta .dot {{
    display: inline-block;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.5;
}}

@media (max-width: 768px) {{
    .footer-share {{ flex-direction: column; align-items: stretch; }}
    #imageform {{ flex-direction: column; align-items: stretch; }}
    #imageform input[type="file"],
    #imageform button {{ width: 100%; }}
    .footer-bottom {{ flex-direction: column; align-items: flex-start; }}
}}

/* ============ EDITOR UI ============ */
#blog-editable-body [data-blog-edit-index],
section[aria-labelledby="faq-heading"] [data-blog-edit-index] {{
    position: relative;
    border-radius: var(--radius-sm);
    transition: background 0.15s ease;
}}
#blog-editable-body [data-blog-edit-index]:hover,
section[aria-labelledby="faq-heading"] [data-blog-edit-index]:hover {{
    background: rgba(15, 118, 110, 0.05);
}}
#blog-editable-body [data-editing="true"],
section[aria-labelledby="faq-heading"] [data-editing="true"] {{
    padding: 0.85rem 1.1rem;
    background: #f7fbfa;
    border: 1px solid var(--brand);
    border-radius: var(--radius-sm);
    outline: none;
    box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.10);
    transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}}

.blog-edit-button {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    margin-left: 0.5rem;
    color: var(--ink-muted);
    font: inherit;
    font-size: 0.9rem;
    border: 1px solid transparent;
    border-radius: 50%;
    cursor: pointer;
    vertical-align: middle;
    background: transparent;
    transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}}
.blog-edit-button:hover {{
    color: #ffffff;
    background: var(--brand);
    border-color: var(--brand);
}}

.blog-paragraph-tools {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: -0.55rem 0 1.25rem;
    padding: 0.75rem;
    border-radius: var(--radius-sm);
    background: var(--surface-soft);
    border: 1px solid var(--border);
}}

.blog-section-actions {{ display: flex; justify-content: flex-end; margin: 1rem 0 1.2rem; }}

.blog-add-section-button {{
    min-height: 42px;
    padding: 0.7rem 1.15rem;
    color: #ffffff;
    font: inherit;
    font-weight: 600;
    font-size: 0.92rem;
    border: 0;
    border-radius: 999px;
    background: linear-gradient(135deg, var(--brand), var(--brand-dark));
    cursor: pointer;
    box-shadow: 0 6px 16px rgba(15, 118, 110, 0.22);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
.blog-add-section-button:hover {{ transform: translateY(-1px); box-shadow: 0 10px 20px rgba(15, 118, 110, 0.28); }}

.blog-add-section-form {{
    display: grid;
    gap: 0.75rem;
    margin: 0 0 1.5rem;
    padding: 1.1rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface-soft);
}}
.blog-add-section-form[hidden] {{ display: none; }}
.blog-add-section-form input,
.blog-add-section-form textarea {{
    width: 100%;
    padding: 0.85rem 0.95rem;
    color: var(--ink);
    font: inherit;
    font-size: 0.95rem;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    background: #ffffff;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
.blog-add-section-form input:focus,
.blog-add-section-form textarea:focus {{
    outline: none;
    border-color: var(--brand);
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}}
.blog-add-section-form textarea {{ min-height: 140px; resize: vertical; }}

.blog-add-section-form-actions {{ display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }}

.blog-add-section-save,
.blog-add-section-cancel {{
    min-height: 40px;
    padding: 0.65rem 1.15rem;
    font: inherit;
    font-weight: 600;
    font-size: 0.9rem;
    border-radius: 999px;
    cursor: pointer;
    transition: transform 0.15s ease;
}}
.blog-add-section-save {{
    color: #ffffff;
    border: 0;
    background: var(--brand-dark);
}}
.blog-add-section-cancel {{
    color: var(--ink);
    border: 1px solid var(--border-strong);
    background: #ffffff;
}}
.blog-add-section-save:hover,
.blog-add-section-cancel:hover {{ transform: translateY(-1px); }}

.blog-paragraph-tools button {{
    min-height: 36px;
    padding: 0.5rem 0.9rem;
    font: inherit;
    font-weight: 600;
    font-size: 0.86rem;
    border-radius: 999px;
    cursor: pointer;
    transition: transform 0.15s ease, filter 0.15s ease;
}}
.blog-paragraph-tools button:hover {{ transform: translateY(-1px); }}

.blog-save-button {{ color: #ffffff; border: 0; background: linear-gradient(135deg, var(--brand), var(--brand-dark)); }}
.blog-cancel-button {{ color: var(--ink); border: 1px solid var(--border-strong); background: #ffffff; }}
.blog-image-upload-button {{ color: var(--brand-dark); border: 1px solid rgba(15, 118, 110, 0.4); background: var(--brand-soft); }}
.blog-url-button {{ color: var(--link); border: 1px solid rgba(29, 78, 216, 0.35); background: #eff6ff; }}

.blog-url-input,
.blog-image-name-input {{
    flex: 1 1 220px;
    min-height: 38px;
    min-width: 200px;
    padding: 0.5rem 0.75rem;
    color: var(--ink);
    font: inherit;
    font-size: 0.9rem;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-xs);
    background: #ffffff;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
.blog-url-input:focus,
.blog-image-name-input:focus {{
    outline: none;
    border-color: var(--link);
    box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12);
}}
.blog-image-name-input:focus {{
    border-color: var(--brand);
    box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}}

.blog-image-upload-button:disabled {{ cursor: wait; opacity: 0.7; }}
.blog-image-upload-input {{ display: none; }}

.blog-edit-status {{ color: var(--ink-muted); font-size: 0.88rem; }}
.blog-edit-status.error {{ color: #b42318; font-weight: 600; }}

/* ============ FAQ ============ */
.faq-section {{ margin: 3rem 0 0; }}

.faq-list {{ display: grid; gap: 0.85rem; }}

.faq-item {{
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--surface);
    overflow: hidden;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}
.faq-item:hover {{ border-color: var(--border-strong); box-shadow: var(--shadow-xs); }}
.faq-item[open] {{ border-color: var(--brand); box-shadow: var(--shadow-sm); }}

.faq-item summary {{
    position: relative;
    padding: 1.05rem 3rem 1.05rem 1.15rem;
    color: var(--ink);
    font-weight: 600;
    font-size: 1.02rem;
    cursor: pointer;
    list-style: none;
    border-radius: var(--radius);
    transition: background 0.15s ease, color 0.15s ease;
}}
.faq-item summary::-webkit-details-marker {{ display: none; }}
.faq-item summary::after {{
    content: "+";
    position: absolute;
    right: 1.15rem;
    top: 50%;
    transform: translateY(-50%);
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--brand-dark);
    font-size: 1.15rem;
    font-weight: 500;
    background: var(--brand-soft);
    border-radius: 50%;
    transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease;
}}
.faq-item[open] summary::after {{
    content: "−";
    background: var(--brand);
    color: #ffffff;
    transform: translateY(-50%) rotate(180deg);
}}
.faq-item summary:hover {{ background: var(--surface-soft); color: var(--brand-dark); }}

.faq-item p {{
    margin: 0;
    padding: 1rem 1.15rem 1.15rem;
    color: var(--ink-muted);
    font-size: 0.98rem;
    line-height: 1.7;
    border-top: 1px solid var(--border);
}}

/* ============ RESPONSIVE ============ */
@media (max-width: 768px) {{
    body {{ font-size: 16px; }}

    .blog-shell {{ width: min(var(--container), 100% - 0.9rem); margin-top: 0.75rem; }}

    #body-contents {{
        padding: 1.25rem;
        border-radius: 0;
        border-left: 0;
        border-right: 0;
        box-shadow: none;
    }}

    #blog-editable-body img,
    #blog-editable-body .editable-blog-image {{
        width: 100%;
        max-width: 100%;
        max-height: calc(100vh - 2rem);
        max-height: calc(100svh - 2rem);
        object-fit: contain;
        border-radius: var(--radius-sm);
    }}

    h1 {{ font-size: clamp(1.75rem, 7vw, 2.3rem); }}
    h2 {{ font-size: clamp(1.3rem, 5vw, 1.6rem); margin-top: 2rem; }}

    .blog-save-button {{ width: 100%; }}

    .navbar {{ padding: 0.75rem 1rem; }}
    .place-page-link.place-page-link-nav {{ display: none; }}

    .blog-paragraph-tools {{ padding: 0.6rem; }}
    .blog-paragraph-tools button {{ width: 100%; }}
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
        <a class="logo" href="/">ParaTara</a>
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

<main class="blog-shell">
    <article id="body-contents">
        <header class="blog-hero">
                <span class="blog-kicker">{category} · {place_name}</span>
                <h1>{title}</h1>
                <a class="place-page-link" href="{place_page_url}">Explore {place_name}</a>
        </header>
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
    {{% if user.is_authenticated %}}
    <div class="blog-section-actions">
        <button type="button" class="blog-add-section-button" id="addBlogSectionButton">Add section</button>
    </div>
    <form class="blog-add-section-form" id="blogAddSectionForm" action="{blog_edit_save_url}" method="post" onsubmit="return false;" hidden>
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
        <input type="text" id="blogAddSectionTitle" maxlength="180" placeholder="Section title">
        <textarea id="blogAddSectionParagraph" placeholder="One paragraph for this section"></textarea>
        <div class="blog-add-section-form-actions">
            <button type="button" class="blog-add-section-save">Save section</button>
            <button type="button" class="blog-add-section-cancel" id="cancelBlogSectionButton">Cancel</button>
            <span class="blog-edit-status" id="blogAddSectionStatus"></span>
        </div>
    </form>
    {{% endif %}}
 </main>
  


 

<script>

var place_name = "{place_name}";
var placename = "{place_name}";
var blogPlaceSlug = "{place_slug}";
var blogTitleSlug = "{title_slug}";
var blogParagraphSaveUrl = "{blog_edit_save_url}";
var blogImageUploadUrl = "{upload_url}";
var blogImagesRequested = false;
var blogCanEdit = false;

try {{
    blogCanEdit = {{{{ user.is_authenticated|yesno:'true,false' }}}};
}} catch (err) {{
    blogCanEdit = false;
}}

// Fisher-Yates shuffle algorithm for proper randomization
function shuffleArray(array) {{
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {{
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }}
    return shuffled;
}}

function prepareNestedSectionImages(root = document) {{
    root.querySelectorAll('img[data-blog-layout-image="true"]').forEach(image => image.remove());
    root.querySelectorAll('#blog-editable-body section[data-blog-image-layout="true"]').forEach(section => {{
        delete section.dataset.blogImageLayout;
    }});
    root.querySelectorAll('#blog-editable-body section > p > img').forEach(sourceImage => {{
        const section = sourceImage.closest('section');
        if (!section) return;

        sourceImage.dataset.blogSourceImage = 'true';
        const layoutImage = sourceImage.cloneNode(true);
        delete layoutImage.dataset.blogSourceImage;
        layoutImage.dataset.blogLayoutImage = 'true';
        layoutImage.contentEditable = 'false';
        section.insertBefore(layoutImage, section.firstChild);
    }});
    root.querySelectorAll('#blog-editable-body section').forEach(section => {{
        if (Array.from(section.children).some(child => child.tagName === 'IMG')) {{
            section.dataset.blogImageLayout = 'true';
        }}
    }});
}}

function setupImageLightbox() {{
    const body = document.getElementById('blog-editable-body');
    if (!body || document.getElementById('blog-image-lightbox')) return;

    const lightbox = document.createElement('div');
    lightbox.id = 'blog-image-lightbox';
    lightbox.className = 'blog-image-lightbox';
    lightbox.setAttribute('role', 'dialog');
    lightbox.setAttribute('aria-modal', 'true');
    lightbox.innerHTML = '<button type="button" aria-label="Close image">&times;</button><img alt="">';
    document.body.appendChild(lightbox);

    const preview = lightbox.querySelector('img');
    const close = () => {{
        lightbox.classList.remove('open');
        document.body.style.overflow = '';
        preview.removeAttribute('src');
    }};

    body.addEventListener('click', event => {{
        const image = event.target.closest('img');
        if (!image || image.dataset.blogSourceImage === 'true' || image.closest('[data-editing="true"]')) return;
        preview.src = image.currentSrc || image.src;
        preview.alt = image.alt || 'Full-size image';
        lightbox.classList.add('open');
        document.body.style.overflow = 'hidden';
    }});
    lightbox.addEventListener('click', close);
    document.addEventListener('keydown', event => {{
        if (event.key === 'Escape' && lightbox.classList.contains('open')) close();
    }});
}}

async function fetchAndInsertImages() {{
    if (blogImagesRequested) return;
    blogImagesRequested = true;

    try {{
        // Fetch images from Django
        const response = await fetch(`/imageapp/images/${{placename}}/`);
        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const data = await response.json();

        const images = Array.isArray(data.images)
            ? data.images.map(img => img.imbbURL).filter(Boolean)
            : [];
        if (!images.length) return;

        // Shuffle array to pick random images using Fisher-Yates
        const shuffled = shuffleArray(images);

        // Find all possible insertion points: content-sections, after h2/h3, after paragraphs
        const bodyContents = document.querySelector("#body-contents");
        if (!bodyContents) return;

        // Get all content sections and other potential insertion points
        const contentSections = Array.from(bodyContents.querySelectorAll('#blog-editable-body section'));
        
        // If no sections found, fall back to direct body-contents
        const insertionPoints = contentSections.length > 0 ? contentSections : [bodyContents];
        
        const maxImages = 3;
        const selectedSections = shuffleArray(insertionPoints).slice(0, Math.min(maxImages, shuffled.length));

        selectedSections.forEach((section, index) => {{
            const imgUrl = shuffled[index];
            const img = document.createElement("img");
            img.src = imgUrl;
            img.loading = "lazy";
            img.decoding = "async";
            img.fetchPriority = "low";
            img.alt = "Blog content image";
            img.className = "dynamic-blog-image";
            section.appendChild(img);
            section.dataset.blogImageLayout = 'true';
        }});

    }} catch (err) {{
        console.error("Error fetching images:", err);
    }}
}}

function scheduleBlogImages() {{
    const body = document.getElementById('blog-editable-body');
    if (!body) return;

    const requestImages = () => {{
        if ('requestIdleCallback' in window) {{
            window.requestIdleCallback(fetchAndInsertImages, {{ timeout: 1500 }});
        }} else {{
            window.setTimeout(fetchAndInsertImages, 250);
        }}
    }};

    if (!('IntersectionObserver' in window)) {{
        requestImages();
        return;
    }}

    const observer = new IntersectionObserver(entries => {{
        if (!entries.some(entry => entry.isIntersecting)) return;
        observer.disconnect();
        requestImages();
    }}, {{ rootMargin: '600px 0px' }});
    observer.observe(body);
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
                        img.decoding = 'async';
                        img.fetchPriority = 'low';
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
	            img.fetchPriority = 'low';
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

    function isHeifImage(file) {{
        const type = (file.type || '').toLowerCase();
        const name = (file.name || '').toLowerCase();
        return type.includes('heic') || type.includes('heif') || /\\.(heic|heif)$/i.test(name);
    }}

    function shouldNormalizeImageUpload(file) {{
        const type = (file.type || '').toLowerCase();
        const name = (file.name || '').toLowerCase();
        if (type === 'image/gif' || type === 'image/svg+xml' || /\\.(gif|svg)$/i.test(name)) {{
            return false;
        }}
        return type.startsWith('image/') || /\\.(heic|heif|jpe?g|png|webp)$/i.test(name);
    }}

    function loadImageFile(file) {{
        return new Promise((resolve, reject) => {{
            const objectUrl = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => {{
                URL.revokeObjectURL(objectUrl);
                resolve(img);
            }};
            img.onerror = () => {{
                URL.revokeObjectURL(objectUrl);
                reject(new Error('This phone image format could not be opened in the browser.'));
            }};
            img.src = objectUrl;
        }});
    }}

    function canvasToBlob(canvas, type, quality) {{
        return new Promise((resolve, reject) => {{
            canvas.toBlob(blob => {{
                if (blob) {{
                    resolve(blob);
                    return;
                }}
                reject(new Error('This browser could not prepare the image for upload.'));
            }}, type, quality);
        }});
    }}

    async function normalizeImageForUpload(file) {{
        if (!file || !shouldNormalizeImageUpload(file)) {{
            return file;
        }}

        const heif = isHeifImage(file);
        if (!window.URL || !document.createElement('canvas').getContext) {{
            if (heif) {{
                throw new Error('Phone camera HEIC/HEIF images need to be converted to JPEG before upload.');
            }}
            return file;
        }}

        try {{
            const img = await loadImageFile(file);
            const maxDimension = 1800;
            const scale = Math.min(1, maxDimension / Math.max(img.naturalWidth || img.width, img.naturalHeight || img.height));
            const width = Math.max(1, Math.round((img.naturalWidth || img.width) * scale));
            const height = Math.max(1, Math.round((img.naturalHeight || img.height) * scale));
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext('2d');
            context.drawImage(img, 0, 0, width, height);

            const blob = await canvasToBlob(canvas, 'image/jpeg', 0.84);
            const originalName = (file.name || 'camera-image').replace(/\\.[^.]+$/, '');
            const normalizedFile = new File([blob], `${{originalName || 'camera-image'}}.jpg`, {{
                type: 'image/jpeg',
                lastModified: Date.now(),
            }});

            if (!heif && file.type === 'image/jpeg' && normalizedFile.size >= file.size) {{
                return file;
            }}
            return normalizedFile;
        }} catch (error) {{
            if (heif) {{
                throw error;
            }}
            console.warn('Image normalization skipped:', error);
            return file;
        }}
    }}

    async function uploadImageIntoSection(paragraph, imageInput, imageNameInput, uploadButton, status) {{
        const file = imageInput.files && imageInput.files[0];
        if (!file) return;

        uploadButton.disabled = true;
        status.textContent = 'Preparing image...';
        status.classList.remove('error');

        let fileToUpload;
        try {{
            fileToUpload = await normalizeImageForUpload(file);
        }} catch (err) {{
            console.error("Error preparing image:", err);
            status.textContent = `Image upload failed: ${{err.message || 'Please choose a JPEG or PNG image.'}}`;
            status.classList.add('error');
            uploadButton.disabled = false;
            imageInput.value = '';
            return;
        }}

        const formData = new FormData();
        formData.append('image', fileToUpload);
        formData.append('image_name', imageNameInput.value.trim());
        formData.append('imageclassID', place_name);
        formData.append('blog_place_slug', blogPlaceSlug);
        formData.append('blog_title_slug', blogTitleSlug);
        formData.append('source', 'blog_inline_editor');

        status.textContent = 'Uploading image...';

        try {{
            const response = await fetch(blogImageUploadUrl, {{
                method: 'POST',
                body: formData,
                headers: {{
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie('csrftoken'),
                }}
            }});

            let data = {{}};
            try {{
                data = await response.json();
            }} catch (jsonError) {{
                if (!response.ok) {{
                    throw new Error(`HTTP ${{response.status}}`);
                }}
                throw jsonError;
            }}
            if (!response.ok || data.status !== 'success' || !data.image_url) {{
                throw new Error(data.error || `HTTP ${{response.status}}`);
            }}

            insertUploadedImageIntoSection(paragraph, data.image_url);
            status.textContent = 'Image inserted. Click Save to keep it.';
            imageNameInput.value = '';
        }} catch (err) {{
            console.error("Error uploading image:", err);
            status.textContent = `Image upload failed: ${{err.message || 'Please try again.'}}`;
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
        button.addEventListener('click', event => {{
            event.preventDefault();
            event.stopPropagation();
            startParagraphEdit(paragraph);
        }});
        paragraph.appendChild(button);
    }}

    function setupEditableParagraphs() {{
        const body = document.getElementById('blog-editable-body');
        if (!body) return;

        body.querySelectorAll('h2, p').forEach((paragraph, index) => {{
            paragraph.dataset.blogEditIndex = String(index);
            paragraph.dataset.blogEditScope = 'article';
            paragraph.dataset.blogEditTag = paragraph.tagName.toLowerCase();
        }});

        body.querySelectorAll('h2[data-blog-edit-index], p[data-blog-edit-index]').forEach(paragraph => {{
            attachParagraphEditButton(paragraph);
        }});

        const faq = document.querySelector('section[aria-labelledby="faq-heading"]');
        if (faq) {{
            faq.querySelectorAll('h2, summary, p').forEach((block, index) => {{
                block.dataset.blogEditIndex = String(index);
                block.dataset.blogEditScope = 'faq';
                block.dataset.blogEditTag = block.tagName.toLowerCase();
                attachParagraphEditButton(block);
            }});
        }}
    }}

    function toggleAddSectionForm(show) {{
        const form = document.getElementById('blogAddSectionForm');
        const button = document.getElementById('addBlogSectionButton');
        const titleInput = document.getElementById('blogAddSectionTitle');
        const paragraphInput = document.getElementById('blogAddSectionParagraph');
        const status = document.getElementById('blogAddSectionStatus');
        if (!form || !button) return;

        form.hidden = !show;
        button.hidden = show;
        if (!show) {{
            form.reset();
            if (status) {{
                status.textContent = '';
                status.classList.remove('error');
            }}
            return;
        }}

        if (titleInput) {{
            titleInput.focus();
        }} else if (paragraphInput) {{
            paragraphInput.focus();
        }}
    }}

    async function saveNewBlogSection() {{
        const form = document.getElementById('blogAddSectionForm');
        const titleInput = document.getElementById('blogAddSectionTitle');
        const paragraphInput = document.getElementById('blogAddSectionParagraph');
        const status = document.getElementById('blogAddSectionStatus');
        const saveButton = form ? form.querySelector('.blog-add-section-save') : null;
        const body = document.getElementById('blog-editable-body');
        if (!form || !titleInput || !paragraphInput || !status || !saveButton || !body) return;

        const title = titleInput.value.trim();
        const paragraphText = paragraphInput.value.replace(/\\s*\\n\\s*/g, ' ').trim();
        const paragraphWrapper = document.createElement('p');
        paragraphWrapper.textContent = paragraphText;

        if (!title) {{
            status.textContent = 'Section title is required.';
            status.classList.add('error');
            titleInput.focus();
            return;
        }}

        if (!paragraphText) {{
            status.textContent = 'Section paragraph is required.';
            status.classList.add('error');
            paragraphInput.focus();
            return;
        }}

        saveButton.disabled = true;
        status.textContent = 'Saving section...';
        status.classList.remove('error');

        try {{
            const response = await fetch(blogParagraphSaveUrl, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken'),
                }},
                body: JSON.stringify({{
                    operation: 'insert_section',
                    place_slug: blogPlaceSlug,
                    title_slug: blogTitleSlug,
                    page_url: window.location.pathname,
                    section_title: title,
                    section_body_html: paragraphWrapper.innerHTML,
                }})
            }});

            const data = await response.json();
            if (!response.ok || !data.ok || !data.inserted_html) {{
                throw new Error(data.error || `HTTP ${{response.status}}`);
            }}

            const temp = document.createElement('div');
            temp.innerHTML = data.inserted_html;
            const section = temp.firstElementChild;
            if (!section) {{
                throw new Error('Saved section did not return valid HTML.');
            }}

            body.appendChild(section);
            setupEditableParagraphs();
            prepareNestedSectionImages(document);
            updateVisibleLastUpdated(data);
            toggleAddSectionForm(false);
        }} catch (err) {{
            console.error('Error adding section:', err);
            status.textContent = `Add section failed: ${{err.message || 'Please try again.'}}`;
            status.classList.add('error');
        }} finally {{
            saveButton.disabled = false;
        }}
    }}

    function setupAddSectionForm() {{
        const form = document.getElementById('blogAddSectionForm');
        const openButton = document.getElementById('addBlogSectionButton');
        const cancelButton = document.getElementById('cancelBlogSectionButton');
        const saveButton = form ? form.querySelector('.blog-add-section-save') : null;
        if (!form || !openButton || !cancelButton || !saveButton) return;

        openButton.addEventListener('click', () => toggleAddSectionForm(true));
        cancelButton.addEventListener('click', () => toggleAddSectionForm(false));
        saveButton.addEventListener('click', () => saveNewBlogSection());
        form.addEventListener('submit', event => {{
            event.preventDefault();
            saveNewBlogSection();
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
        prepareNestedSectionImages(document);
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
        imageUploadInput.accept = 'image/jpeg,image/png,image/webp,image/heic,image/heif,image/*';
        imageUploadInput.className = 'blog-image-upload-input';

        let addUrlButton = document.createElement('button');
        addUrlButton.type = 'button';
        addUrlButton.className = 'blog-url-button';
        addUrlButton.textContent = 'Add URL';

        let putLocationButton = document.createElement('button');
        putLocationButton.type = 'button';
        putLocationButton.className = 'blog-url-button';
        putLocationButton.textContent = 'Put location';

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

        putLocationButton.addEventListener('click', () => {{
            if (!navigator.geolocation) {{
                status.textContent = 'Geolocation is not supported in this browser.';
                status.classList.add('error');
                return;
            }}

            status.textContent = 'Getting your location...';
            status.classList.remove('error');

            navigator.geolocation.getCurrentPosition(
                (position) => {{
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    const mapUrl = `https://www.google.com/maps?q=${{latitude}},${{longitude}}&z=15`;
                    const selectedText = getParagraphSelection(paragraph);
                    const selectedRange = selectedText ? selectedText.range : null;
                    const linkText = (selectedText && selectedText.text.trim()) || 'My location';

                    if (insertLinkIntoSection(paragraph, mapUrl, linkText, selectedRange)) {{
                        status.textContent = 'Location link inserted. Click Save to keep it.';
                        status.classList.remove('error');
                    }} else {{
                        status.textContent = 'Could not add the location link.';
                        status.classList.add('error');
                    }}
                }},
                (error) => {{
                    let message = 'Unable to get your location.';
                    if (error.code === error.PERMISSION_DENIED) {{
                        message = 'Location access was denied.';
                    }} else if (error.code === error.POSITION_UNAVAILABLE) {{
                        message = 'Location is unavailable right now.';
                    }} else if (error.code === error.TIMEOUT) {{
                        message = 'Location request timed out.';
                    }}
                    status.textContent = message;
                    status.classList.add('error');
                }},
                {{
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }}
            );
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
        tools.appendChild(putLocationButton);
        
        
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
                editable_scope: paragraph.dataset.blogEditScope || 'article',
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

    if (blogCanEdit) {{
        setupEditableParagraphs();
        setupAddSectionForm();
    }}
    prepareNestedSectionImages(document);
    setupImageLightbox();
    scheduleBlogImages();
    getBlogLists();
    fetchCollections();

    const yearEl = document.getElementById('footerYear');
    if (yearEl) {{
        yearEl.textContent = new Date().getFullYear();
    }}


    
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
        <div style="margin-top: 1.5rem;">
            <a href="/userProfile/tour-guide/register/" class="collection-link" style="display: inline-block;">Register as Tour Guide</a>
        </div>
    </section>
<footer class="site-footer">
    <div class="footer-inner">
        <div class="footer-top">
            <div class="footer-brand">
                <a class="footer-logo" href="/">ParaTara</a>
                <p class="footer-tagline">Travel guides and local experiences for {place_name} and beyond — written for real trips, not for clicks.</p>
            </div>

            <div class="footer-col">
                <h3>Explore</h3>
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/places/">Places</a></li>
                    <li><a href="/pages/blog/">Blog</a></li>
                    <li><a href="/userProfile/tour-guide/register/">Tour guides</a></li>
                </ul>
            </div>

            <div class="footer-col">
                <h3>Company</h3>
                <ul>
                    <li><a href="/about/">About</a></li>
                    <li><a href="https://foreigntravelsteps.com">Foreign Travel Steps</a></li>
                    <li><a href="mailto:foreigntravelsteps@paratara.com">Contact</a></li>
                    <li><a href="/privacy/">Privacy</a></li>
                </ul>
            </div>

            <div class="footer-col footer-newsletter">
                <h3>Stay in touch</h3>
                <p>New travel guides and local tips, straight to your inbox.</p>
                <form method="post" action="{subscribe_url}" id="subscribeForm">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
                    <input type="email" name="email" placeholder="Your email" required>
                    <input type="text" name="name" placeholder="Name (optional)">
                    <input type="hidden" name="source" value="blog_footer">
                    <button type="submit">Subscribe</button>
                </form>
            </div>
        </div>

        <div class="footer-share">
            <p>Share your {place_name} photos with the community:</p>
            <form id="imageform" action="{upload_url}" method="POST" enctype="multipart/form-data">
                {{% csrf_token %}}
                <input type="hidden" value="{place_name}" name="imageclassID" required>
                <input type="file" name="image" accept="image/*" required>
                <button type="submit">Upload picture</button>
            </form>
        </div>

        <div class="footer-bottom">
            <p>&copy; <span id="footerYear">2026</span> ParaTara. Written by <a href="https://foreigntravelsteps.com">Foreign Travel Steps</a>.</p>
            <p class="footer-meta">
                <span>{category}</span>
                <span class="dot"></span>
                <span>{place_name}</span>
            </p>
        </div>
    </div>
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
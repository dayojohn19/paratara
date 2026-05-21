from django.urls import reverse
from django.middleware.csrf import get_token
import os
from django.utils.text import slugify
from django.conf import settings
import json
import logging
import time
from garden.models import Collection, CollectionGroup
from openai import OpenAI
import ast
from home.models import Places_v2
from apis.models import Blogs
from singlepage2.pyhtmlopt import optimize_file
import re
client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
logger = logging.getLogger(__name__)

# USES call htmlwriter then calls generate_blog_object to save the blog in the database, then generates the html page with SEO optimizations, FAQ schema, and article schema for better search engine visibility. The generated HTML is saved in the appropriate folder structure for serving as a static page on the site.
def generate_blog_object(request, place_name, title, category='Guide', summary='No Summary Provided', text_content=''):
    place = Places_v2.objects.filter(placename__iexact=place_name).first()    
    title_slug = slugify(title)
    print('Word count for blog content:', len(text_content.split()))
    print('type of text_content:', type(text_content))

    place_blog_list = list(place.blog.all())
    for b in place_blog_list:
        if slugify(getattr(b, 'title', '') or '') == title_slug:
            print('place place_')
            return b    
    title = re.sub(r'<a\b[^>]*>(.*?)</a>',r'\1',title,flags=re.IGNORECASE | re.DOTALL)            
    summary = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', summary, flags=re.IGNORECASE | re.DOTALL)
    blog_item = Blogs.objects.create(
        category=category,
        blogplace=place,
        title=title,
        textContent=text_content,
        summarize=summary,

    )
    generate_blog_page(request, place_name, title, text_content, category=category)
    place.blog.add(blog_item)

    current_domain = request.build_absolute_uri('/').rstrip('/')
    place_slug = slugify(getattr(place, 'slug', '') or place.placename)
    title_slug = slugify(title)
    blog_context = f"\n\nAvailable Blogs & Articles:\n📝 {title} - URL: {current_domain}/pages/blog/{place_slug}/{title_slug}/\n"
    print(blog_context)

def generate_blog_page(request, place_name, title, body_text, cover_image_url=None, faq_entries=None, blog_searchable_keys_description=None, category=None):
    print('Generating blog page with title:', title)
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
            # Print token usage
            if hasattr(meta_res, 'usage'):
                print(f"Token usage for meta description: {meta_res.usage}")
            else:
                print("No token usage info for meta description")
            _blog_searchable = meta_res.choices[0].message.content.strip().strip('"')
            print('   ✅ Generated searchable keys description for SEO meta description.')
            return _blog_searchable
        except Exception as e:
            print("META DESCRIPTION ERROR:", e)
            _blog_searchable = f"Discover {title} in {place_name}: Complete travel guide with directions, top activities, entrance fees, insider tips, and best times to visit for an unforgettable experience."
        
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

    if blog_searchable_keys_description:
        print(f"Searchable Keys Description: {blog_searchable_keys_description}")
        time.sleep(0.5)
    logger.info(f"Generating blog page: {title} in {place_name}")
    
    csrf_token = ""
    if request is None:
        logger.warning("Request object is None, CSRF token unavailable")
    else:
        try:
            csrf_token = get_token(request)
        except Exception as e:
            logger.error(f"Error obtaining CSRF token: {e}")
    upload_url = reverse("imageapp:uploadimage")
    subscribe_url = reverse("apis:subscribe_email")
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
    except OSError as e:
        logger.error(f"Failed to create folder {folder_path}: {e}")
        raise

    # The final HTML file location
    file_path = os.path.join(folder_path, f"{title_slug}.html")
    logger.debug(f"Output file path: {file_path}")

    # The canonical full URL on your live site
    canonical_url = f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"

    collections_html = f'''
                        <h2>📱 Local Collections & QR Experiences</h2>
                        <p id="collections-loading">Discover interactive collections nearby. Scan QR codes for memories! Loading...</p>
                        <div id="dynamic-collections" class="collection-section">
                        </div>
                        '''

    # Build FAQ Schema and Article Schema
    try:
        faq_entries = []
        faq_questions = [
    "What is the best time to visit?",
    "How much is the entrance fee or total cost?",
    "How do I get there?",
    "What should I bring for the trip?",
    "Is it safe to visit and what travel tips should I know?"
]
        if category == 'Product':
            print('Category is about product\n')
            faq_questions = [
    "What is the best product to buy in 2026?",
    "Where is the best place to buy it?",
    "How much does it currently cost?",
    "What are the top alternatives or competitors?",
    "Is it worth buying in 2026?"
]

        faq_prompt = f'''Generate 5 common FAQs about "{title}" in "{place_name}".
        
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
        # Print token usage
        if hasattr(res, 'usage'):
            print(f"Token usage for FAQ generation: {res.usage}")
        else:
            print("No token usage info for FAQ generation")
        faq_text = res.choices[0].message.content.strip()
    
        # Try to parse as JSON
        faq_entries = ast.literal_eval(faq_text) if faq_text.startswith('[') else []
        
        # Post-process: ensure all @id fields use the canonical URL
        for idx, entry in enumerate(faq_entries, start=1):
            if isinstance(entry, dict):
                entry["@id"] = f"{canonical_url}#{slugify(entry['name'])}"
                print(f"Processed FAQ entry {idx}: {entry['name']}")
        
        print(f"Generated {len(faq_entries)} FAQ entries")
    except Exception as e:
        print("FAQ GENERATION ERROR:", e)
        faq_entries = []
    
    print(f"   ✅ Generated {len(faq_entries)} FAQ entries")    
    if faq_entries:
        print("FAQ Entries:")
        if isinstance(faq_entries, list):
            for entry in faq_entries:
                print(f"  {entry}")
                time.sleep(0.5)
        else:
            print(f"  {faq_entries}")
            time.sleep(0.5)
        
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
    
    # Article schema for SEO
    article_schema_dict = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": f"{title} — {place_name}",
            "description": blog_searchable_keys_description or f"Discover {title} in {place_name}",
            "image": cover_image_url,
            "author": {
                "@type": "Organization",
                "name": "Foreign Travel Steps",
                "url": "https://foreigntravelsteps.com"
            },
            "datePublished": "2026-05-11",
            "dateModified": "2026-05-11",
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
                                            <!-- Google tag (gtag.js) -->
                                            <script> window.dataLayer = window.dataLayer || []; function gtag(){{dataLayer.push(arguments);}} gtag('js', new Date()); gtag('config', 'G-MH2W7TQEH3'); </script>
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
                                                <meta property="og:description" content="{blog_searchable_keys_description if blog_searchable_keys_description else f'Discover {title} in {place_name}: Complete travel guide with directions, top activities, entrance fees, insider tips, and best times to visit for an unforgettable experience.'}">
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
/* Allow click-to-open on desktop too */
.dropdown.open .dropdown-menu {{
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}}
:root {{
    --surface: #fdfbf5;
    --surface-alt: #f4f0e4;
    --page-bg: #eef1e4;

    --accent: #556b2f;
    --accent-dark: #38461f;
    --accent-light: #8c6b4f;

    --text: #3f3a2f;
    --text-muted: #7a7468;

    --border: #d8d2c3;

    --white: #ffffff;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
    --shadow-md: 0 2px 8px rgba(0,0,0,0.05);
    --shadow-lg: 0 6px 18px rgba(0,0,0,0.06);
}}

* {{ 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    line-height: 1.7;
    color: var(--text);
    background: var(--page-bg);
    font-size: 16px;
}}

h1, h2, h3 {{ 
    font-weight: 700;
    line-height: 1.3;
    color: var(--text);
}}

h1 {{ 
    font-size: 2.5rem;
    margin-bottom: 1rem;
}}

h2 {{ 
    font-size: 1.875rem;
    color: var(--accent);
    margin: 2.5rem 0 1.25rem;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid var(--surface-alt);
}}

h3 {{ 
    font-size: 1.375rem;
    margin: 1.75rem 0 0.875rem;
    color: var(--accent-dark);
}}

p {{
    margin-bottom: 1.25rem;
    color: var(--text);
}}

strong {{
    color: var(--text);
    font-weight: 600;
}}



li {{
    margin-bottom: 0.625rem;
    color: var(--text);
}}

img {{
    width: 100%;
    height: auto;
    border-radius: 12px;
    margin: 1.5rem 0;
}}

/* Navigation */



/* Navbar Base */
.navbar {{

    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    background: #ffffff;

    border-bottom: 1px solid #e2e8f0;
    top: 0;
    z-index: 1000;
}}

.logo {{
    font-size: 1.4rem;
    font-weight: 800;
    color: #2563eb;
}}

/* Links */
.nav-links {{
    list-style: none;
    display: none;
    gap: 2rem;
}}

.nav-links a {{
    text-decoration: none;
    color: #0f172a;
    font-weight: 600;
}}

/* Dropdown */
.dropdown {{
    position: relative;
}}

.dropdown-menu {{
    width: 100vw;
    position: absolute;
    top: 130%;
    left: 0;
    background: #ffffff;
    min-width: 180px;
    list-style: none;
    /* padding: 0.75rem 0; */
    border-radius: 12px;
    box-shadow: none;
    opacity: 0;
    visibility: hidden;
    transform: translateY(10px);
    
}}

.dropdown-menu li a {{
    display: block;
    padding: 1.25rem 1.5rem;
    font-size: 1rem;
    border-radius: 8px;
    
}}

.dropdown-menu li a:hover {{
    background: var(--surface-alt);
    transform: translateX(4px);
}}
/* Main Content */
#body-contents {{
    max-width: 900px;
    margin: 0 auto;
    padding: 3rem 2rem;
    background: var(--white);

}}



@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.intro-section {{
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    color: var(--white);
    padding: 2.5rem;
    border-radius: 14px;
    margin-bottom: 2.5rem;
    border: 1px solid var(--border);

}}

.intro-section h2 {{
    color: var(--white);
    border: none;
    margin-top: 0;
    font-size: 2.25rem;
}}

.intro-section p {{
    color: rgba(255,255,255,0.95);
    font-size: 1.125rem;
    margin-bottom: 0;
}}

.content-section {{
    margin-bottom: 3rem;
}}

/* Info Boxes */
.highlight-box {{
    background: var(--surface-alt);
    border-left: 5px solid var(--accent);
    padding: 1.75rem;
    border-radius: 12px;
    margin: 2rem 0;
    box-shadow: var(--shadow-sm);
}}

.highlight-box h3 {{
    color: var(--accent);
    margin-top: 0;
}}

.highlight-box ul {{
    margin-bottom: 0;
}}

.tip-box {{
    background: var(--surface-alt);
    border-left: 5px solid var(--accent-light);
    padding: 1.75rem;
    border-radius: 12px;
    margin: 2rem 0;
    box-shadow: var(--shadow-sm);
}}

.tip-box p strong {{
    color: var(--accent-light);
}}

.mindset-box {{
    background: linear-gradient(to right, var(--surface), var(--surface-alt));
    padding: 2rem;
    border-radius: 16px;
    margin: 2rem 0;
    border: 2px solid var(--surface-alt);
    box-shadow: var(--shadow-md);
}}

.mindset-box h3 {{
    color: var(--accent);
    margin-top: 1.5rem;
    font-size: 1.25rem;
}}

.mindset-box h3:first-of-type {{
    margin-top: 0;
}}

.mindset-box p {{
    color: var(--text);
    margin-bottom: 0;
}}

/* CTA Section */
.cta-section {{
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    color: var(--white);
    padding: 3rem;
    text-align: center;
    margin: 3rem 0;
    box-shadow: var(--shadow-lg);
}}

.cta-section h2 {{
    color: var(--white);
    border: none;
    margin: 0 0 1rem;
    font-size: 2rem;
}}

.cta-section p {{
    color: rgba(255,255,255,0.95);
    font-size: 1.125rem;
    margin: 0;
}}

/* Blog List Sidebar */
#blog-list {{
    list-style: none;
    max-height: 100vh;
    height: 100vh;
    overflow-y: auto;
    background: var(--white);
}}

#blog-list h1 {{
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    color: var(--primary-blue);
}}

#blog-list li {{
    border-bottom: 1px solid #e2e8f0;
    padding: 1rem 0;
    
}}

#blog-list li:hover {{
    background: var(--bg-light);
}}

#blog-list li:last-child {{ 
    border-bottom: none; 
}}

#blog-list a {{
    text-decoration: none;
    font-size: 0.875rem;
    color: var(--text-muted);
    display: block;
    
}}

#blog-list a:hover {{
    color: var(--accent);
}}

.collection-section .collections-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}}

.collection-section .collection-card {{
    background: #ffffff;

    padding: 1.5rem;

    
}}

.collection-section .collection-card:hover {{
background: #f8fafc;
}}

.collection-section .collection-card img {{
    width: 100%;
    height: 200px;
    object-fit: cover;
    border-radius: 8px;
    margin-bottom: 1rem;
}}

.collection-section .collection-card h4 {{
    font-size: 1.25rem;
    margin-bottom: 0.5rem;
    color: var(--accent);
}}

.collection-section .collection-card p {{
    color: var(--text-muted);
    margin-bottom: 1rem;
    line-height: 1.5;
}}

.collection-section .collection-link {{
    display: inline-block;
    background: linear-gradient(135deg, var(--accent), var(--accent-dark));
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    
}}

.collection-section .collection-link:hover {{
    opacity: 0.9;
}}

/* Footer */
footer {{
    text-align: center;
    padding: 3rem 2rem;
    background: linear-gradient(135deg, var(--accent-dark), var(--accent));
    color: var(--white);
    margin-top: 0;
}}

footer h1 {{
    font-size: 1.75rem;
    margin-bottom: 0.75rem;
    color: var(--white);
}}

footer p {{
    color: rgba(255,255,255,0.9);
    margin-bottom: 0.5rem;
}}

footer a {{ 
    color: var(--white);
    text-decoration: underline;
    
}}

footer a:hover {{
    opacity: 0.8;
}}

footer form {{
    margin-top: 2rem;
    padding-top: 2rem;
    border-top: 1px solid rgba(255,255,255,0.2);
}}

footer button {{
    background: #6a1875;
    color: var(--primary-blue);
    border: none;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 1rem;
    
}}

footer button:hover {{
    transform: translateY(-2px);
}}

footer input[type="file"] {{
    margin-top: 1rem;
}}

/* Hamburger Menu Icon - Friendly & Animated */
.hamburger {{
    display: none;
    flex-direction: column;
    justify-content: space-around;
    width: 30px;
    height: 25px;
    cursor: pointer;
    padding: 5px;
    border-radius: 8px;
    background: transparent;

    
}}

.hamburger:hover {{
    transform: scale(1.05);

}}

.hamburger:active {{
    transform: scale(0.98);
}}

.hamburger span {{
    display: block;
    height: 3px;
    width: 100%;
    background: var(--accent);
    border-radius: 3px;
    
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}}

.hamburger span:nth-child(1) {{
    transform-origin: right center;

}}
.hamburger span:nth-child(2) {{
        margin-top: 4px;
}}

.hamburger span:nth-child(3) {{
    transform-origin: right center;
    margin-top: 4px;
}}

/* X Animation when open */
.hamburger.open span:nth-child(1) {{
    transform: rotate(45deg) translate(5px, 5px);
}}

.hamburger.open span:nth-child(2) {{
    opacity: 0;
    transform: translateX(20px);
}}

.hamburger.open span:nth-child(3) {{
    transform: rotate(-45deg) translate(7px, -6px);
}}

/* Mobile Menu Styles */
.hamburger {{
    display: block;
}}

.dropdown:hover .dropdown-menu {{
    opacity: 1;
    visibility: visible;
    transform: translateY(0);

        
    }}
    .nav-links {{        
        overflow: scroll;

        top: 70px;
        background: #ffffff;
        flex-direction: column;


        display: none;

    }}

    .open {{
        display: block;
    }}

    .dropdown-menu {{
        position: static;
        opacity: 1;
        visibility: visible;
        transform: none;
        box-shadow: none;
        /* padding-left: 1rem; */
        display: none;
    }}

    .dropdown.open .dropdown-menu {{
        display: block;
    }}
    #body-contents {{
        padding: 2rem 1rem;
    }}
/* Mobile Responsive */
@media (max-width: 768px) {{


    h1 {{ font-size: 2rem; }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.125rem; }}

    .intro-section {{
        padding: 2rem 1.5rem;
    }}

    .intro-section h2 {{
        font-size: 1.75rem;
    }}

    .highlight-box,
    .tip-box,
    .mindset-box,
    .cta-section {{
        padding: 1.5rem;
    }}
}}

@media (max-width: 480px) {{
    #body-contents {{
        padding: 1.5rem 1rem;
    }}

    h1 {{ font-size: 1.75rem; }}
    
    .intro-section h2 {{
        font-size: 1.5rem;
    }}

    .cta-section h2 {{
        font-size: 1.5rem;
    }}
}}

@media (min-width: 640px) {{
    #subscribeForm {{
        flex-wrap: nowrap;
    }}

    #subscribeForm input[type="email"] {{
        flex: 2;
    }}

    #subscribeForm input[type="text"] {{
        flex: 1;
    }}

    #subscribeForm button {{
        width: auto;
        white-space: nowrap;
    }}
}}
#subscribeForm {{
    max-width: 420px;
    margin: 0 auto;
    padding: 20px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}}

#subscribeForm input[type="email"],
#subscribeForm input[type="text"] {{
    flex: 1 1 100%;
    padding: 12px 14px;
    border-radius: 8px;
    border: 1px solid #ddd;
    font-size: 15px;
    outline: none;
    
}}

#subscribeForm input::placeholder {{
    color: #aaa;
}}

#subscribeForm input:focus {{
    border-color: #6c63ff;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15);
}}

#subscribeForm button {{
    width: 100%;
    padding: 12px 16px;
    border-radius: 8px;
    border: none;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    background: linear-gradient(135deg, #6c63ff, #4f46e5);
    color: #fff;
    
}}

#subscribeForm button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
    opacity: 0.95;
}}

#subscribeForm button:active {{
    transform: translateY(0);
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.25);
}}
</style>

    
</head>
<body>
                                                                        <!-- Google Tag Manager (noscript) -->
                                                                        <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-MNDNQVRF"
                                                                        height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
                                                                        <!-- End Google Tag Manager (noscript) -->



<nav class="navbar">
    <div style="display: flex; align-items: center; gap: 12px;">
         <div class="hamburger" id="hamburgerBtn" onclick="toggleMenu()">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <div class="logo">ParaTara</div>
    </div>

    <ul class="nav-links" id="navLinks">
        <ul class="" id="blog-list">
        </ul>
    </ul>
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
    {body_text}
  </article>
  


 

<script>

var place_name = "{place_name}";
var placename = "{place_name}";

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
            img.style.maxWidth = "100%";
            img.style.display = "block";
            img.style.margin = "1.5rem 0";
            img.style.borderRadius = "12px";
            img.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";

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
async function fetchData(endpoint, elementId, templateFn, errorMsg) {{
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
            link.textContent = blog.title.replace(/<\/?a[^>]*>/g, '');
            item.appendChild(link);
            fragment.appendChild(item);
        }});
        
        blogList.appendChild(fragment);
    }}, 'No blogs found for this place.');
}}

function fetchCollections() {{
    fetchData('getPlaceCollections/' + placename, 'collections-loading', (data) => {{
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
                directionsLink.style.display = 'inline-flex';
                directionsLink.style.alignItems = 'center';
                directionsLink.style.gap = '0.4em';
                directionsLink.style.marginTop = '0.5rem';
                directionsLink.style.color = '#2563eb';
                directionsLink.style.fontWeight = 'bold';

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
    }}, 'No local collections found nearby.');
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
    <ul class="cta-section">Tour Guide Contacts:
        {{% for tg in tourguide %}}
        <input type="text" value="{{{{ tg.mobile_number }}}}" readonly style="width: 100%; margin-top: 0.5rem; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9rem;">
        {{% endfor %}}
        
    </ul>
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
    <button type="submit"><p>Upload your Picture</p></button>
</form>
</footer>
</body>
</html>
"""
    logger.info(f"Blog page generated successfully: {len(html_content)} bytes")



    print('   ✅ HTML generated: {} characters'.format(len(html_content)))
    folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "singlepage2", "templates", "blogs", place_slug
    )
    print(f'   📁 Blog folder: {folder}')
    os.makedirs(folder, exist_ok=True)

    blog_slug = slugify(title)
    file_path = os.path.join(folder, f"{blog_slug}.html")
    print(f"\n[3.4/5] 💾 Saving blog file...")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"   ✅ Saved to: {file_path}")
# ------------
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        time.sleep(0.5)
        f.flush()
        time.sleep(0.5)
        f.close()


    try:
        print('   ✅ File write complete, starting optimization...')
        optimize_file(file_path)
        print('   ✅ Optimization complete!')
    except Exception as e:
        print('   ⚠️ Optimization failed:', e)  


    return html_content


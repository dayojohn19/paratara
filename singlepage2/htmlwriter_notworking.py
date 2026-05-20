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
    print('TItle before process:   ', title)
    title = re.sub(r'<a\b[^>]*>(.*?)</a>',r'\1',title,flags=re.IGNORECASE | re.DOTALL)            
    summary = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', summary, flags=re.IGNORECASE | re.DOTALL)
    print('Title after process:   ', title)

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
        faq_prompt = f'''Generate 5 common FAQs about "{title}" in "{place_name}".
        
                        Return ONLY a valid JSON array with no markdown formatting. Format:
                        [
                        {{"@type": "Question", "@id": "{canonical_url}#[question name]", "name": "Question?", "acceptedAnswer": {{"@type": "Answer", "text": "Answer text."}}}},
                        ... 
                        ]
                        Use the page URL "{canonical_url}" in all "@id" fields (question name1, question name2, question name3, etc.)
                        Questions should cover: best time to visit, entrance fee/cost, how to get there, what to bring, safety/tips.
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
/* Reset and box-sizing */
* {{
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}}

/* Root variables for colors and shadows */
:root {{
  --primary-blue: #0ea5e9;
  --dark-blue: #0369a1;
  --light-blue: #e0f2fe;
  --accent-orange: #fb923c;
  --light-orange: #fff7ed;
  --text-dark: #1e293b;
  --text-gray: #64748b;
  --bg-light: #f8fafc;
  --white: #ffffff;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.05);
  --shadow-lg: 0 6px 18px rgba(0, 0, 0, 0.06);
}}

/* Body styles */
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
  line-height: 1.7;
  color: var(--text-dark);
  background: var(--bg-light);
  font-size: 16px;
}}

/* Headings */
h1, h2, h3 {{
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-dark);
}}

h1 {{
  font-size: 2.5rem;
  margin-bottom: 1rem;
}}

h2 {{
  font-size: 1.875rem;
  color: var(--primary-blue);
  margin: 2.5rem 0 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 3px solid var(--light-blue);
}}

h3 {{
  font-size: 1.375rem;
  margin: 1.75rem 0 0.875rem;
  color: var(--dark-blue);
}}

/* Paragraphs and text */
p {{
  margin-bottom: 1.25rem;
  color: var(--text-dark);
}}

strong {{
  color: var(--text-dark);
  font-weight: 600;
}}

/* List items */
li {{
  margin-bottom: 0.625rem;
  color: var(--text-dark);
}}

/* Images */
img {{
  width: 100%;
  height: auto;
  border-radius: 12px;
  margin: 1.5rem 0;
  display: block;
}}

/* Container for main content */
#body-contents {{
  max-width: 900px;
  margin: 0 auto;
  padding: 3rem 2rem;
  background: var(--white);
}}

/* Sections */
.content-section {{
  margin-bottom: 3rem;
}}

.intro-section {{
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue));
  color: var(--white);
  padding: 2.5rem;
  border-radius: 14px;
  margin-bottom: 2.5rem;
  border: 1px solid #dfe3ea;
}}

.intro-section h2 {{
  border: none;
  margin-top: 0;
  font-size: 2.25rem;
}}

.intro-section p {{
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.125rem;
  margin-bottom: 0;
}}

/* Info and tip boxes */
.highlight-box,
.tip-box {{
  padding: 1.75rem;
  border-radius: 12px;
  margin: 2rem 0;
  box-shadow: var(--shadow-sm);
}}

.highlight-box {{
  background: var(--light-blue);
  border-left: 5px solid var(--primary-blue);
}}

.highlight-box h3 {{
  color: var(--primary-blue);
  margin-top: 0;
}}

.highlight-box ul {{
  margin-bottom: 0;
}}

.tip-box {{
  background: var(--light-orange);
  border-left: 5px solid var(--accent-orange);
}}

.tip-box p strong {{
  color: var(--accent-orange);
}}

/* Mindset box */
.mindset-box {{
  background: linear-gradient(to right, #f0f9ff, #e0f2fe);
  padding: 2rem;
  border-radius: 16px;
  margin: 2rem 0;
  border: 2px solid var(--light-blue);
  box-shadow: var(--shadow-md);
}}

.mindset-box h3 {{
  color: var(--primary-blue);
  margin-top: 1.5rem;
  font-size: 1.25rem;
}}

.mindset-box h3:first-of-type {{
  margin-top: 0;
}}

.mindset-box p {{
  color: var(--text-dark);
  margin-bottom: 0;
}}

/* CTA Section */
.cta-section {{
  background: linear-gradient(135deg, var(--accent-orange), #f97316);
  color: var(--white);
  padding: 3rem;
  text-align: center;
  margin: 3rem 0;
  box-shadow: var(--shadow-lg);
}}

.cta-section h2 {{
  font-size: 2rem;
  margin: 0 0 1rem;
  border: none;
}}

.cta-section p {{
  font-size: 1.125rem;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
}}

/* Blog list sidebar */
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

#blog-list li:last-child {{
  border-bottom: none;
}}

#blog-list a {{
  text-decoration: none;
  font-size: 0.875rem;
  color: var(--text-gray);
  display: block;
}}

#blog-list a:hover {{
  color: var(--primary-blue);
}}

/* Collections grid and cards */
.collection-section .collections-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}}

.collection-section .collection-card {{
  background: #ffffff;
  padding: 1.5rem;
  border-radius: 8px;
  transition: background 0.3s;
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
  color: var(--primary-blue);
}}

.collection-section .collection-card p {{
  color: var(--text-gray);
  margin-bottom: 1rem;
  line-height: 1.5;
}}

.collection-section .collection-link {{
  display: inline-block;
  background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue));
  color: #fff;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.3s;
}}

.collection-section .collection-link:hover {{
  opacity: 0.9;
}}

/* Footer styles */
footer {{
  text-align: center;
  padding: 3rem 2rem;
  background: linear-gradient(135deg, var(--dark-blue), var(--primary-blue));
  color: var(--white);
}}

footer h1 {{
  font-size: 1.75rem;
  margin-bottom: 0.75rem;
}}

footer p {{
  color: rgba(255, 255, 255, 0.9);
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
  border-top: 1px solid rgba(255, 255, 255, 0.2);
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
  transition: transform 0.2s, box-shadow 0.2s;
}}

footer button:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
}}

footer input[type="file"] {{
  margin-top: 1rem;
}}

/* Hamburger menu styles */
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
  transition: transform 0.2s;
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
  background: var(--primary-blue);
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  transition: all 0.3s;
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

/* Hamburger open state transformations */
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

/* Responsive adjustments for smaller screens */
@media (max-width: 768px) {{
  h1 {{
    font-size: 2rem;
  }}
  h2 {{
    font-size: 1.5rem;
  }}
  h3 {{
    font-size: 1.125rem;
  }}
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
  h1 {{
    font-size: 1.75rem;
  }}
  .intro-section h2 {{
    font-size: 1.5rem;
  }}
  .cta-section h2 {{
    font-size: 1.5rem;
  }}
}}

/* Additional mobile styles for navigation */
@media (max-width: 768px) {{
  .nav-links {{
    display: none;
    flex-direction: column;
    overflow: auto;
    top: 70px;
    background: #fff;
    position: absolute;
    width: 100%;
    border-radius: 0 0 12px 12px;
    box-shadow: var(--shadow-md);
  }}
  .nav-links.open {{
    display: flex;
  }}
  /* Adjust #body-contents padding */
  #body-contents {{
    padding: 2rem 1rem;
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

  <article id="body-contents">
    {collections_html}
    {body_text}
  </article>
                                                          

    <ul class="cta-section">Tour Guide Contacts:
        {{% for tg in tourguide %}}
        <input type="text" value="{{{{ tg.mobile_number }}}}" readonly style="width: 100%; margin-top: 0.5rem; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9rem;">
        {{% endfor %}}
        
    </ul>
  <footer>
  <form method="post" action="{subscribe_url}" id="subscribeForm">
    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
    <input type="email" name="email" placeholder="Your email" required>
    <input type="text" name="name" placeholder="Name (optional)">
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

// Fetch and insert images into content
async function fetchAndInsertImages() {{
  try {{
    const response = await fetch(`/imageapp/images/{{{{ placename }}}}/`);
    const data = await response.json();
    const images = data.images.map(img => img.imbbURL);
    const shuffled = shuffleArray(images);
    const bodyContents = document.querySelector("#body-contents");
    if (!bodyContents) return;

    const sections = Array.from(bodyContents.querySelectorAll('.content-section, .intro-section'));
    const insertionPoints = sections.length > 0 ? sections : [bodyContents];

    let count = 0;
    const maxImages = 3;
    shuffled.slice(0, maxImages).forEach((imgUrl) => {{
      if (count >= maxImages) return;
      count++;
      const img = document.createElement("img");
      Object.assign(img, {{
        src: imgUrl,
        loading: "lazy",
        alt: "Blog content image",
        style: `
          max-width: 100%; display: block; margin: 1.5rem 0; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        `
      }});

      const section = insertionPoints[Math.floor(Math.random() * insertionPoints.length)];
      const children = Array.from(section.children);
      if (children.length > 0) {{
        const randIndex = Math.floor(Math.random() * children.length);
        children[randIndex].insertAdjacentElement('afterend', img);
      }} else {{
        section.appendChild(img);
      }}
    }});
  }} catch (err) {{
    console.error("Error fetching images:", err);
  }}
}}

// Generic fetch function with error handling
async function fetchData(endpoint, elementId, templateFn, errorMsg) {{
  const csrftoken = getCookie('csrftoken');
  try {{
    const response = await fetch(`/apis/${{endpoint}}/`, {{
      headers: {{
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrftoken,
      }}
    }});
    if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
    const data = await response.json();
    if (!data || data.length === 0) {{
      const el = document.getElementById(elementId);
      if (el) el.textContent = errorMsg;
      return;
    }}
    templateFn(data);
  }} catch (err) {{
    console.error(`Error fetching ${{endpoint}}:`, err);
    const el = document.getElementById(elementId);
    if (el) el.textContent = `Failed to load ${{endpoint}}`;
  }}
}}

// Populate blog list
function getBlogLists() {{
  fetchData('getPlaceBlogs/{{{{ placename }}}}', 'blog-list', (data) => {{
    const list = document.getElementById('blog-list');
    const fragment = document.createDocumentFragment();
    data.forEach(blog => {{
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = blog.localurlpath;
      a.textContent = blog.title.replace(/<\/?a[^>]*>/g, '');
      li.appendChild(a);
      fragment.appendChild(li);
    }});
    list.appendChild(fragment);
  }}, 'No blogs found for this place.');
}}

// Populate collections
function fetchCollections() {{
  fetchData('getPlaceCollections/{{{{ placename }}}}', 'collections-loading', (data) => {{
    const container = document.querySelector('#dynamic-collections');
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

      fragment.appendChild(div);
    }});
    container.appendChild(fragment);
    document.getElementById('collections-loading').style.display = 'none';
  }}, 'No local collections found nearby.');
}}

// Helper to get cookie value
function getCookie(name) {{
  const cookies = document.cookie ? document.cookie.split(';') : [];
  for (let cookie of cookies) {{
    cookie = cookie.trim();
    if (cookie.startsWith(`${{name}}=`)) {{
      return decodeURIComponent(cookie.slice(name.length + 1));
    }}
  }}
  return null;
}}

// Initialize event listeners on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {{
  // Submit form
  const form = document.querySelector("#imageform");
  form.addEventListener("submit", (e) => {{
    e.preventDefault();
    const formData = new FormData(form);
    fetch("{{{{ upload_url }}}}", {{
      method: "POST",
      body: formData,
      headers: {{
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCookie('csrftoken'),
      }}
    }})
    .then(res => res.json())
    .then(data => console.log("Success:", data))
    .catch(err => console.error(err));
  }});

  // Fetch images and populate content
  fetchAndInsertImages();
  getBlogLists();
  fetchCollections();

  // Hamburger toggle
  const hamburgerBtn = document.getElementById('hamburgerBtn');
  if (hamburgerBtn) {{
    hamburgerBtn.addEventListener('click', () => {{
      hamburgerBtn.classList.toggle('open');
      document.getElementById('navLinks').classList.toggle('open');
    }});
  }}

  // Close dropdown on outside click
  document.addEventListener('click', (ev) => {{
    const dropdown = document.getElementById('dropdowntoogle');
    if (!dropdown) return;
    if (dropdown.classList.contains('open') && !dropdown.contains(ev.target)) {{
      dropdown.classList.remove('open');
    }}
    // Close on link click inside dropdown
    if (ev.target.tagName === 'A' && dropdown.contains(ev.target)) {{
      dropdown.classList.remove('open');
    }}
  }});

  // Close dropdown on Escape
  document.addEventListener('keydown', (ev) => {{
    if (ev.key === 'Escape') {{
      const dropdown = document.getElementById('dropdowntoogle');
      dropdown && dropdown.classList.remove('open');
    }}
  }});
}});
</script>


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


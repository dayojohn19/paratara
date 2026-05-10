from django.urls import reverse
from django.middleware.csrf import get_token
import os
from django.utils.text import slugify
from django.conf import settings
import json
from garden.models import Collection, CollectionGroup
def generate_blog_page(request,place_name, title, body_text, cover_image_url="/static/images/default-cover.jpg", faq_entries=None):
    print("=== DEBUG: generate_blog_page called ===")
    print(f"  HTML WRITER 2 Running //////")
    print(f"  request: {request} (type: {type(request)})")
    print(f"  place_name: '{place_name}'")
    print(f"  title: '{title}'")
    print(f"  body_text len: {len(body_text) if body_text else 0}")
    print(f"  cover_image_url: '{cover_image_url}'")
    print(f"  faq_entries: {faq_entries} (len: {len(faq_entries) if faq_entries else 0})")
    print("=======================================")
    print("DEBUG: About to get CSRF token...")
    if request is None:
        print("ERROR: request is None! Cannot get CSRF token.")
        csrf_token = ""  # fallback
    else:
        try:
            csrf_token = get_token(request)
            print(f"DEBUG: CSRF token obtained: {csrf_token[:10]}...")
        except Exception as e:
            print(f"ERROR getting CSRF: {e}")
            csrf_token = ""
    print("DEBUG: CSRF step done.")
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
    os.makedirs(folder_path, exist_ok=True)

    # The final HTML file location
    file_path = os.path.join(folder_path, f"{title_slug}.html")
    print(f"DEBUG: Prepared file_path: {file_path}")

    # The canonical full URL on your live site
    canonical_url = f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"

    collections_html = f'''
  <h2>📱 Local Collections & QR Experiences</h2>
<div id="dynamic-collections" class="collection-section">
  <p id="collections-loading">Discover interactive collections nearby. Scan QR codes for memories! Loading...</p>
</div>
    '''

    # ✅ Build FAQ Schema if provided

    faq_schema = f"""
<script type="application/ld+json">
{json.dumps({
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": faq_entries
}, indent=2)}
</script>
"""
        



    # Full SEO HTML Page
    html_content = f"""
    <!DOCTYPE html>
        <html lang="en">
        <head>
                                            {faq_schema}
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

                                                <meta name="description" content="{title} in {place_name}. Learn how to visit, travel tips, prices, and the best time to explore.">

                                                <!-- Canonical -->
                                                <link rel="canonical" href="{canonical_url}">

                                                <!-- Open Graph -->
                                                <meta property="og:title" content="{title} — {place_name}">
                                                <meta property="og:description" content="Travel guide for {place_name}. Includes how to get there, activities, fees, and tips.">
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
    --primary-blue: #0ea5e9;
    --dark-blue: #0369a1;
    --light-blue: #e0f2fe;
    --accent-orange: #fb923c;
    --light-orange: #fff7ed;
    --text-dark: #1e293b;
    --text-gray: #64748b;
    --bg-light: #f8fafc;
    --white: #ffffff;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
    --shadow-lg: 0 10px 30px rgba(0,0,0,0.12);
}}

* {{ 
    box-sizing: border-box; 
    margin: 0; 
    padding: 0; 
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    line-height: 1.7;
    color: var(--text-dark);
    background: var(--bg-light);
    font-size: 16px;
}}

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

p {{
    margin-bottom: 1.25rem;
    color: var(--text-dark);
}}

strong {{
    color: var(--text-dark);
    font-weight: 600;
}}



li {{
    margin-bottom: 0.625rem;
    color: var(--text-dark);
}}

img {{
    width: 100%;
    height: auto;
    border-radius: 12px;
    margin: 1.5rem 0;
    box-shadow: var(--shadow-md);
}}

/* Navigation */



/* Navbar Base */
.navbar {{

    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.5rem;
    background: #ffffff;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    position: sticky;
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
    display: flex;
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
    box-shadow: 0 12px 40px rgba(0,0,0,0.15);
    opacity: 0;
    visibility: hidden;
    transform: translateY(10px);
    transition: all 0.3s ease;
}}

.dropdown-menu li a {{
    display: block;
    padding: 1.25rem 1.5rem;
    font-size: 1rem;
    border-radius: 8px;
    transition: all 0.2s ease;
}}

.dropdown-menu li a:hover {{
    background: var(--light-blue);
    transform: translateX(4px);
}}

.dropdown-menu li a:hover {{
    background: #f1f5f9;
}}
/* Main Content */
#body-contents {{
    max-width: 900px;
    margin: 0 auto;
    padding: 3rem 2rem;
    background: var(--white);
    box-shadow: var(--shadow-md);
}}

.blog-post {{
    animation: fadeIn 0.6s ease-in;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.intro-section {{
    background: linear-gradient(135deg, var(--primary-blue), var(--dark-blue));
    color: var(--white);
    padding: 3rem;
    border-radius: 16px;
    margin-bottom: 3rem;
    box-shadow: var(--shadow-lg);
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
    background: var(--light-blue);
    border-left: 5px solid var(--primary-blue);
    padding: 1.75rem;
    border-radius: 12px;
    margin: 2rem 0;
    box-shadow: var(--shadow-sm);
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
    padding: 1.75rem;
    border-radius: 12px;
    margin: 2rem 0;
    box-shadow: var(--shadow-sm);
}}

.tip-box p strong {{
    color: var(--accent-orange);
}}

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
    transition: background 0.2s ease;
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
    color: var(--text-gray);
    display: block;
    transition: color 0.2s ease;
}}

#blog-list a:hover {{
    color: var(--primary-blue);
}}

.collection-section .collections-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}}

.collection-section .collection-card {{
    background: var(--white);
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: var(--shadow-md);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.collection-section .collection-card:hover {{
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
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
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    transition: opacity 0.2s ease;
}}

.collection-section .collection-link:hover {{
    opacity: 0.9;
}}

/* Footer */
footer {{
    text-align: center;
    padding: 3rem 2rem;
    background: linear-gradient(135deg, var(--dark-blue), var(--primary-blue));
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
    transition: opacity 0.3s ease;
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
    transition: transform 0.2s ease;
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
    background: var(--light-blue);
    box-shadow: var(--shadow-sm);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}

.hamburger:hover {{
    transform: scale(1.05);
    box-shadow: var(--shadow-md);
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
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

    .nav-links.open {{
        display: flex;
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
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
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
    transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
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

async function fetchAndInsertImages() {{
    try {{
        // Fetch images from Django
        const response = await fetch(`/imageapp/images/${{placename}}/`);
        const data = await response.json();

        const images = data.images.map(img => img.imbbURL); // array of URLs

        // Shuffle array to pick random images
        const shuffled = images.sort(() => 0.5 - Math.random());

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












async function getBlogLists() {{
    csrftoken = getCookie('csrftoken');
    
    await fetch(`/apis/getPlaceBlogs/${{placename}}/`, {{
        method: 'GET',
        headers: {{
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrftoken,
        }}
    }})
    .then(res => res.json())
    .then(data => {{
        const blogList = document.getElementById("blog-list");

        if (!data.length) {{
            blogList.innerHTML = "<p>No blogs found for this place.</p>";
            return;
        }}
        data.forEach(blog => {{
            const item = document.createElement("li");
            const link = document.createElement("a");
            link.href = blog.localurlpath;
            link.textContent = blog.title;
            item.appendChild(link);
            blogList.appendChild(item);
        }});

    }})
    .catch(err => {{
        console.error("Error fetching blogs:", err);
    }});
}}

async function fetchCollections() {{
    csrftoken = getCookie('csrftoken');
    
    await fetch(`/apis/getPlaceCollections/${{placename}}/`, {{
        method: 'GET',
        headers: {{
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrftoken,
        }} 
    }})
    .then(res => res.json())
    .then(data => {{
        const collectionsDiv = document.querySelector("#dynamic-collections");
        const loadingP = document.getElementById("collections-loading");

        if (!data || !data.length) {{
            loadingP.textContent = "No local collections found nearby.";
            return;
        }}

        let html = '<div class="collection-card">';
        
        data.forEach(col => {{
            const linkUrl = col.collectionGoogleDriveURL || col.collectionVideo || `/garden/collection/${{col.collectionUniqueID}}/`;
            html += `
                <div class="">
                    ${{col.collectionPicture ? `<img src="${{col.collectionPicture}}" alt="${{col.collectionName}}" loading="lazy">` : ''}}
                    <h4>${{col.name}}</h4>
                    <p>${{col.address ? col.collectionDescription.substring(0, 130) + '...' : ' '}}</p>

                </div>
            `;
        }});
        html += '</div>';

        collectionsDiv.innerHTML = html;
    }})
    .catch(err => {{
        console.error("Error fetching collections:", err);
        document.getElementById("collections-loading").textContent = "Failed to load collections.";
    }});
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
    <input type="text" name="name" placeholder="Name (optional)">
    <input type="hidden" name="source" value="blog_footer">
    <button type="submit">Subscribe</button>
</form>
    <h1>{title}</h1>
  <p><strong>Location:</strong> {place_name}</p>


    <p>Written by <strong><a href="https://foreigntravelsteps.com">Foreign Travel Steps</a></strong> | <a href="#">Contact Me at foreigntravelsteps@paratara.com</a> </p>
  
  





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
    print(f"DEBUG: Generated HTML content (len: {len(html_content)})")
    print("DEBUG: Function complete.")
    return html_content


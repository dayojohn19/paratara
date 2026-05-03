from django.urls import reverse
from django.middleware.csrf import get_token
import os
from django.utils.text import slugify
from django.conf import settings
import json
def generate_blog_page(request,place_name, title, body_text, cover_image_url="/static/images/default-cover.jpg", faq_entries=None):
    csrf_token = get_token(request)  # from django.middleware.csrf import get_token
    upload_url = reverse("imageapp:uploadimage")
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

    # The canonical full URL on your live site
    canonical_url = f"https://www.paratara.com/pages/blog/{place_slug}/{title_slug}/"

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
    html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
                                            {faq_schema}
                                            <script id="Cookiebot" src="https://consent.cookiebot.com/uc.js" data-cbid="f333d02c-4b9d-44bf-90a8-648b9ac87ab2" data-blockingmode="auto" type="text/javascript"></script>
                                            <!-- Google tag (gtag.js) -->
                                            <script> window.dataLayer = window.dataLayer || []; function gtag(){{{{dataLayer.push(arguments);}}}} gtag('js', new Date()); gtag('config', 'G-MH2W7TQEH3'); </script>
                                            <meta name="google-site-verification" content="8jqO-yxHVkp0mIbnh_nvbfA0N21q0QcCR4aDkFbb8rc" />
                                            <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4843007524416588" crossorigin="anonymous"></script>
                                            <meta name="google-adsense-account" content="ca-pub-4843007524416588">

                                            <!-- Google Tag Manager -->
                                            <script>
                                            (function(w,d,s,l,i){{{{ 
                                                w[l] = w[l] || []; 
                                                w[l].push({{{{ 'gtm.start': new Date().getTime(), event: 'gtm.js' }}}}); 
                                                var f = d.getElementsByTagName(s)[0],
                                                    j = d.createElement(s),
                                                    dl = l != 'dataLayer' ? '&l=' + l : ''; 
                                                j.async = true; 
                                                j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl; 
                                                f.parentNode.insertBefore(j, f); 
                                            }}}})(window, document, 'script', 'dataLayer', 'GTM-MNDNQVRF');
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
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
     font-weight: 500;
      color: #555;    
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Inter", Arial, sans-serif;
    line-height: 1.6;
    margin: 0 auto;
    padding:0;
    margin:0;
}}

h1 {{ margin-top: 0; }}
h2 {{ color: #0077b6; margin-bottom: 10px; }}

img {{
    width: 100%;

    margin: 12px 0;
}}

header {{
    background: url('https://riley.ph/wp-content/uploads/2018/07/surigao-del-norte-bucas-grande-club-tara-resort-10-5.jpg') center/cover no-repeat;
    color: white;
    text-align: center;
    padding: 100px 20px;
}}

header h1 {{
    font-size: 3em;
    text-shadow: 2px 2px 5px rgba(0,0,0,0.5);
}}

section {{
    max-width: 800px;
    margin: 50px auto;
    padding: 0 20px;
}}

.steps {{
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}}

.step {{
    margin-bottom: 20px;
    padding-left: 15px;
    border-left: 3px solid #00b4d8;
}}

.step h3 {{ margin-bottom: 8px; }}

#blog-list {{
    padding-left:10px;
    list-style: none;
    max-height: 100vh;
    height: 100vh;

    width:100%;
    overflow:scroll;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
}}

#blog-list li {{
    border-bottom: 1px solid #e0e0e0;
    padding: 1rem 0;
}}

#blog-list li:last-child {{ border-bottom: none; }}

#blog-list a {{

    text-decoration: none;
    font-size: 0.7rem;
    letter-spacing: 0.3px;
    display: block;
    transition: color 0.2s ease;
}}

#blog-list a:focus {{
    color: #0056b3;
    outline: none;
}}

footer {{
    text-align: center;
    padding: 30px;
    background: #0077b6;
    color: white;
    margin-top: 50px;
}}

footer a {{ color: #caf0f8; text-decoration: none; }}

.bucas-card {{
    max-width: 720px;
    margin: 1rem auto;
    padding: 1rem 1.25rem;
    border-radius: 12px;
    box-shadow: 0 6px 22px rgba(0,0,0,0.08);
    background: linear-gradient(180deg, rgba(255,255,255,0.95), #fbffff);
    border: 1px solid rgba(0,0,0,0.04);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial;
}}

.bucas-card h3 {{ margin-bottom: 0.5rem; font-size: 1.125rem; }}

.bucas-desc {{
    margin-bottom: 0.75rem;
    line-height: 1.55;
    font-size: 0.98rem;
    color: #1f2937;
}}

.bucas-features {{
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.4rem;
}}

.bucas-features li {{
    background: rgba(0,160,140,0.05);
    padding: 0.45rem 0.6rem;
    border-radius: 8px;
    font-size: 0.93rem;
}}

.bucas-note {{
    margin-top: 0.6rem;
    font-size: 0.85rem;
    opacity: 0.75;
}}


/* Desktop Menu */
.navbar {{

  display: flex;
justify-content: center;
align-items: center;
padding: 15px 20px;
font-family: system-ui, -apple-system, BlinkMacSystemFont, "Inter", Arial, sans-serif;


}}

.nav-links {{
  list-style: none;
  display: flex;
  gap: 40px;
}}

.nav-links a {{
  color: #555;
  text-decoration: none;
  font-weight: 400;
  letter-spacing: 1px;
  text-transform: uppercase;
  white-space: nowrap;
}}

.arrow {{
  font-size: 12px;
  opacity: 0.7;
  margin-left: 4px;
}}

/* Hamburger (hidden on desktop) */
.hamburger {{
  display: none;
  font-size: 26px;
  cursor: pointer;
  top: 50%;
transform: translateY(-50%);
}}

/* ----------------------------------------- */
/* 📱 Mobile View */
/* ----------------------------------------- */
@media (max-width: 768px) {{

.navbar {{
position: fixed;
top: 0;
left: 0;
width: 100%;
background: white;
z-index: 999;
height:50px;
}}

  .hamburger {{
    display: block;
    position: absolute;
    right: 20px;
    top: 18px;
    top: 50%;
transform: translateY(-50%);
  }}

  .nav-links {{
    position: absolute;
    top: 40px;
    right: 0;
    background: white;
    width: 200px;
    flex-direction: column;
    gap: 20px;
    padding: 20px;
    display: none; /* hidden by default */
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
  }}

  .nav-links.open {{
    display: flex; /* show when open */
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
  <div class="logo"></div>

  <div class="hamburger" onclick="toggleMenu()">
    ☰
  </div>

  <ul class="nav-links" id="blog-list">
    <h1>More Links</h1>
    <li><a href="#">ABOUT <span class="arrow">▼</span></a></li>
    <li><a href="#">BLOG</a></li>
  </ul>
</nav>                                                                        



  <article id="body-contents">
    {body_text}
  </article>
  




<script>

place_name = "{place_name}"
placename = "{place_name}"

async function fetchAndInsertImages() {{
    try {{
        // Fetch images from Django
        const response = await fetch(`/imageapp/images/${{placename}}/`);
        const data = await response.json();

        const images = data.images.map(img => img.imbbURL); // array of URLs

        // Shuffle array to pick random images
        const shuffled = images.sort(() => 0.5 - Math.random());


        const imageContainer = document.querySelector(".steps") || document.querySelector("#body-contents");
        let count = 0;

        shuffled.slice(0, images.length).forEach(imgUrl => {{
            if (count >= 10) return;
            count++;        

            const img = document.createElement("img");

            img.src = imgUrl;
            img.style.maxWidth = "100%";
            img.style.display = "block";
            img.style.margin = "0.5rem 0";

            // Insert at a random child position
            const children = imageContainer.children;
            const randomIndex = Math.floor(Math.random() * (children.length + 1));
            if (randomIndex === children.length) {{
                imageContainer.appendChild(img);
            }} else {{
                imageContainer.insertBefore(img, children[randomIndex]);
            }}
        }});

    }} catch (err) {{
        console.error("Error fetching images:", err);
    }}
}}












async function getBlogLists() {{
    csrftoken = getCookie('csrftoken');
    
    await fetch(`/apis/getPlaceBlogs/Siargao/`, {{
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
        const list = document.createElement("ul");
        data.forEach(blog => {{
            const item = document.createElement("li");
            const link = document.createElement("a");
            link.href = blog.localurlpath;
            link.textContent = blog.title;
            link.target = "_blank";
            item.appendChild(link);
            list.appendChild(item);
        }});
        blogList.appendChild(list);
    }})
    .catch(err => {{
        console.error("Error fetching blogs:", err);
        document.getElementById("blog-list").innerHTML =
            "<p>Error loading blogs.</p>";
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
    const form = document.querySelector("form");
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


    
let bottomTriggered = false;

window.addEventListener("scroll", function() {{
    if (!bottomTriggered && window.innerHeight + window.scrollY >= document.body.offsetHeight) {{
        bottomTriggered = true;
        toggleMenu()


    }}
}});




}});
  

function toggleMenu() {{
  document.getElementById("blog-list").classList.toggle("open");
}}


</script>

  <footer>
    <h1>{title}</h1>
  <p><strong>Location:</strong> {place_name}</p>


    <p>Written by <strong>Foreign Travel Steps</strong> | <a href="#">Contact Me</a> | <a href="#">Instagram</a></p>
  
  





<form action="{upload_url}" method="POST" enctype="multipart/form-data">
    {{% csrf_token %}}

    <input type="hidden" value="{place_name}" name="imageclassID" required>
    <input type="file" name="image" required>
    <button type="submit"><p>Upload your Picture</p></button>
</form>
</footer>
</body>
</html>
"""
    return html_content


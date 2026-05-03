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
:root {{
  --primary: #0066cc;
  --text: #2b2b2b;
  --text-light: #5a5a5a;
  --bg: #fafafa;
  --white: #ffffff;
  --border: #ddd;
}}

* {{ 
  box-sizing: border-box; 
  margin: 0; 
  padding: 0; 
}}

body {{
  font-family: Georgia, 'Times New Roman', serif;
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
  font-size: 18px;
}}

h1, h2, h3, h4, h5, h6 {{
  font-family: -apple-system, system-ui, sans-serif;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text);
  margin-bottom: 0.8rem;
}}

h1 {{ font-size: 2.2rem; }}
h2 {{ 
  font-size: 1.8rem; 
  margin-top: 2rem;
  margin-bottom: 1rem;
}}
h3 {{ 
  font-size: 1.4rem; 
  margin-top: 1.5rem;
}}

p {{
  margin-bottom: 1.2rem;
  color: var(--text-light);
  line-height: 1.7;
}}

img {{
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 1.5rem 0;
}}

header {{
  background: linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)), 
              url('https://riley.ph/wp-content/uploads/2018/07/surigao-del-norte-bucas-grande-club-tara-resort-10-5.jpg') center/cover;
  color: white;
  text-align: center;
  padding: 100px 20px 80px;
}}

header h1 {{
  font-size: clamp(2rem, 4vw, 3rem);
  text-shadow: 0 2px 10px rgba(0,0,0,0.3);
  font-weight: 700;
  color: white;
}}

section {{
  max-width: 750px;
  margin: 40px auto;
  padding: 0 20px;
}}

#body-contents {{
  background: var(--white);
  padding: 2.5rem;
  margin: 2rem auto;
  max-width: 750px;
  border-radius: 4px;
}}

.steps {{
  background: var(--white);
  padding: 2rem;
  margin: 1.5rem 0;
  border: 1px solid var(--border);
  border-radius: 4px;
}}

.step {{
  margin-bottom: 1.5rem;
  padding: 1rem 0 1rem 1.5rem;
  border-left: 3px solid var(--primary);
}}

.step h3 {{ 
  margin-bottom: 0.5rem;
  color: var(--text);
}}

.card {{
  max-width: 750px;
  margin: 2rem auto;
  padding: 2rem;
  border-radius: 4px;
  background: var(--white);
  border: 1px solid var(--border);
}}

.card h3 {{ 
  margin-bottom: 0.8rem;
  color: var(--text);
}}

.description {{
  margin-bottom: 1.2rem;
  line-height: 1.7;
  color: var(--text-light);
}}

ul {{
  list-style: disc;
  padding-left: 1.5rem;
  margin: 1rem 0;
}}

ul li {{
  padding: 0.3rem 0;
  color: var(--text-light);
}}

.note {{
  margin-top: 1rem;
  font-size: 0.95rem;
  color: var(--text-light);
  font-style: italic;
}}

#blog-list {{
  padding: 1.5rem;
  max-height: 100vh;
  overflow-y: auto;
  background: var(--white);
}}

#blog-list h1 {{
  font-size: 1.2rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}}

#blog-list li {{
  border-bottom: 1px solid var(--border);
  padding: 0.8rem 0;
}}

#blog-list li:last-child {{ 
  border-bottom: none; 
}}

#blog-list a {{
  text-decoration: none;
  color: var(--text);
  font-size: 0.95rem;
}}

#blog-list a:hover {{
  color: var(--primary);
}}

.navbar {{
  display: flex;
  justify-content: center;
  padding: 1rem 2rem;
  background: var(--white);
  border-bottom: 1px solid var(--border);
}}

.nav-links {{
  display: flex;
  gap: 2rem;
  list-style: none;
}}

.nav-links a {{
  color: var(--text);
  text-decoration: none;
  font-family: -apple-system, system-ui, sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
}}

.nav-links a:hover {{
  color: var(--primary);
}}

.arrow {{
  font-size: 0.7em;
  margin-left: 4px;
}}

.hamburger {{
  display: none;
  font-size: 24px;
  cursor: pointer;
}}

footer {{
  text-align: center;
  padding: 3rem 2rem;
  background: #f5f5f5;
  margin-top: 3rem;
  border-top: 1px solid var(--border);
}}

footer h1 {{
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}}

footer p {{
  color: var(--text-light);
  margin: 0.5rem 0;
}}

footer a {{ 
  color: var(--primary);
  text-decoration: none;
}}

footer a:hover {{
  text-decoration: underline;
}}

footer form {{
  margin-top: 2rem;
  padding: 1.5rem;
  background: var(--white);
  border-radius: 4px;
  border: 1px solid var(--border);
  display: inline-block;
}}

footer input[type="file"] {{
  margin: 1rem 0;
  padding: 0.5rem;
}}

footer button {{
  background: var(--primary);
  color: white;
  border: none;
  padding: 0.7rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
}}

footer button:hover {{
  opacity: 0.9;
}}

@media (max-width: 768px) {{
  body {{ font-size: 17px; }}
  h1 {{ font-size: 1.8rem; }}
  h2 {{ font-size: 1.5rem; }}
  h3 {{ font-size: 1.2rem; }}

  .navbar {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: var(--white);
    z-index: 999;
    height: 60px;
  }}

  .hamburger {{
    display: block;
    position: absolute;
    right: 1.5rem;
    top: 50%;
    transform: translateY(-50%);
  }}

  .nav-links {{
    position: fixed;
    top: 60px;
    right: -100%;
    background: var(--white);
    width: 250px;
    height: calc(100vh - 60px);
    flex-direction: column;
    gap: 0;
    padding: 1.5rem;
    border-left: 1px solid var(--border);
    transition: right 0.3s;
  }}

  .nav-links.open {{
    right: 0;
  }}

  .nav-links li {{
    width: 100%;
    padding: 0.8rem 0;
  }}

  #body-contents {{
    padding: 1.5rem;
    margin-top: 80px;
  }}

  .card, .steps {{
    padding: 1.5rem;
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

  <div id="blog-list" class="nav-links">
    <h1>More Links</h1>
    <ul>
      <li><a href="/">HOME</a></li>
      <li><a href="#">ABOUT <span class="arrow">▼</span></a></li>
      <li><a href="/pages/blog">BLOG</a></li>
    </ul>
    <div id="blog-list-container"></div>
  </div>
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
        const blogListContainer = document.getElementById("blog-list-container");

        if (!data.length) {{
            blogListContainer.innerHTML = "<p>No blogs found for this place.</p>";
            return;
        }}
        
        const heading = document.createElement("h2");
        heading.textContent = "Related Articles";
        heading.style.fontSize = "1rem";
        heading.style.marginTop = "1.5rem";
        heading.style.paddingTop = "1rem";
        heading.style.borderTop = "1px solid var(--border-color)";
        blogListContainer.appendChild(heading);
        
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
        blogListContainer.appendChild(list);
    }})
    .catch(err => {{
        console.error("Error fetching blogs:", err);
        document.getElementById("blog-list-container").innerHTML =
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


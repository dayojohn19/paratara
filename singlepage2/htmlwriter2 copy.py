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
  --primary-color: #2563eb;
  --primary-dark: #1e40af;
  --secondary-color: #06b6d4;
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --bg-light: #f9fafb;
  --bg-white: #ffffff;
  --border-color: #e5e7eb;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 10px 30px rgba(0,0,0,0.1);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
}}

* {{ 
  box-sizing: border-box; 
  margin: 0; 
  padding: 0; 
}}

body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
  line-height: 1.7;
  color: var(--text-primary);
  background: var(--bg-light);
  font-size: 17px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}

/* Typography */
h1, h2, h3, h4, h5, h6 {{
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
  margin-bottom: 1rem;
}}

h1 {{ 
  font-size: 2.5rem; 
  letter-spacing: -0.02em;
}}

h2 {{ 
  font-size: 2rem; 
  color: var(--primary-color);
  margin-top: 2.5rem;
  margin-bottom: 1.25rem;
}}

h3 {{ 
  font-size: 1.5rem; 
  margin-top: 2rem;
}}

p {{
  margin-bottom: 1.25rem;
  color: var(--text-secondary);
  line-height: 1.8;
}}

img {{
  width: 100%;
  height: auto;
  border-radius: var(--radius-md);
  margin: 1.5rem 0;
  box-shadow: var(--shadow-md);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}}

img:hover {{
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}}

/* Header */
header {{
  background: linear-gradient(135deg, rgba(37,99,235,0.95) 0%, rgba(6,182,212,0.9) 100%), 
              url('https://riley.ph/wp-content/uploads/2018/07/surigao-del-norte-bucas-grande-club-tara-resort-10-5.jpg') center/cover no-repeat;
  color: white;
  text-align: center;
  padding: 120px 20px 100px;
  position: relative;
  overflow: hidden;
}}

header::before {{
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 30% 50%, rgba(255,255,255,0.1) 0%, transparent 60%);
}}

header h1 {{
  font-size: clamp(2rem, 5vw, 3.5rem);
  text-shadow: 0 4px 20px rgba(0,0,0,0.3);
  position: relative;
  z-index: 1;
  letter-spacing: -0.03em;
  font-weight: 800;
}}

/* Main Content */
section {{
  max-width: 820px;
  margin: 60px auto;
  padding: 0 24px;
}}

#body-contents {{
  background: var(--bg-white);
  padding: 3rem 2.5rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  margin: 2rem auto;
  max-width: 820px;
}}

/* Steps & Cards */
.steps {{
  background: var(--bg-white);
  padding: 2rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  transition: box-shadow 0.3s ease;
}}

.steps:hover {{
  box-shadow: var(--shadow-md);
}}

.step {{
  margin-bottom: 2rem;
  padding: 1.5rem;
  padding-left: 2rem;
  border-left: 4px solid var(--primary-color);
  background: linear-gradient(90deg, rgba(37,99,235,0.03) 0%, transparent 100%);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  transition: all 0.3s ease;
}}

.step:hover {{
  border-left-color: var(--secondary-color);
  background: linear-gradient(90deg, rgba(6,182,212,0.05) 0%, transparent 100%);
  transform: translateX(4px);
}}

.step h3 {{ 
  margin-bottom: 0.75rem;
  color: var(--primary-color);
  font-size: 1.25rem;
}}

/* Blog List Sidebar */
#blog-list {{
  padding: 1.5rem;
  list-style: none;
  max-height: 100vh;
  height: 100vh;
  width: 100%;
  overflow-y: auto;
  background: var(--bg-white);
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) transparent;
}}

#blog-list::-webkit-scrollbar {{
  width: 6px;
}}

#blog-list::-webkit-scrollbar-track {{
  background: transparent;
}}

#blog-list::-webkit-scrollbar-thumb {{
  background: var(--border-color);
  border-radius: 10px;
}}

#blog-list h1 {{
  font-size: 1.25rem;
  margin-bottom: 1.5rem;
  color: var(--text-primary);
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--border-color);
}}

#blog-list li {{
  border-bottom: 1px solid var(--border-color);
  padding: 1rem 0;
  transition: background 0.2s ease;
}}

#blog-list li:hover {{
  background: var(--bg-light);
  padding-left: 0.5rem;
  margin-left: -0.5rem;
  border-radius: var(--radius-sm);
}}

#blog-list li:last-child {{ 
  border-bottom: none; 
}}

#blog-list a {{
  text-decoration: none;
  font-size: 0.95rem;
  color: var(--text-secondary);
  display: block;
  transition: color 0.2s ease;
  font-weight: 500;
}}

#blog-list a:hover {{
  color: var(--primary-color);
}}

#blog-list a:focus {{
  color: var(--primary-dark);
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: 4px;
}}

/* Footer */
footer {{
  text-align: center;
  padding: 3rem 2rem;
  background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary-color) 100%);
  color: white;
  margin-top: 4rem;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
}}

footer h1 {{
  font-size: 1.75rem;
  margin-bottom: 0.5rem;
  color: white;
}}

footer p {{
  color: rgba(255,255,255,0.9);
  margin: 0.5rem 0;
}}

footer a {{ 
  color: #fff;
  text-decoration: underline;
  transition: opacity 0.2s ease;
}}

footer a:hover {{
  opacity: 0.8;
}}

footer form {{
  margin-top: 2rem;
  padding: 2rem;
  background: rgba(255,255,255,0.1);
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
  display: inline-block;
}}

footer input[type="file"] {{
  margin: 1rem 0;
  padding: 0.75rem;
  background: white;
  border-radius: var(--radius-sm);
  border: none;
  color: var(--text-primary);
  font-size: 0.95rem;
}}

footer button {{
  background: white;
  color: var(--primary-color);
  border: none;
  padding: 0.875rem 2rem;
  border-radius: var(--radius-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1rem;
  box-shadow: var(--shadow-md);
}}

footer button:hover {{
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  background: var(--bg-light);
}}

footer button:active {{
  transform: translateY(0);
}}

/* Bucas Card */
.bucas-card {{
  max-width: 760px;
  margin: 2rem auto;
  padding: 2rem;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  background: var(--bg-white);
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
}}

.bucas-card:hover {{
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}}

.bucas-card h3 {{ 
  margin-bottom: 1rem;
  font-size: 1.5rem;
  color: var(--primary-color);
}}

.bucas-desc {{
  margin-bottom: 1.5rem;
  line-height: 1.8;
  font-size: 1.05rem;
  color: var(--text-secondary);
}}

.bucas-features {{
  list-style: none;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}}

.bucas-features li {{
  background: linear-gradient(135deg, rgba(37,99,235,0.05) 0%, rgba(6,182,212,0.05) 100%);
  padding: 0.875rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.98rem;
  border-left: 3px solid var(--secondary-color);
  transition: all 0.2s ease;
}}

.bucas-features li:hover {{
  background: linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(6,182,212,0.08) 100%);
  padding-left: 1.25rem;
}}

.bucas-note {{
  margin-top: 1rem;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-style: italic;
}}

/* Navigation */
.navbar {{
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 1rem 2rem;
  background: var(--bg-white);
  box-shadow: var(--shadow-sm);
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
  background: rgba(255,255,255,0.95);
}}

.nav-links {{
  list-style: none;
  display: flex;
  gap: 3rem;
  align-items: center;
}}

.nav-links a {{
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  white-space: nowrap;
  font-size: 0.875rem;
  transition: color 0.2s ease;
  position: relative;
}}

.nav-links a::after {{
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--primary-color);
  transition: width 0.3s ease;
}}

.nav-links a:hover {{
  color: var(--primary-color);
}}

.nav-links a:hover::after {{
  width: 100%;
}}

.arrow {{
  font-size: 10px;
  opacity: 0.6;
  margin-left: 4px;
}}

.hamburger {{
  display: none;
  font-size: 28px;
  cursor: pointer;
  color: var(--text-primary);
  transition: color 0.2s ease;
}}

.hamburger:hover {{
  color: var(--primary-color);
}}

/* Mobile Responsive */
@media (max-width: 768px) {{
  body {{
    font-size: 16px;
  }}

  h1 {{ font-size: 2rem; }}
  h2 {{ font-size: 1.5rem; }}
  h3 {{ font-size: 1.25rem; }}

  .navbar {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    background: rgba(255,255,255,0.98);
    backdrop-filter: blur(20px);
    z-index: 999;
    height: 60px;
    padding: 1rem;
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
    right: -100vw;
    background: var(--bg-white);
    width: 250px;
    height: calc(100vh - 60px);
    flex-direction: column;
    gap: 0;
    padding: 1.5rem;
    box-shadow: -4px 0 20px rgba(0,0,0,0.1);
    transition: right 0.3s ease;
    align-items: flex-start;
  }}

  .nav-links.open {{
    right: 0;
  }}

  .nav-links li {{
    width: 100%;
    padding: 0;
  }}

  .nav-links a {{
    width: 100%;
    padding: 0.875rem 0;
    display: block;
  }}

  #body-contents {{
    padding: 2rem 1.5rem;
    margin-top: 80px;
  }}

  header {{
    padding: 100px 20px 80px;
  }}

  .step {{
    padding: 1rem;
    padding-left: 1.5rem;
  }}

  .bucas-card {{
    padding: 1.5rem;
  }}

  footer {{
    padding: 2rem 1rem;
  }}

  footer form {{
    padding: 1.5rem;
    width: 100%;
  }}
}}

@media (max-width: 480px) {{
  #body-contents {{
    padding: 1.5rem 1rem;
  }}
  
  .steps {{
    padding: 1.25rem;
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


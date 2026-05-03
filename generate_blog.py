import os
import django
from django.conf import settings
from django.test import RequestFactory

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webSchedule.settings')
django.setup()

from apis.models import Blogs
from home.models import Places_v2
from singlepage2.htmlwriter import generate_blog_page

# Create mock request
factory = RequestFactory()
request = factory.get('/')

# Parameters
place_name = "Siargao"
title = "How to Run in Siargao: The Ultimate Guide"
body_text = """<div class="intro-section">
<h2>Discover Running in Siargao</h2>
<p>Siargao Island, famous for its world-class waves, also offers incredible opportunities for runners. Whether you're a seasoned marathoner or just looking to enjoy a leisurely jog, Siargao's diverse terrain and scenic routes make it a runner's paradise.</p>
</div>

<div class="content-section">
<h2>Best Places to Run in Siargao</h2>
<p>Siargao has several excellent locations for running:</p>
<ul>
<li><strong>Cloud 9 Beach:</strong> Run along the soft sand and enjoy ocean views.</li>
<li><strong>Magpupungko Rock Pools:</strong> Scenic trails around the tidal pools.</li>
<li><strong>General Luna Town:</strong> Flat roads perfect for long runs.</li>
</ul>
</div>

<div class="highlight-box">
<h3>Running Tips for Siargao</h3>
<ul>
<li>Run early in the morning to avoid the heat.</li>
<li>Stay hydrated and wear sunscreen.</li>
<li>Respect local customs and the environment.</li>
</ul>
</div>

<div class="cta-section">
<h2>Ready to Run in Siargao?</h2>
<p>Book your trip today and experience the best of Siargao's running trails!</p>
</div>"""

cover_image_url = "/static/images/siargao-running.jpg"
faq_entries = [
    {
        "@type": "Question",
        "name": "When is the best time to run in Siargao?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "The best time is early morning or late afternoon to avoid the intense heat."
        }
    },
    {
        "@type": "Question",
        "name": "What should I bring for running in Siargao?",
        "acceptedAnswer": {
            "@type": "Answer",
            "text": "Bring water, sunscreen, comfortable running shoes, and insect repellent."
        }
    }
]

# Generate HTML
html_content = generate_blog_page(request, place_name, title, body_text, cover_image_url, faq_entries)

# Write to file
from django.utils.text import slugify
place_slug = slugify(place_name)
title_slug = slugify(title)
folder_path = os.path.join(settings.BASE_DIR, "singlepage2", "templates", "blogs", place_slug)
os.makedirs(folder_path, exist_ok=True)
file_path = os.path.join(folder_path, f"{title_slug}.html")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

# Create blog entry in database
place, created = Places_v2.objects.get_or_create(placename=place_name)
blog = Blogs.objects.create(
    blogplace=place,
    title=title,
    category='Guide',
    summarize='Discover the best running routes and tips in Siargao.',
    readtime=5,
    localurlpath=f"/pages/blog/{place_slug}/{title_slug}/"
)
# Add to place's blog list
place.blog.add(blog)

print(f"Blog created at {file_path}")
print(f"Blog entry added to database: {blog}")
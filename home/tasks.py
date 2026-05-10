import base64
import io
import os
import qrcode
import ast
import re

from django.conf import settings
from django.utils.text import slugify

from .models import TouristSpot, Places_v2
from apis.models import Blogs

from webSchedule.utils import upload_to_imgbb
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from singlepage2.htmlwriter import generate_blog_page
from openai import OpenAI

client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')


def process_tourist_spot(spot_id):
    try:
        spot = TouristSpot.objects.get(id=spot_id)
        place = spot.place
        name = spot.name
        touristplacepicture = ''

        # =========================
        # ✅ 1. Generate Description
        # =========================
        if not spot.desc:
            try:
                print(f"Generating description for {name} in {place.placename}...")
                prompt = f"Write a short 1-2 sentence tourist description of {name} in {place.placename}"
                res = client.chat.completions.create(
                    model=settings.GROK_MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100
                )
                spot.desc = res.choices[0].message.content.strip()
                spot.save()
            except Exception as e:
                print("DESC ERROR:", e)

        # =========================
        # ✅ 2. Generate Image
        # =========================
        if not spot.img:
            try:
                from webSchedule.utils import getPlacePhoto
                
                image = getPlacePhoto(None, name)
                if image:
                    url = upload_to_imgbb(image)
                    spot.img = url
                    spot.save()
            except Exception as e:
                print("IMG ERROR:", e)

        # =========================
        # ✅ 3. Generate Blog
        # =========================
        try:
            print(f"Generating blog for {name} in {place.placename}...")
            blog_prompt = f'''Write a COMPLETE travel blog about "{name}" in "{place.placename}".

OUTPUT FORMAT - EXACTLY:
Title: [Catchy blog title max 60 chars]

Then exactly TWO NEWLINES

Then HTML content using EXACT structure and CSS classes:


 Use the provided image URL for the spot if relevant.
Do not use markdown, only HTML. Use emojis in h2, make engaging/informative for tourists, include costs/tips/activities for {name} in {place.placename}.

<article class="blog-post">
  <div class="intro-section">
    <h2>[Engaging intro title with emoji]</h2>
    <p>[Hook paragraph inviting reader]</p>
  </div>

  <div class="content-section">
    <h2>[Section 1 title emoji]</h2>
    <p>[Details]</p>
    <div class="highlight-box">
      <h3>Famous for:</h3>
      <ul><li>✅ ...</li>...</ul>
    </div>
  </div>

  <div class="content-section">
    <h2>💰 Budget Breakdown</h2>
    ...
    <div class="tip-box">
      <p><strong>💡 Tips:</strong></p>
      <ul><li>...</li></ul>
    </div>
  </div>

  <div class="content-section">
    <h2>🤝 How to Get There</h2>
    <p>...</p>
  </div>

  <div class="content-section">
    <h2>💪 Success Mindset</h2>
    <div class="mindset-box">
      <h3>From Fear to Adventure</h3>
      <p>...</p>
      <h3>...</h3>
      <p>...</p>
    </div>
  </div>
  
<div class="mindset-box">
  <h2>⚠️ Safety, Hazards & Local Updates</h2>

  <div class="cta-section">
    <h3>Safety Tips</h3>
    <p>{{ safety_tips }}</p>

    <h3>Hazards to Watch</h3>
    <p>{{ hazards }}</p>

    <h3> Updates</h3>
    <p>{{ latest place specific news incidents and accidents with regard to tourist and updates }} <small>{{date taken}}</small></p>

  </div>
</div>

  <div class="cta-section">
    <h2>Ready to Visit?</h2>
    <p>[Strong CTA]</p>
  </div>
</article>

Use emojis in h2, make engaging/informative for tourists, include costs/tips/activities for {name} in {place.placename}.'''

            res = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": blog_prompt}],
                max_tokens=3000
            )

            full_response = res.choices[0].message.content.strip()

            # Parse title and HTML
            parts = full_response.split('\n\n', 1)
            blog_title = parts[0].replace('Title: ', '').strip() if parts[0].startswith('Title:') else f"Visit {name}"
            blog_content = parts[1] if len(parts) > 1 else full_response

            place_slug = slugify(place.placename)
            blog_slug = slugify(blog_title)
            print(f"Generated blog content for {name}: {blog_content[:100]}...")
            html = generate_blog_page(
                None,
                place_name=place.placename,
                title=blog_title,
                body_text=blog_content,
                cover_image_url=spot.img,
                faq_entries=[]
            )
            print('Generated HTML length:', len(html))

            folder = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "singlepage2", "templates", "blogs", place_slug
            )
            print('Blog folder path:', folder)
            os.makedirs(folder, exist_ok=True)

            file_path = os.path.join(folder, f"{blog_slug}.html")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Blog page saved to {file_path}")
            blog = Blogs.objects.create(
                blogplace=place,
                title=blog_title[:64],
                category="Guide",
                summarize=spot.desc[:140],
                readtime=5,
                localurlpath=f"/pages/blog/{place_slug}/{blog_slug}",
                textContent=blog_content
            )

            place.blog.add(blog)

        except Exception as e:
            print("BLOG ERROR:", e)

        # =========================
        # ✅ 4. Generate QR
        # =========================
        try:
            url = f"https://www.paratara.com/{place.slug}/visit/{spot.slug}/"

            qr = qrcode.make(url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")

            from django.core.files.base import ContentFile

            qr_file = ContentFile(buffer.getvalue())
            qr_file.name = f"{spot.slug}-qr.png"

            qr_url = upload_to_imgbb(qr_file) 
            # file = buffer.getvalue()
            # qr_url = upload_to_imgbb(file)

            spot.qr_code_url = qr_url
            spot.save()

        except Exception as e:
            print("QR ERROR:", e)

        print(f"✅ Finished processing {name}")

    except Exception as e:
        print("TASK ERROR:", e)
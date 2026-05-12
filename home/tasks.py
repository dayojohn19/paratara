import base64
import io
import os
import qrcode

import re

from django.conf import settings
from django.utils.text import slugify

from .models import TouristSpot, Places_v2
from apis.models import Blogs

from webSchedule.utils import upload_to_imgbb
import requests
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from singlepage2.htmlwriter import generate_blog_object
from openai import OpenAI

client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')


def process_creating_blog(request, for_place,blog__title=None,to_title=None):
    try:


        # =========================
        # ✅  Generate Blog
        # =========================
        if to_title is not None:
            print('Creating blog title based on user input:', to_title)
            # First, extract the key topic from natural language input
            extract_prompt = f'''Extract the main topic/subject from this user request: "{to_title}"
            Return ONLY the extracted topic (2-4 words), nothing else.
            determine if its about promotion of a specific place, activity, or event in {for_place.placename} and if so extract that as the topic.'''
            try:
                extract_res = client.chat.completions.create(
                    model=settings.GROK_MODEL_NAME,
                    messages=[{"role": "user", "content": extract_prompt}],
                    max_tokens=50
                )
                topic = extract_res.choices[0].message.content.strip()
                print(f"   📍 Extracted topic: {topic}")
                
                # Now generate an engaging blog title based on the extracted topic
                title_prompt = f'''Generate a single catchy and engaging blog title (max 60 characters) "{topic}" in "{for_place.placename}". 
                Only return the title, nothing else.'''
                title_res = client.chat.completions.create(
                    model=settings.GROK_MODEL_NAME,
                    messages=[{"role": "user", "content": title_prompt}],
                    max_tokens=100
                )
                blog__title = title_res.choices[0].message.content.strip()
                print(f"   ✅ Generated blog title: {blog__title}")
            except Exception as e:
                print(f"   ⚠️ Title generation failed: {e}, using default: {to_title}")
                blog__title = to_title
        print(f"\n[3/5] 📰 Generating blog content...")
        try:
            print(f"Generating blog for {blog__title} in {for_place.placename}...")
            blog_prompt = f'''Write a COMPLETE luxurious blog about "{blog__title}" in "{for_place.placename}".
                OUTPUT FORMAT - EXACTLY:
                Title: [Catchy blog title max 60 chars]
                Then exactly TWO NEWLINES
                Then HTML content using EXACT structure and CSS classes:
                Use the provided image URL for the spot if relevant.
                Do not use markdown, only HTML. Use emojis in h2, make engaging/informative for tourists, include costs/tips/activities for {blog__title} in {for_place.placename}.
                Include content appropriate to the user's request and double check if user is asking for a specific topic/subject and provided a url if so create a simple promotion 
                !important  insert icons, if link is preset add the links, and content relevant to the user's request and {for_place.placename}
                                
                <article class="blog-post">
                  <div class="intro-section">
                    <h2>[Engaging intro title with emoji]</h2>
                    <p>[Summary: Hook paragraph inviting reader and create a story like of being here max of 15 words]</p>
                  </div>
                  <div class="content-section">
                    <h2>[Section 1 title emoji]</h2>
                    <p>[Details]</p>
                    <div class="highlight-box">
                      <h3>Known for:</h3>
                      <ul><li>✅ ...</li>...</ul>
                    </div>
                  </div>
                  <div class="content-section">
                    <h2>[Festivals or event and an icon] </h2>
                    <div>
                    - insert any festivals and events with their dates in {for_place.placename}
                    </div>
                  </div>
                  <div class="content-section">
                    <div>
                    - Reasons to come here in {for_place.placename}
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
                  <div class="mindset-box">
                    <h2>⚠️ Safety, Hazards & Local Updates</h2>
                    <div class="cta-section">
                      <h3>Safety Tips</h3>
                      <p>{{ safety_tips }}</p>
                      <h3>Hazards to Watch</h3>
                      <p>{{ hazards }}</p>
                      <h3> Updates</h3>
                      <p>{{ current year latest place specific news incidents and accidents with regard to tourist and updates }} <small>{{current date taken}}</small></p>
                    </div>
                  </div>
                  <div class="cta-section">
                    <h2>Ready to Visit?</h2>
                    <p>[Strong CTA]</p>
                  </div>
                </article>
                Category: based on user message determine its category from the following 'Guide','Story','Tip and Trick','Explore','Product'
                Use emojis in h2, make engaging/informative for tourists, include costs/tips/activities for {blog__title} in {for_place.placename}.
                '''

            res = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": blog_prompt}],
                max_tokens=4000
            )

            full_response = res.choices[0].message.content.strip()
            usage = res.usage

            print("Prompt tokens:", usage.prompt_tokens)
            print("Completion tokens:", usage.completion_tokens)
            print("Total tokens:", usage.total_tokens)  
            print('-----------------')                              
  
            # Parse title and HTML
            parts = full_response.split('\n\n', 1)
            
            # Extract Title (first line)
            blog_title = parts[0].replace('Title: ', '').strip() if parts[0].startswith('Title:') else f"Visit {blog__title}"
            
            # Extract Category and Summary from the full response
            category_match = re.search(r'Category:\s*([^\n]+)', full_response)
            blog_category = category_match.group(1).strip() if category_match else "Guide"
            
            summary_match = re.search(r'Summary:\s*([^\n]+)', full_response)
            blog_summary = summary_match.group(1).strip() if summary_match else f"Discover {blog__title} in {for_place.placename}"
            # Remove "Summary:" prefix if it accidentally got included
            if blog_summary.startswith('Summary:'):
                blog_summary = blog_summary[8:].strip()
            
            # Extract HTML content (everything after the first double newline)
            blog_content = parts[1] if len(parts) > 1 else full_response
            
            print('Blog Category:', blog_category)
            print('Blog Summary:', blog_summary[:50])
            print('Blog Content:', blog_content[:50])
            print('Blog Title:', blog_title[:50])
            place_slug = slugify(for_place.placename)
            
            print(f"   ✅ Blog title: {blog_title}")
            print(f"   ✅ Content generated: {len(blog_content)} characters")
            
            # =========================
            # Generate Meta Description
            # =========================
            print(f"\n[3.1/5] 🔍 Generating SEO meta description...")
            # meta_description = ''
            # try:
            #     meta_prompt = f'''Create an SEO-friendly meta description for a travel blog titled "{blog_title}" about "{blog__title}" in "{for_place.placename}". 
            #                     with like these keywords: {blog__title}, {for_place.placename}, travel guide, things to do, entrance fee, tips, festivals and best time to visit.
            #                     Keep it under 160 characters and make it enticing for travelers searching online.'''
            #     meta_res = client.chat.completions.create(
            #         model=settings.GROK_MODEL_NAME,
            #         messages=[{"role": "user", "content": meta_prompt}],
            #         max_tokens=160
            #     )
            #     meta_description = meta_res.choices[0].message.content.strip().strip('"')
            # except Exception as e:
            #     print("META DESCRIPTION ERROR:", e)
            #     meta_description = f"Discover {blog__title} in {for_place.placename}: Complete travel guide with directions, top activities, entrance fees, insider tips, and best times to visit for an unforgettable experience."
            
            # print(f"   ✅ Meta description: {meta_description[:60]}...")
            
            # =========================
            # Generate FAQ Entries (for SEO Schema)
            # =========================
            print(f"\n[3.2/5] ❓ Generating FAQ entries...")
            

            
            print(f"\n[3.3/5] 🎨 Generating HTML page...")
            html = generate_blog_object(
                request,
                place_name=for_place.placename,
                title=blog__title,
                text_content=blog_content,
                summary=blog_summary, 
                category=blog_category,
            )
            

            print(f"\n[3.5/5] 🗂️  Creating database entry...")
            # TODO CAN CALL singlepage.views import create_blog_from_user_request()
            # blog = Blogs.objects.create(
            #     blogplace=for_place,
            #     title=blog_title[:64],
            #     category="Guide",
            #     summarize=spot.desc[:140],
            #     readtime=5,
            #     localurlpath=f"/pages/blog/{place_slug}/{blog_slug}",
            #     textContent=blog_content
            # )
            # for_place.blog.add(blog)
            #TODO this can go to singlepage2.views import ensure_blog_in_db() and be called on demand when user clicks blog link, instead of pre-creating all blogs for all places and spots
            from singlepage2.views import ensure_blog_page_and_url
            # ensure_blog_page_and_url(None, blog, for_place, blog_title, blog_content, meta_description, faq_entries)

            print(f"   ✅ Blog entry created in database")
            # ---------==== endtodo

        except Exception as e:
            print("BLOG ERROR:", e)

        # =========================
        # ✅ 4. Generate QR
        # =========================
        print(f"\n[4/5] 🔗 Generating QR code...")
        try:
            print(f"   ⏳ Creating QR code URL...")
            
            
            url = f"https://www.paratara.com/{slugify(for_place)}/visit/{slugify(blog__title)}/"

            qr = qrcode.make(url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")

            from django.core.files.base import ContentFile

            filename = f"{slugify(for_place)}-qr.png"
            qr_path = os.path.join(settings.MEDIA_ROOT, 'qr_codes', filename)
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            
            print(f"   ⏳ Saving QR code to disk...")
            with open(qr_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            qr_url = f"{settings.MEDIA_URL}qr_codes/{filename}"


            print(f"   ✅ QR code saved: {qr_url}")

        except Exception as e:
            print("QR ERROR:", e)

        print(f"\n{'='*60}")
        print(f"✅ COMPLETED: {blog__title}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ TASK ERROR: {e}")
        print(f"{'='*60}\n")
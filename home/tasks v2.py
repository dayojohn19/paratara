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


def process_creating_blog(request, for_place,blog__title=None,to_title=None,create_tourist_spot=False):


    try:
        link_promotion_present = None
        import re
        if to_title is not None:
            if ThereisLink := re.search(r'(https?://\S+)', to_title):

                text = """
                create a blog for https://www.amazon.com/dp/B0CP7SV7XV?pd_rd_w=xjvsm&content-id=abc123
                """
                text = to_title

                # Find the URL
                url_pattern = r'https?://[^\s]+'
                match = re.search(url_pattern, text)

                link = match.group(0) if match else ""

                # Remove the URL from the string
                remaining_text = re.sub(url_pattern, '', text).strip()
                to_title = remaining_text
                link_promotion_present = f'promoting link include this exactly <a href="{link}" target="_blank" class="promotion-link">Check it out here</a>'
                print("Link:", link_promotion_present)
                print("Remaining Text:", remaining_text)

        # =========================
        # ✅  Generate Blog
        # =========================
        if to_title is not None:
            print('Creating blog title based on user input:', to_title)
            extract_prompt = f'''Extract the main topic/subject from this user request: "{to_title}"
            # First, extract the key topic from natural language input
            Return ONLY the extracted topic (2-4 words) 
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
                # title_prompt = f'''Generate a single catchy and engaging blog title (max 60 characters) "{topic}" in "{for_place.placename}". 
                # Only return the title, nothing else.'''
                # title_res = client.chat.completions.create(
                #     model=settings.GROK_MODEL_NAME,
                #     messages=[{"role": "user", "content": title_prompt}],
                #     max_tokens=100
                # )
                # blog__title = title_res.choices[0].message.content.strip()
                blog__title = topic
                print(f"   ✅ Generated blog title: {blog__title}")
            except Exception as e:
                print(f"   ⚠️ Title generation failed: {e}, using default: {to_title}")
                blog__title = to_title
        print(f"\n[3/5] 📰 Generating blog content...")
        blog_title = str(blog__title or '').strip() or f"Blog in {for_place.placename}"
        try:
            print(f"Generating blog for {blog__title} in {for_place.placename}...")

            promotion_instruction = (
                link_promotion_present
                if link_promotion_present
                else "No promotional URL was provided."
            )

            blog_prompt = f'''Create a polished, engaging blog post from this user topic/request:
"{blog__title}"

Local context/place: "{for_place.placename}"
Promotion/link instruction: {promotion_instruction}

IMPORTANT INTENT RULES:
- First understand the real intent of the topic/request. It may be travel, a product promotion, a general lifestyle topic, a local guide, an event, a story, a tip article, or something else.
- Do NOT force every article to be a tourist travel guide.
- If the topic is travel, attractions, restaurants, resorts, activities, events, or visiting "{for_place.placename}", write a useful travel/local guide.
- If the topic promotes a product or includes a promotional URL, write an editorial blog that connects "{for_place.placename}" to the product naturally. For example, show how the product helps with a local activity, trip, lifestyle, climate, family outing, commute, resort stay, beach day, pool day, or everyday need. Mention the product with helpful context, not as spam.
- If the topic is not travel-related, write about the requested subject directly and use "{for_place.placename}" only as a relevant local angle, example, audience context, or setting.
- If the request text includes words like "create a blog about", "write about", or similar instructions, ignore those command words and focus on the actual subject.
- Never invent specific breaking news, official rules, festival dates, prices, or safety alerts. If exact current details are uncertain, say readers should verify official/local sources before going or buying.

RESPONSE FORMAT (EXACTLY):
Title: [Catchy title, max 60 chars]

[HTML content below]

REQUIREMENTS:
- HTML only (no markdown)
- Use CSS classes: blog-post, intro-section, content-section, highlight-box, tip-box, mindset-box, cta-section
- Include emojis in all h2 headings
- Match the audience to the intent: tourists for travel topics, local readers for local/lifestyle topics, shoppers for product topics, and general readers for broad topics
- Be specific, practical, warm, and premium in tone
- Include estimated costs, comparisons, practical tips, activities, use cases, or buying considerations only when relevant to the topic
- If a URL was provided, include the exact link HTML from the promotion/link instruction once, with natural context
- Avoid keyword stuffing and hard-sell language

CONTENT STRUCTURE (must include ALL sections, but adapt headings/content to the intent):
1. Intro Section (150 words max) - Hook the reader with a relevant story or situation
2. What Makes It Worth Reading - Explain the subject, product, place, or idea and why it matters
3. Local Connection - Connect the topic to "{for_place.placename}" in a useful, believable way
4. Best Uses / Things To Do / Key Benefits - Choose the label that fits the topic
5. Practical Breakdown - Costs, budget, time, features, comparisons, or planning details when relevant
6. How To Experience / Use / Choose It - Practical next steps, directions, usage tips, or buying advice
7. Safety, Updates & Smart Tips - Safety, maintenance, local cautions, verification advice, or current-year considerations without inventing facts
8. Call to Action - Strong closing statement that fits the topic

EXTRACT AT END:
Category: [Choose ONE based on intent: 'Guide', 'Story', 'Tip and Trick', 'Explore', 'Product']
Summary: [One-line summary for preview, max 140 chars]

HTML TEMPLATE EXAMPLE:
<article class="blog-post">
  <div class="intro-section">
    <h2>🎯 [Emoji + Title]</h2>
    <p>[Engaging intro paragraph]</p>
  </div>
  <div class="content-section">
    <h2>✨ [Feature Title]</h2>
    <p>[Details and descriptions]</p>
    <div class="highlight-box">
      <h3>Known for:</h3>
      <ul><li>✅ Item 1</li><li>✅ Item 2</li></ul>
    </div>
  </div>
  [Additional sections...]
  <div class="tip-box">
    <p><strong>💡 Pro Tips:</strong></p>
    <ul><li>Tip 1</li><li>Tip 2</li></ul>
  </div>
  <div class="mindset-box">
    <h2>⚠️ Safety & Updates</h2>
    <p>[Safety information and current local news]</p>
  </div>
  <div class="cta-section">
    <h2>🚀 Ready to Visit?</h2>
    <p>[Strong call to action]</p>
  </div>
</article>
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
            import re

            raw_title = parts[0].strip()
            blog_title = re.sub(r'^Title:\s*', '', raw_title, flags=re.IGNORECASE).strip().strip('"')
            blog_title = blog_title or str(blog__title or '').strip() or f"Blog in {for_place.placename}"
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
            blog_content = re.sub(
                r'\s*Category:\s*[^\n]+\s*Summary:\s*[^\n]+\s*$',
                '',
                blog_content,
                flags=re.IGNORECASE | re.DOTALL
            ).strip()
            import re

            # blog_summary = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', blog_summary, flags=re.IGNORECASE)
            # blog_title = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', blog_title, flags=re.IGNORECASE)
            blog_title = re.sub(r'<a\b[^>]*>(.*?)</a>',r'\1',blog_title,flags=re.IGNORECASE | re.DOTALL)            
            blog_summary = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', blog_summary, flags=re.IGNORECASE | re.DOTALL)
            if '<a' in blog_title:
                blog_title += '</a>'
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
                title=blog_title,
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
            
            
            url = f"https://www.paratara.com/{slugify(for_place)}/visit/{slugify(blog_title)}/"
            if create_tourist_spot == True:
                tourist_spot_blog_url = url = f"https://www.paratara.com/pages/blog/{slugify(for_place)}/{slugify(blog_title)}/"
                process_create_tourist_spot(request, tourist_spot_blog_url, blog_summary)
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



def process_create_tourist_spot(request,url, blog_summary):
    print("""

Creating Tourist Spots



""")
    from django.shortcuts import render, get_object_or_404
    from resorts.models import resortItem as ResortItem
    from imageapp.imageuploader import getPlacePhoto
    def get_clean_value(data, key, default=""):
        val = data.get(key, default)

        # If it's a list → take first item
        if isinstance(val, list):
            val = val[0] if val else default

        # If None → return default
        if val is None:
            return default

        # Convert EVERYTHING to string safely
        return str(val).strip()

    data = getattr(request, "POST", request)  # ✅ ALWAYS defined    
    if request.method == "POST":
        name = get_clean_value(data, "name")
        place_id = get_clean_value(data, "place")
        slug = get_clean_value(data, "slug")
        desc = get_clean_value(data, "desc")
        latitude = get_clean_value(data, "latitude")
        longitude = get_clean_value(data, "longitude")
        picture = get_clean_value(data, "picture")
        place = get_object_or_404(Places_v2, id=place_id)

        resort_ids = data.getlist("resortItem")

        if not name or not place_id:
            return render(request, "home/tourist_spot_create.html", {
                "places": Places_v2.objects.all(),
                "resorts": ResortItem.objects.all(),
                "error": "Place and Name are required"
            })

        coords = None
        if latitude and longitude:
            try:
                coords = {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                }
            except:
                pass
# ----------- Processing Spot
        if not desc:
            try:
            #     print(f"   ⏳ Generating description...")
            #     prompt = f"Write a short 1-2 sentence tourist description of {name} in {place.placename}"
            #     res = client.chat.completions.create(
            #         model=settings.GROK_MODEL_NAME,
            #         messages=[{"role": "user", "content": prompt}],
            #         max_tokens=100
            #     )
                # desc = res.choices[0].message.content.strip()
                desc =blog_summary
                # spot.save()
                print(f"   ✅ Description saved")
            except Exception as e:
                print("DESC ERROR:", e)
        else:
            print(f"   ✅ Description already exists")
        if not picture:
            try:
                print(f"   ⏳ Fetching image...")

                from webSchedule.utils import upload_to_imgbb
                
                print('Trying to get Picture')
                image = getPlacePhoto(None, name)
                if image:
                    try:
                        print(f"   ⏳ Uploading image to imgbb...")
                        picture = upload_to_imgbb(image)
                    except:
                        print("     Failed to upload in IMBB saving as url instead")
                        picture = image

                    print("   ✅ Image saved")
                else:
                    print(f"   ⚠️  No image found for {name}")
            except Exception as e:
                print("IMG ERROR:", e)
        else:
            print(f"   ✅ Image already exists")

        # ✅ Create immediately (FAST)

        print('\n\n')
        print('Creating TOURIST SPORT URL',url)
        print('\n\n')
        spot = TouristSpot.objects.create(
            place=place,
            name=name,
            slug=slug,
            desc=desc or "",
            coords=coords,
            img=picture,
            url=url
        )
 
        if not spot.spot_id:
            spot.spot_id = f"SPOT-{spot.id}"
            spot.save()

        if resort_ids:
            resorts = ResortItem.objects.filter(id__in=resort_ids)
            spot.resortItem.set(resorts)

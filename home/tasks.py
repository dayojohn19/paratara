import io
import os
import qrcode

import re

from django.conf import settings
from django.utils.text import slugify

from .models import TouristSpot, Places_v2

from singlepage2.htmlwriter import generate_blog_object


from openai import OpenAI

client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')


BLOG_CATEGORIES = {"Guide", "Story", "Tip and Trick", "Explore", "Product"}


def _strip_anchor_tags(value):
    return re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', str(value or ''), flags=re.IGNORECASE | re.DOTALL).strip()


def _get_place_slug(place):
    value = getattr(place, 'slug', '') or getattr(place, 'placename', '') or str(place or '')
    return slugify(value) or 'place'


def _get_list_value(data, key):
    if hasattr(data, 'getlist'):
        return data.getlist(key)
    if not hasattr(data, 'get'):
        return []
    value = data.get(key, [])
    if value in (None, ''):
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _parse_blog_response(full_response, fallback_title, place_name):
    full_response = (full_response or '').strip()
    parts = re.split(r'\n\s*\n', full_response, maxsplit=1)

    raw_title = parts[0].strip() if parts else ''
    blog_title = re.sub(r'^Title:\s*', '', raw_title, flags=re.IGNORECASE).strip().strip('"')
    if not blog_title or blog_title.lower().startswith('<article'):
        blog_title = fallback_title
    blog_title = _strip_anchor_tags(blog_title) or fallback_title

    category_match = re.search(r'^Category:\s*([^\n]+)', full_response, flags=re.IGNORECASE | re.MULTILINE)
    blog_category = category_match.group(1).strip().strip("'\"") if category_match else "Guide"
    if blog_category not in BLOG_CATEGORIES:
        blog_category = "Guide"

    summary_match = re.search(r'^Summary:\s*([^\n]+)', full_response, flags=re.IGNORECASE | re.MULTILINE)
    blog_summary = summary_match.group(1).strip() if summary_match else f"Discover {fallback_title} in {place_name}"
    blog_summary = _strip_anchor_tags(blog_summary)
    if blog_summary.lower().startswith('summary:'):
        blog_summary = blog_summary[8:].strip()

    blog_content = parts[1] if len(parts) > 1 else full_response
    try:
        if len(blog_content) == 0:
            print('Blog Full response :', full_response[:1000])
            print()
            print(parts[1] if len(parts) > 1 else 'No content section found in response')
            print()            
            print("   ⚠️ No content found after splitting, using full response as content")
            print("   ⚠️ No content found after splitting, using full response as content")
            print("   ⚠️ No content found after splitting, using full response as content")
            print('Blog content before cleaning:', blog_content[:1000])
    except Exception as e:
        pass
    
    blog_content = re.sub(r'^\s*Title:\s*[^\n]+\n+', '', blog_content, flags=re.IGNORECASE).strip()
    for _ in range(2):
        blog_content = re.sub(r'\s*(Category|Summary):\s*[^\n]+\s*$', '', blog_content, flags=re.IGNORECASE).strip()

    return blog_title, blog_content, blog_category, blog_summary[:400]


def process_creating_blog(request, for_place,blog__title=None,to_title=None,create_tourist_spot=False):


    try:
        link_promotion_present = None
        place_name = getattr(for_place, 'placename', str(for_place))
        place_slug = _get_place_slug(for_place)
        if to_title is not None:
            to_title = str(to_title).strip()
            url_pattern = r'https?://[^\s]+'
            match = re.search(url_pattern, to_title)
            if match:
                link = match.group(0)
                to_title = re.sub(url_pattern, '', to_title).strip()
                if not to_title:
                    to_title = str(blog__title or link).strip()
                link_promotion_present = f'promoting link include this exactly <a href="{link}" target="_blank" class="promotion-link">Check it out here</a>'
                print("Link:", link_promotion_present)
                print("Remaining Text:", to_title)

        # =========================
        # ✅  Generate Blog
        # =========================
        if to_title is not None:
            print('Creating blog title based on user input:', to_title)
            extract_prompt = f'''Extract the main topic/subject from this user request: "{to_title}"
            # First, extract the key topic from natural language input
            Return ONLY the extracted topic (2-4 words) 
            determine if its about promotion of a specific place, activity, or event in {place_name} and if so extract that as the topic.'''
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
        blog_title = str(blog__title or '').strip() or f"Blog in {place_name}"
        blog_category = "Guide"
        blog_summary = f"Discover {blog_title} in {place_name}"
        blog_content = ""
        try:
            print(f"Generating blog for {blog__title} in {place_name}...")

            promotion_instruction = (
                link_promotion_present
                if link_promotion_present
                else "No promotional URL was provided."
            )

            blog_prompt = f'''Create a polished, engaging blog post from this user topic/request:
"{blog__title}"

Local context/place: "{place_name}"
Promotion/link instruction: {promotion_instruction}

IMPORTANT INTENT RULES:
- First understand the real intent of the topic/request. It may be travel, a product promotion, a general lifestyle topic, a local guide, an event, a story, a tip article, or something else.
- Do NOT force every article to be a tourist travel guide.
- If the topic is travel, attractions, restaurants, resorts, activities, events, or visiting "{place_name}", write a useful travel/local guide.
- If the topic promotes a product or includes a promotional URL, write an editorial blog that connects "{place_name}" to the product naturally. For example, show how the product helps with a local activity, trip, lifestyle, climate, family outing, commute, resort stay, beach day, pool day, or everyday need. Mention the product with helpful context, not as spam.
- If the topic is not travel-related, write about the requested subject directly and use "{place_name}" only as a relevant local angle, example, audience context, or setting.
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
3. Local Connection - Connect the topic to "{place_name}" in a useful, believable way
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
    <h1>🎯 [Emoji + Title]</h1>
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
    <h1>⚠️ Safety & Updates</h1>
    <p>[Safety information and current local news]</p>
  </div>
  <div class="cta-section">
    <h1>🚀 Ready to Visit?</h1>
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
            usage = getattr(res, "usage", None)
            if usage:
                print("Prompt tokens:", getattr(usage, "prompt_tokens", "n/a"))
                print("Completion tokens:", getattr(usage, "completion_tokens", "n/a"))
                print("Total tokens:", getattr(usage, "total_tokens", "n/a"))
                print('-----------------')
  
            blog_title, blog_content, blog_category, blog_summary = _parse_blog_response(
                full_response,
                fallback_title=blog_title,
                place_name=place_name,
            )
            print('Blog Category:', blog_category) 
            print('Blog Summary:', blog_summary[:50])

            print('Blog Content:', blog_content[:50])
            print('Blog Title:', blog_title[:50])
            
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
                place_name=place_name,
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
            
            
            blog_slug = slugify(blog_title) or 'blog'
            url = f"https://www.paratara.com/{place_slug}/visit/{blog_slug}/"
            created_spot = None
            if create_tourist_spot == True:
                tourist_spot_blog_url = url = f"https://www.paratara.com/pages/blog/{place_slug}/{blog_slug}/"
                created_spot = process_create_tourist_spot(request, tourist_spot_blog_url, blog_summary)
            qr = qrcode.make(url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")

            filename = f"{place_slug}-{blog_slug}-qr.png"
            qr_path = os.path.join(settings.MEDIA_ROOT, 'qr_codes', filename)
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            
            print(f"   ⏳ Saving QR code to disk...")
            with open(qr_path, 'wb') as f:
                f.write(buffer.getvalue())
            
            qr_url = f"{settings.MEDIA_URL}qr_codes/{filename}"

            if created_spot is not None:
                created_spot.qr_code_url = qr_url
                created_spot.save(update_fields=["qr_code_url"])

            print(f"   ✅ QR code saved: {qr_url}")

        except Exception as e:
            print("QR ERROR:", e)

        print(f"\n{'='*60}")
        print(f"✅ COMPLETED: {blog__title}")
        print(f"link: {url}")
        print(f"{'='*60}\n")
        return url

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ TASK ERROR: {e}")
        print(f"{'='*60}\n")



def process_create_tourist_spot(request,url, blog_summary):
    print("""

Creating Tourist Spots



""")
    from django.shortcuts import render
    from resorts.models import resortItem as ResortItem
    from imageapp.imageuploader import getPlacePhoto

    def render_error(message):
        print(message)
        if hasattr(request, "META"):
            return render(request, "home/tourist_spot_create.html", {
                "places": Places_v2.objects.all(),
                "resorts": ResortItem.objects.all(),
                "error": message
            })
        return None

    def get_clean_value(data, key, default=""):
        if not hasattr(data, "get"):
            return default
        val = data.get(key, default)

        # If it's a list → take first item
        if isinstance(val, list):
            val = val[0] if val else default

        # If None → return default
        if val is None:
            return default

        # Convert EVERYTHING to string safely
        return str(val).strip()

    data = getattr(request, "POST", request) or {}
    if getattr(request, "method", "POST") == "POST":
        name = get_clean_value(data, "name")
        place_id = get_clean_value(data, "place")
        slug = get_clean_value(data, "slug")
        desc = get_clean_value(data, "desc")
        latitude = get_clean_value(data, "latitude")
        longitude = get_clean_value(data, "longitude")
        picture = get_clean_value(data, "picture")

        resort_ids = _get_list_value(data, "resortItem")

        if not name or not place_id:
            return render_error("Place and Name are required")

        place = Places_v2.objects.filter(id=place_id).first()
        if not place:
            return render_error("Place was not found")

        coords = None
        if latitude and longitude:
            try:
                coords = {
                    "latitude": float(latitude),
                    "longitude": float(longitude)
                }
            except (TypeError, ValueError):
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
                desc = blog_summary
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
        print('Creating TOURIST SPOT URL', url)
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

        return spot

    return None

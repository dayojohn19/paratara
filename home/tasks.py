import io
import os
import qrcode

import re

from django.conf import settings
from django.utils.text import slugify

from .models import TouristSpot, Places_v2

from singlepage2.blog_prompt import build_blog_prompt
from singlepage2.htmlwriter import generate_blog_object


client = settings.GROK_CLIENT


BLOG_CATEGORIES = {"Guide", "Story", "Tip and Trick", "Explore", "Product"}
BLOG_CATEGORY_ALIASES = {
    "guide": "Guide",
    "travel guide": "Guide",
    "local guide": "Guide",
    "story": "Story",
    "personal story": "Story",
    "experience": "Story",
    "tip": "Tip and Trick",
    "tips": "Tip and Trick",
    "tips and tricks": "Tip and Trick",
    "tip and tricks": "Tip and Trick",
    "tip & trick": "Tip and Trick",
    "tip & tricks": "Tip and Trick",
    "how to": "Tip and Trick",
    "explore": "Explore",
    "things to do": "Explore",
    "activity": "Explore",
    "activities": "Explore",
    "event": "Explore",
    "events": "Explore",
    "product": "Product",
    "product review": "Product",
    "buying guide": "Product",
    "shopping": "Product",
    "promotion": "Product",
}
TITLE_LABELS = ("Title", "Blog Title", "blog_title")
CATEGORY_LABELS = ("Category", "Blog Category", "blog_category", "BlogCategory")
SUMMARY_LABELS = ("Summary", "Blog Summary", "blog_summary", "BlogSummary", "Summarize", "Description")


def _strip_anchor_tags(value):
    return re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', str(value or ''), flags=re.IGNORECASE | re.DOTALL).strip()


def _plain_text(value):
    value = _strip_anchor_tags(value)
    value = re.sub(r'<[^>]+>', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def _clean_metadata_value(value):
    value = _plain_text(value)
    value = re.sub(r'^\s*(?:[-*#>]+|\d+[.)])\s*', '', value)
    value = value.strip().strip("'\"`").strip()
    value = re.sub(r'^\*+', '', value)
    value = re.sub(r'\*+$', '', value)
    return value.strip()


def _label_pattern(labels):
    return "|".join(re.escape(label) for label in labels)


def _extract_labeled_value(text, labels):
    if not text:
        return ""

    label_pattern = _label_pattern(labels)
    patterns = (
        rf'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?\s*(?:{label_pattern})\s*(?:\*\*)?\s*[:\-]\s*(.+?)\s*$',
        rf'(?is)<(?:p|span|li)[^>]*>\s*(?:<(?:strong|b)[^>]*>)?\s*(?:{label_pattern})\s*:?\s*(?:</(?:strong|b)>)?\s*(.*?)\s*</(?:p|span|li)>',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_metadata_value(match.group(1))
    return ""


def _normalized_key(value):
    return re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower()).strip()


def _infer_blog_category(value):
    source = _normalized_key(value)
    if not source:
        return "Guide"

    for alias, category in BLOG_CATEGORY_ALIASES.items():
        if source == _normalized_key(alias):
            return category

    keyword_groups = (
        ("Product", r'\b(product|buy|buyer|buying|shop|shopping|review|price|promo|promotion|brand|store)\b'),
        ("Story", r'\b(story|experience|journey|memory|personal)\b'),
        ("Tip and Trick", r'\b(tip|tips|trick|tricks|how to|checklist|advice|avoid|budget|cost)\b'),
        ("Explore", r'\b(explore|things to do|activity|activities|attraction|event|events|festival|where to go)\b'),
    )
    for category, pattern in keyword_groups:
        if re.search(pattern, source):
            return category

    return "Guide"


def _normalize_blog_category(value, fallback_text=""):
    cleaned_value = _clean_metadata_value(value)
    if cleaned_value in BLOG_CATEGORIES:
        return cleaned_value

    normalized_value = _normalized_key(cleaned_value)
    for alias, category in BLOG_CATEGORY_ALIASES.items():
        alias_key = _normalized_key(alias)
        if normalized_value == alias_key or alias_key in normalized_value:
            return category

    return _infer_blog_category(f"{cleaned_value} {fallback_text}")


def _fallback_blog_summary(title, place_name, blog_content="", category="Guide"):
    plain_content = _plain_text(blog_content)
    if plain_content:
        sentences = re.split(r'(?<=[.!?])\s+', plain_content)
        for sentence in sentences:
            sentence = _clean_metadata_value(sentence)
            if sentence and not sentence.lower().startswith(("title:", "category:", "summary:")):
                return sentence[:400]

    title = _clean_metadata_value(title) or "this topic"
    place_name = _clean_metadata_value(place_name) or "this place"
    fallback_by_category = {
        "Product": f"Practical product guide for {title}, with useful local context for {place_name}.",
        "Story": f"A local story about {title} in {place_name}.",
        "Tip and Trick": f"Useful tips for {title} in {place_name}.",
        "Explore": f"Explore {title} in {place_name} with practical local tips.",
        "Guide": f"Helpful guide to {title} in {place_name}.",
    }
    return fallback_by_category.get(category, fallback_by_category["Guide"])[:400]


def _remove_labeled_metadata_lines(text):
    label_pattern = _label_pattern(TITLE_LABELS + CATEGORY_LABELS + SUMMARY_LABELS)
    return re.sub(
        rf'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?\s*(?:{label_pattern})\s*(?:\*\*)?\s*[:\-]\s*.+?\s*$',
        '',
        text or '',
    ).strip()


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
    full_response = re.sub(r'^\s*```(?:html)?\s*', '', full_response, flags=re.IGNORECASE)
    full_response = re.sub(r'\s*```\s*$', '', full_response).strip()

    blog_title = _extract_labeled_value(full_response, TITLE_LABELS)
    if not blog_title or blog_title.lower().startswith('<article'):
        blog_title = fallback_title
    blog_title = _strip_anchor_tags(blog_title) or fallback_title

    raw_category = _extract_labeled_value(full_response, CATEGORY_LABELS)
    blog_category = _normalize_blog_category(raw_category, fallback_text=f"{fallback_title} {full_response[:1000]}")

    article_match = re.search(r'<article\b.*?</article>', full_response, flags=re.IGNORECASE | re.DOTALL)
    if article_match:
        blog_content = article_match.group(0).strip()
    else:
        blog_content = _remove_labeled_metadata_lines(full_response)

    blog_summary = _extract_labeled_value(full_response, SUMMARY_LABELS)
    blog_summary = _clean_metadata_value(blog_summary)
    if blog_summary.lower().startswith('summary:'):
        blog_summary = blog_summary[8:].strip()
    if not blog_summary:
        blog_summary = _fallback_blog_summary(fallback_title, place_name, blog_content, blog_category)

    try:
        if blog_content:
            print('Blog Full response :', full_response[:1000])
            print()
            print(blog_content[:1000])
            print()            
            print('Blog content before cleaning:', blog_content[:1000])
    except Exception as e:
        pass
    
    blog_content = re.sub(r'^\s*Title:\s*[^\n]+\n+', '', blog_content, flags=re.IGNORECASE).strip()
    for _ in range(2):
        blog_content = re.sub(r'\s*(Category|Summary):\s*[^\n]+\s*$', '', blog_content, flags=re.IGNORECASE).strip()
    if not blog_content and full_response:
        blog_content = full_response

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
        fallback_metadata_source = f"{blog_title} {to_title or ''} {link_promotion_present or ''}"
        blog_category = _infer_blog_category(fallback_metadata_source)
        blog_summary = _fallback_blog_summary(blog_title, place_name, category=blog_category)
        blog_content = ""
        try:
            print(f"Generating blog for {blog__title} in {place_name}...")

            promotion_instruction = (
                link_promotion_present
                if link_promotion_present
                else "No promotional URL was provided."
            )

            blog_prompt = build_blog_prompt(
                blog_title=blog__title,
                place_name=place_name,
                promotion_instruction=promotion_instruction,
            )

            res = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": blog_prompt}],
                max_tokens=3000
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
            # =========================
            # ✅ 4. Generate QR
            # =========================
            print(f"\n[4/5] 🔗 Generating QR code...")
            try:
                print(f"   ⏳ Creating QR code URL...")
                
                
                blog_slug = slugify(blog_title) or 'blog'
                url = f"https://www.paratara.com/pages/blog/{place_slug}/{blog_slug}/"
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
            print("❌ BLOG ERROR:", e)
 

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

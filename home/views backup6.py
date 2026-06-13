
# https://dayotreep.herokuapp.com/ | https://git.heroku.com/dayotreep.git
from collections import defaultdict
import html
import time
from urllib.parse import unquote, urlsplit

from django.db.models import Prefetch, Q, Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from resorts.models import resortPackages, Packages
import re
import os
import re

from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import HttpResponse
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.contrib.staticfiles import finders
from home.models import allSchedules, Places_v2
from django.shortcuts import render
from django.http import JsonResponse 
from django.views.generic import ListView, DetailView
from django.urls import reverse
from .models import allSchedules, Places_v2, SchedTypeAndMode, RequestPageSummary, RequestPage, FacebookPage
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json
from django.views.decorators.http import require_POST
import uuid
import io
import base64
import qrcode
from userProfile.models import UserCredentials
from userProfile.models import TourGuide
from userProfile.services import create_user_with_profile, ensure_user_profile
from django.conf import settings
try:
    from openai import OpenAI as _OpenAI
except ImportError:
    _OpenAI = None
from ai_chat.services.discussion_answer_service import (
    answer_discussion_message,
    check_blog_intent,
    classify_discussion_message as classify_local_discussion_message,
    sanitize_user_message,
)
from .models import PlaceDiscussion, TouristSpot, Visit
from django.http import JsonResponse
import json
import string
# Paymongo Payment
from requests.auth import HTTPBasicAuth
SECRET_KEY = "sk_live_qEeenZi789JGFsBXYMHSbAKe"
auth = HTTPBasicAuth(SECRET_KEY, '')
import requests
# end paymongo
from django import forms
import threading
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from .models import TouristSpot, Places_v2
from resorts.models import resortItem as ResortItem

from imageapp.imageuploader import getPlacePhoto

_EXTERNAL_AI_CLIENT = None


def _get_external_ai_client():
    """Lazy client for legacy non-discussion features that still use Grok."""
    global _EXTERNAL_AI_CLIENT
    if _EXTERNAL_AI_CLIENT is not None:
        return _EXTERNAL_AI_CLIENT
    if _OpenAI is None:
        raise RuntimeError("openai package is not installed")
    if not getattr(settings, "GROK_API_KEY", ""):
        raise RuntimeError("GROK_API_KEY is not configured")
    _EXTERNAL_AI_CLIENT = _OpenAI(api_key=settings.GROK_API_KEY, base_url="https://api.x.ai/v1")
    return _EXTERNAL_AI_CLIENT


class _LazyExternalAIClient:
    @property
    def chat(self):
        return _get_external_ai_client().chat


client = _LazyExternalAIClient()


def process_creating_blog(*args, **kwargs):
    from .tasks import process_creating_blog as _process_creating_blog

    return _process_creating_blog(*args, **kwargs)


def _discussion_csrf(view_func):
    if getattr(settings, "AI_DISCUSSION_CSRF_EXEMPT", True):
        return csrf_exempt(view_func)
    return view_func

DEFAULT_META_IMAGE_URL = (
    "https://511nyrideshare.org/documents/13062580/13063312/"
    "5cf107d7-1710-4076-b902-1aa0e6f554ea.jpg/f64aa95e-0a8c-6aca-470d-eef4ca2002ff"
    "?t=1562101484722"
)


def _absolute_public_url(request, value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        return request.build_absolute_uri(value)
    return ""


_DISCUSSION_RAG_INDEX_CACHE = {}
_DISCUSSION_RAG_EMBED_MODEL = None
_DISCUSSION_RAG_EMBED_UNAVAILABLE = False
_DISCUSSION_RAG_CACHE_SECONDS = 600


def _discussion_clean_text(value, limit=None):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].strip() + "..."
    return text


def _discussion_safe_url(value):
    url = str(value or "").strip()
    if url.startswith(("http://", "https://")):
        return url
    return ""


def _discussion_setting_float(name, default):
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _discussion_blog_url(request, blog_obj):
    current_domain = request.build_absolute_uri('/').rstrip('/')
    local_path = str(getattr(blog_obj, 'localurlpath', '') or '').strip()
    if local_path:
        if local_path.startswith(("http://", "https://")):
            return local_path
        if not local_path.startswith('/'):
            local_path = f"/{local_path}"
        return f"{current_domain}{local_path}"

    external_url = str(getattr(blog_obj, 'url', '') or '').strip()
    if external_url:
        if 'http://127.0.0.1:8000' in external_url:
            external_url = external_url.replace('http://127.0.0.1:8000', current_domain)
        elif 'http://localhost:8000' in external_url:
            external_url = external_url.replace('http://localhost:8000', current_domain)
        return external_url

    blog_place = getattr(blog_obj, 'blogplace', None)
    if blog_place:
        place_slug = slugify(getattr(blog_place, 'slug', '') or getattr(blog_place, 'placename', ''))
        title_slug = slugify(getattr(blog_obj, 'title', ''))
        if place_slug and title_slug:
            return f"{current_domain}/pages/blog/{place_slug}/{title_slug}/"
    return ""


def _discussion_add_doc(docs, kind, title, text_parts, metadata=None):
    text = "\n".join(_discussion_clean_text(part) for part in text_parts if _discussion_clean_text(part))
    title = _discussion_clean_text(title, 180)
    if not title and not text:
        return

    meta = dict(metadata or {})
    meta["kind"] = kind
    meta["title"] = title or _discussion_clean_text(text, 80)
    docs.append({
        "text": text[:2200],
        "metadata": meta,
    })


def _discussion_resort_amenities(resort):
    amenity_fields = {
        'has_wifi': 'WiFi',
        'has_pool': 'Pool',
        'has_bidet': 'Bidet',
        'has_parking': 'Parking',
        'has_restaurant': 'Restaurant',
        'has_bar': 'Bar',
        'has_spa': 'Spa',
        'has_gym': 'Gym',
        'has_beach_access': 'Beach access',
        'has_air_conditioning': 'Air conditioning',
        'has_hot_water': 'Hot water',
        'has_breakfast': 'Breakfast',
        'has_laundry': 'Laundry',
        'pet_friendly': 'Pet friendly',
        'family_friendly': 'Family friendly',
        'has_generator': 'Generator',
        'accepts_gcash': 'GCash',
        'accepts_cash': 'Cash',
        'accepts_debit_card': 'Debit card',
        'accepts_credit_card': 'Credit card',
    }
    return [label for field, label in amenity_fields.items() if getattr(resort, field, False)]


def _discussion_package_docs(docs, resort, relation_name, kind, label, now):
    resort_name = _discussion_clean_text(getattr(resort, 'RealName', '') or getattr(resort, 'name', ''))
    phone = _discussion_clean_text(getattr(resort, 'contactNumber', ''))
    email = _discussion_clean_text(getattr(resort, 'contactEmail', ''))
    resort_website = _discussion_safe_url(getattr(resort, 'websiteURL', ''))
    kind_keywords = {
        'accommodation': 'hotel stay room accommodation booking cheap luxury fan aircon private bathroom',
        'food': 'food restaurant eat dining menu breakfast lunch dinner coffee drink seafood cafe meal',
        'activity': 'activity things to do adventure surf snorkel rental rent sports play',
        'tour': 'tour island hopping guided tour package activity adventure',
    }
    kind_text = f"{label} {kind_keywords.get(kind, '')}".strip()
    shown = 0

    for package in list(getattr(resort, relation_name).all())[:12]:
        package_title = _discussion_clean_text(getattr(package, 'PackageTitle', ''))
        subpackages = list(package.subPackages.all())[:12]
        if not subpackages and package_title:
            _discussion_add_doc(
                docs,
                kind,
                package_title,
                [
                    f"Kind: {kind_text}",
                    f"Place: {getattr(getattr(resort, 'place', None), 'placename', '')}",
                    f"Resort: {resort_name}",
                    f"Package: {package_title}",
                    f"Contact phone: {phone}",
                    f"Contact email: {email}",
                    f"Website: {resort_website}",
                ],
                {
                    "kind_label": label,
                    "resort": resort_name,
                    "phone": phone,
                    "email": email,
                    "website": resort_website,
                    "summary": package_title,
                },
            )
            continue

        for sub in subpackages:
            if shown >= 20:
                return
            if hasattr(sub, 'is_available') and not sub.is_available:
                continue
            expires_at = getattr(sub, 'expires_at', None)
            if expires_at and expires_at <= now:
                continue

            sub_title = _discussion_clean_text(getattr(sub, 'title', ''))
            description = _discussion_clean_text(getattr(sub, 'description', ''), 260)
            information = _discussion_clean_text(getattr(sub, 'information', ''), 260)
            price = getattr(sub, 'price', 0) or 0
            item_website = _discussion_safe_url(getattr(sub, 'website', ''))

            _discussion_add_doc(
                docs,
                kind,
                sub_title or package_title,
                [
                    f"Kind: {kind_text}",
                    f"Resort: {resort_name}",
                    f"Package: {package_title}",
                    f"Title: {sub_title}",
                    f"Description: {description}",
                    f"Information: {information}",
                    f"Price: PHP {price}" if price else "",
                    f"Item website: {item_website}",
                    f"Resort website: {resort_website}",
                    f"Contact phone: {phone}",
                    f"Contact email: {email}",
                ],
                {
                    "kind_label": label,
                    "resort": resort_name,
                    "package_title": package_title,
                    "phone": phone,
                    "email": email,
                    "website": resort_website,
                    "item_website": item_website,
                    "price": str(price) if price else "",
                    "summary": description or information or package_title,
                },
            )
            shown += 1


def _discussion_collect_place_documents(place, request):
    docs = []
    place_name = _discussion_clean_text(getattr(place, 'placename', '') or getattr(place, 'name', ''))
    now = timezone.now()

    for blog in list(place.blogs.all()[:40]):
        title = _discussion_clean_text(getattr(blog, 'title', ''))
        summary = _discussion_clean_text(getattr(blog, 'summarize', ''), 260)
        body = _discussion_clean_text(getattr(blog, 'textContent', ''), 900)
        url = _discussion_blog_url(request, blog)
        _discussion_add_doc(
            docs,
            "blog",
            title,
            [
                "Kind: Blog article travel guide",
                f"Place: {place_name}",
                f"Title: {title}",
                f"Summary: {summary}",
                f"Content: {body}",
                f"URL: {url}",
            ],
            {
                "kind_label": "Blog",
                "url": _discussion_safe_url(url),
                "summary": summary or body,
            },
        )

    resorts = (
        place.resortList
        .prefetch_related(
            'resortAccomodations__subPackages',
            'resortActivities__subPackages',
            'resortTour__subPackages',
            'resortFood__subPackages',
        )
    )
    for resort in list(resorts[:40]):
        resort_name = _discussion_clean_text(getattr(resort, 'RealName', '') or getattr(resort, 'name', ''))
        description = _discussion_clean_text(getattr(resort, 'description', ''), 400)
        address = _discussion_clean_text(getattr(resort, 'address', ''))
        phone = _discussion_clean_text(getattr(resort, 'contactNumber', ''))
        email = _discussion_clean_text(getattr(resort, 'contactEmail', ''))
        website = _discussion_safe_url(getattr(resort, 'websiteURL', ''))
        amenities = _discussion_resort_amenities(resort)
        amenities_text = ", ".join(amenities)

        _discussion_add_doc(
            docs,
            "resort",
            resort_name,
            [
                "Kind: Resort hotel accommodation stay room booking",
                f"Place: {place_name}",
                f"Name: {resort_name}",
                f"Address: {address}",
                f"Description: {description}",
                f"Amenities: {amenities_text}",
                f"Contact phone: {phone}",
                f"Contact email: {email}",
                f"Website: {website}",
            ],
            {
                "kind_label": "Resort",
                "phone": phone,
                "email": email,
                "website": website,
                "summary": description or (f"Amenities: {amenities_text}" if amenities_text else address),
            },
        )

        _discussion_package_docs(docs, resort, 'resortAccomodations', 'accommodation', 'Room', now)
        _discussion_package_docs(docs, resort, 'resortFood', 'food', 'Food', now)
        _discussion_package_docs(docs, resort, 'resortActivities', 'activity', 'Activity', now)
        _discussion_package_docs(docs, resort, 'resortTour', 'tour', 'Tour', now)

    current_date = timezone.now().date()
    event_filter = (
        Q(yearN__gt=current_date.year)
        | Q(yearN=current_date.year, monthN__gt=current_date.month)
        | Q(yearN=current_date.year, monthN=current_date.month, dateN__gte=current_date.day)
    )
    for event in list(place.eventList.filter(event_filter).order_by('yearN', 'monthN', 'dateN')[:40]):
        title = _discussion_clean_text(getattr(event, 'scheduleTitle', ''))
        exact_date = _discussion_clean_text(getattr(event, 'exactDate', ''))
        event_place = _discussion_clean_text(getattr(event, 'schedulePlace', ''))
        details = _discussion_clean_text(getattr(event, 'additionalDetails', '') or getattr(event, 'otherDetails', ''), 320)
        website = _discussion_safe_url(getattr(event, 'scheduleWebsite', ''))
        cost = _discussion_clean_text(getattr(event, 'scheduleCost', ''))
        _discussion_add_doc(
            docs,
            "event",
            title,
            [
                "Kind: Event schedule festival happening activity",
                f"Place: {place_name}",
                f"Title: {title}",
                f"Date: {exact_date}",
                f"Location: {event_place}",
                f"Cost: {cost}",
                f"Details: {details}",
                f"Website: {website}",
            ],
            {
                "kind_label": "Event",
                "url": website,
                "summary": f"{exact_date} at {event_place}".strip(),
                "price": cost,
            },
        )

    guides_qs = TourGuide.objects.filter(is_active=True).select_related('user', 'primary_place')
    guides = list(guides_qs.filter(primary_place=place)[:12])
    if len(guides) < 12:
        existing_ids = {guide.id for guide in guides}
        for guide in guides_qs.filter(primary_place__isnull=True)[:12 - len(guides)]:
            if guide.id not in existing_ids:
                guides.append(guide)

    for guide in guides:
        user = getattr(guide, 'user', None)
        username = _discussion_clean_text(getattr(user, 'username', '') or 'Tour Guide')
        email = _discussion_clean_text(getattr(user, 'email', ''))
        phone = _discussion_clean_text(getattr(guide, 'mobile_number', ''))
        bio = _discussion_clean_text(getattr(guide, 'bio', ''), 360)
        certifications = _discussion_clean_text(getattr(guide, 'certifications', ''), 240)
        experience = getattr(guide, 'experience_years', 0) or 0
        _discussion_add_doc(
            docs,
            "tour_guide",
            username,
            [
                "Kind: Tour guide local guide private guide tourist guide guided tour",
                f"Place: {place_name}",
                f"Name: {username}",
                f"Experience years: {experience}",
                f"Bio: {bio}",
                f"Certifications: {certifications}",
                f"Contact phone: {phone}",
                f"Contact email: {email}",
            ],
            {
                "kind_label": "Tour Guide",
                "phone": phone,
                "email": email,
                "summary": bio or (f"{experience} year(s) experience" if experience else certifications),
            },
        )

    for spot in list(place.tourist_spots.all()[:40]):
        name = _discussion_clean_text(getattr(spot, 'name', ''))
        desc = _discussion_clean_text(getattr(spot, 'desc', ''), 420)
        url = _discussion_safe_url(getattr(spot, 'url', ''))
        _discussion_add_doc(
            docs,
            "tourist_spot",
            name,
            [
                "Kind: Tourist spot attraction destination place to visit",
                f"Place: {place_name}",
                f"Name: {name}",
                f"Description: {desc}",
                f"URL: {url}",
            ],
            {
                "kind_label": "Tourist Spot",
                "url": url,
                "summary": desc,
            },
        )

    return docs


def _discussion_get_embed_model(_step=None):
    global _DISCUSSION_RAG_EMBED_MODEL, _DISCUSSION_RAG_EMBED_UNAVAILABLE
    if _DISCUSSION_RAG_EMBED_MODEL is not None:
        return _DISCUSSION_RAG_EMBED_MODEL
    if _DISCUSSION_RAG_EMBED_UNAVAILABLE:
        return None

    try:
        from llama_index.core import Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        model_name = getattr(settings, 'DISCUSSION_RAG_EMBED_MODEL_NAME', 'BAAI/bge-small-en-v1.5')
        _DISCUSSION_RAG_EMBED_MODEL = HuggingFaceEmbedding(model_name=model_name)
        Settings.embed_model = _DISCUSSION_RAG_EMBED_MODEL
        try:
            Settings.llm = None
        except Exception:
            pass
        if _step:
            _step(f"RAG: HuggingFace embedding ready model={model_name}")
        return _DISCUSSION_RAG_EMBED_MODEL
    except Exception as exc:
        _DISCUSSION_RAG_EMBED_UNAVAILABLE = True
        if _step:
            _step(f"RAG: embedding unavailable, using lexical fallback ({type(exc).__name__})")
        return None


def _discussion_build_llama_index(docs, _step=None):
    embed_model = _discussion_get_embed_model(_step)
    if not embed_model:
        return None

    try:
        from llama_index.core import Document, Settings, VectorStoreIndex

        Settings.embed_model = embed_model
        try:
            Settings.llm = None
        except Exception:
            pass
        llama_docs = [
            Document(text=doc["text"], metadata=doc["metadata"])
            for doc in docs
            if doc.get("text")
        ]
        if not llama_docs:
            return None
        return VectorStoreIndex.from_documents(llama_docs)
    except Exception as exc:
        if _step:
            _step(f"RAG: index build failed, using lexical fallback ({type(exc).__name__})")
        return None


def _discussion_rag_cache_entry(place, request, _step=None):
    domain = request.build_absolute_uri('/').rstrip('/')
    cache_key = (getattr(place, 'pk', None), domain)
    cached = _DISCUSSION_RAG_INDEX_CACHE.get(cache_key)
    now_ts = time.time()
    if cached and cached.get("expires_at", 0) > now_ts:
        return cached

    docs = _discussion_collect_place_documents(place, request)
    index = _discussion_build_llama_index(docs, _step) if docs else None
    entry = {
        "docs": docs,
        "index": index,
        "expires_at": now_ts + _discussion_setting_float('DISCUSSION_RAG_CACHE_SECONDS', _DISCUSSION_RAG_CACHE_SECONDS),
    }
    _DISCUSSION_RAG_INDEX_CACHE[cache_key] = entry
    if _step:
        _step(f"RAG: cached docs={len(docs)} index={'yes' if index else 'no'}")
    return entry


_DISCUSSION_STOP_TOKENS = {
    'what', 'where', 'when', 'which', 'who', 'how', 'can', 'you', 'please', 'the', 'and',
    'for', 'with', 'near', 'around', 'from', 'into', 'about', 'that', 'this', 'there',
    'have', 'has', 'any', 'are', 'available', 'looking', 'need', 'want', 'find', 'give',
    'show', 'tell', 'list', 'best', 'good', 'your', 'here',
}


def _discussion_query_tokens(message):
    tokens = re.findall(r"[a-z0-9]{3,}", (message or "").lower())
    seen = set()
    return [
        token for token in tokens
        if token not in _DISCUSSION_STOP_TOKENS and not (token in seen or seen.add(token))
    ]


def _discussion_intent_kinds(message):
    lower = (message or "").lower()
    if any(term in lower for term in ['tour guide', 'tourguide', 'local guide', 'private guide', 'hire a guide']):
        return ['tour_guide']
    if any(term in lower for term in ['food', 'restaurant', 'eat', 'dining', 'menu', 'breakfast', 'lunch', 'dinner', 'coffee', 'drink']):
        return ['food', 'resort']
    if any(term in lower for term in ['room', 'stay', 'hotel', 'resort', 'accommodation', 'booking']):
        return ['accommodation', 'resort']
    if any(term in lower for term in ['event', 'events', 'festival', 'schedule', 'happening']):
        return ['event']
    if any(term in lower for term in ['activity', 'activities', 'things to do', 'what to do', 'tour', 'surf', 'snorkel', 'rent']):
        return ['activity', 'tour', 'tourist_spot']
    if any(term in lower for term in ['blog', 'article', 'guide']):
        return ['blog', 'tourist_spot']
    return []


def _discussion_lexical_matches(message, docs, top_k=6):
    tokens = _discussion_query_tokens(message)
    if not tokens:
        preferred_kinds = _discussion_intent_kinds(message)
        if preferred_kinds:
            return [
                {
                    "text": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": 0.1,
                }
                for doc in docs
                if doc.get("metadata", {}).get("kind") in preferred_kinds
            ][:top_k]
        return []

    scored = []
    phrase = _discussion_clean_text(message).lower()
    for doc in docs:
        metadata = doc.get("metadata", {})
        title = str(metadata.get("title", "")).lower()
        kind = str(metadata.get("kind", "")).lower()
        text = str(doc.get("text", "")).lower()
        haystack = f"{kind} {title} {text}"
        score = 0
        for token in tokens:
            if token in title:
                score += 4
            if token in kind:
                score += 3
            if token in haystack:
                score += 1
        if phrase and len(phrase) > 6 and phrase in haystack:
            score += 5
        if score:
            scored.append({
                "text": doc.get("text", ""),
                "metadata": metadata,
                "score": float(score),
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _discussion_node_text(node_obj):
    if hasattr(node_obj, "get_content"):
        try:
            return node_obj.get_content(metadata_mode="none")
        except TypeError:
            return node_obj.get_content()
    return str(getattr(node_obj, "text", "") or "")


def _discussion_retrieve_matches(message, place, request, _step=None, top_k=6):
    entry = _discussion_rag_cache_entry(place, request, _step)
    docs = entry.get("docs", [])
    matches = []
    index = entry.get("index")

    if index:
        try:
            retriever = index.as_retriever(similarity_top_k=top_k)
            min_score = _discussion_setting_float('DISCUSSION_RAG_MIN_SCORE', 0.30)
            for result in retriever.retrieve(message):
                score = getattr(result, "score", None)
                if score is not None and score < min_score:
                    continue
                node_obj = getattr(result, "node", result)
                matches.append({
                    "text": _discussion_node_text(node_obj),
                    "metadata": dict(getattr(node_obj, "metadata", {}) or {}),
                    "score": float(score or 0),
                })
            if _step:
                _step(f"RAG: vector matches={len(matches)}")
        except Exception as exc:
            if _step:
                _step(f"RAG: vector retrieval failed, using lexical fallback ({type(exc).__name__})")

    if not matches:
        matches = _discussion_lexical_matches(message, docs, top_k=top_k)
        if _step:
            _step(f"RAG: lexical matches={len(matches)}")
    return _discussion_dedupe_matches(matches)


def _discussion_dedupe_matches(matches):
    deduped = []
    seen = set()
    for match in matches:
        metadata = match.get("metadata", {})
        key = (
            metadata.get("kind", ""),
            metadata.get("title", ""),
            metadata.get("resort", ""),
            metadata.get("package_title", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
    return deduped


def _discussion_preferred_matches(message, matches):
    preferred_kinds = _discussion_intent_kinds(message)
    if not preferred_kinds:
        return matches

    preferred = [match for match in matches if match.get("metadata", {}).get("kind") in preferred_kinds]
    return preferred or matches


def _discussion_has_model_intent(message):
    lower = (message or "").lower()
    intent_terms = [
        'resort', 'hotel', 'stay', 'room', 'accommodation', 'booking', 'food', 'restaurant',
        'eat', 'dining', 'menu', 'activity', 'activities', 'things to do', 'tour', 'event',
        'schedule', 'festival', 'tour guide', 'local guide', 'guide', 'blog', 'article',
        'spot', 'visit', 'where to', 'what to do',
    ]
    return any(term in lower for term in intent_terms)


def _discussion_input_html(value):
    value = _discussion_clean_text(value)
    if not value:
        return ""
    escaped = html.escape(value, quote=True)
    return f'<input type="text" value="{escaped}" readonly onclick="this.select()">'


def _discussion_link_html(url, title):
    url = _discussion_safe_url(url)
    if not url:
        return ""
    return (
        f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">'
        f'{html.escape(title, quote=True)}</a>'
    )


def _discussion_match_html(match):
    metadata = match.get("metadata", {})
    kind = metadata.get("kind", "")
    kind_label = metadata.get("kind_label", kind.replace("_", " ").title() if kind else "Result")
    title = _discussion_clean_text(metadata.get("title", ""))
    resort = _discussion_clean_text(metadata.get("resort", ""))
    summary = _discussion_clean_text(metadata.get("summary", ""), 150)
    price = _discussion_clean_text(metadata.get("price", ""))

    label = html.escape(kind_label, quote=True)
    display_title = html.escape(title, quote=True)
    if resort and kind not in {"resort", "tour_guide"}:
        display_title = f'{display_title} at <strong>{html.escape(resort, quote=True)}</strong>'

    parts = [f'<strong>{label}: {display_title}</strong>']
    if summary:
        parts.append(html.escape(summary, quote=True))
    if price:
        price_label = price if not price.isdigit() else f"PHP {price}"
        parts.append(f'Price: {html.escape(price_label, quote=True)}')

    contact_parts = []
    for label_text, key in [('Phone', 'phone'), ('Email', 'email'), ('Website', 'website')]:
        contact_input = _discussion_input_html(metadata.get(key, ""))
        if contact_input:
            contact_parts.append(f'{label_text}: {contact_input}')
    if contact_parts and kind in {'resort', 'accommodation', 'food', 'activity', 'tour', 'tour_guide'}:
        parts.append('Contact: ' + " ".join(contact_parts))

    link_url = metadata.get("url") or metadata.get("item_website") or metadata.get("website")
    link_title = "Read article" if kind == "blog" else "Open link"
    link = _discussion_link_html(link_url, link_title)
    if link:
        parts.append(link)

    return ". ".join(part for part in parts if part)


def _discussion_response_from_matches(message, place, matches):
    matches = _discussion_preferred_matches(message, matches)
    if not matches:
        if _discussion_has_model_intent(message):
            place_name = html.escape(_discussion_clean_text(getattr(place, 'placename', 'this place')), quote=True)
            return (
                f'I could not find matching listed information for <strong>{place_name}</strong> yet. '
                'Try a specific resort, room, food, activity, event, blog, or tour guide keyword.'
            )
        return ""

    place_name = html.escape(_discussion_clean_text(getattr(place, 'placename', 'this place')), quote=True)
    rendered = [_discussion_match_html(match) for match in matches[:2]]
    rendered = [item for item in rendered if item]
    if not rendered:
        return ""
    return f' ' + " ".join(rendered)


def _discussion_model_backed_response(message, place, request, _step=None):
    matches = _discussion_retrieve_matches(message, place, request, _step)
    return _discussion_response_from_matches(message, place, matches)


def _classify_discussion_message(message):
    lower = (message or "").strip().lower()
    if not lower:
        return "NOT_QUESTION"

    create_verbs = ['make', 'create', 'write', 'generate']
    if (
        any(phrase in lower for phrase in ['make a blog', 'create a blog', 'write a blog', 'generate a blog'])
        or ('blog' in lower and any(verb in lower for verb in create_verbs))
        or ('article' in lower and any(verb in lower for verb in create_verbs))
    ):
        return "BLOG"

    greeting_only = {
        'hi', 'hello', 'hey', 'thanks', 'thank you', 'salamat', 'ok', 'okay', 'nice',
        'good morning', 'good afternoon', 'good evening',
    }
    if lower in greeting_only:
        return "NOT_QUESTION"

    question_terms = [
        '?', 'what', 'where', 'when', 'which', 'who', 'how', 'can i', 'can you',
        'do you', 'is there', 'are there', 'looking for', 'need', 'want', 'find',
        'recommend', 'suggest', 'available', 'price', 'cost', 'book', 'contact',
    ]
    if any(term in lower for term in question_terms) or _discussion_has_model_intent(lower):
        return "QUESTION"

    return "NOT_QUESTION"


class FacebookPageForm(forms.ModelForm):
    place = forms.ModelChoiceField(queryset=Places_v2.objects.all(), empty_label="Select a Place")

    class Meta:
        model = FacebookPage
        fields = ['page_id', 'name', 'link', 'about', 'category']


def favicon(request):
    icon_path = (
        finders.find("home/images/favicon-32x32.png")
        or finders.find("home/images/favicon-48x48.png")
        or finders.find("home/images/favicon.png")
    )
    if not icon_path:
        raise Http404("Favicon not found")
    return FileResponse(open(icon_path, "rb"), content_type="image/png")


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # First IP is original client in most proxy setups
        return xff.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR')


def _redirect_back_with_params(request, **params):
    print('Redirecting back with params:', params)
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    referer = request.META.get('HTTP_REFERER')
    if not referer:
        return redirect('/')
    print('Original Referer:', referer)
    parts = urlsplit(referer)
    qs = dict(parse_qsl(parts.query))
    for k, v in params.items():
        if v is None:
            qs.pop(k, None)
        else:
            qs[k] = str(v)
    redirect_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(qs), parts.fragment))
    return redirect(redirect_url)

 
def register_siargao_event(request, event_id):
    if request.method != 'POST':
        return _redirect_back_with_params(request)

    from .models import SiargaoEventSchedule, SiargaoEventRegistrant

    event_obj = get_object_or_404(SiargaoEventSchedule, id=event_id)

    full_name = (request.POST.get('full_name') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip()
    notes = (request.POST.get('notes') or '').strip()
    event_date = (request.POST.get('event_date') or '').strip()
    print('Event Date:', event_date)
    try:
        pax = int(request.POST.get('pax') or 1)
    except Exception:
        pax = 1
    if pax < 1:
        pax = 1

    if not full_name or not email:
        return _redirect_back_with_params(request, ev_reg_error='1', event_id=event_id)

    existing = SiargaoEventRegistrant.objects.filter(event=event_obj, email__iexact=email).first()
    if existing:
        existing.full_name = full_name
        existing.email = email
        existing.phone = phone
        existing.event_date = event_date
        existing.pax = pax
        existing.notes = notes
        existing.save()
        return _redirect_back_with_params(request, ev_reg_exists='1', event_id=event_id)

    SiargaoEventRegistrant.objects.create(
        event=event_obj,
        full_name=full_name,
        email=email,
        phone=phone,
        event_date=event_date,
        pax=pax,
        notes=notes,
    )
    return _redirect_back_with_params(request, ev_reg_success='1', event_id=event_id)


def presentation_insights(request):
    return render(request, 'home/presentation_insights.html')
def presentation(request):
    return render(request, 'home/presentation.html')


def _format_dashboard_datetime(dt, include_time=True):
    if not dt:
        return 'N/A'
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    fmt = '%b %d, %Y, %I:%M %p' if include_time else '%b %d, %Y'
    return dt.strftime(fmt).replace(' 0', ' ')


def _format_dashboard_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def _format_dashboard_decimal(value, places=1):
    try:
        return f"{float(value):,.{places}f}"
    except Exception:
        return f"{0:.{places}f}"


def _format_dashboard_percent(part, whole):
    if not whole:
        return "0%"
    value = (float(part) / float(whole)) * 100
    return f"{value:.0f}%" if value >= 10 else f"{value:.1f}%"


def _request_summary_location_dict(location_json, key):
    if not isinstance(location_json, dict):
        return {}
    value = location_json.get(key) or {}
    return value if isinstance(value, dict) else {}


def _request_summary_country(summary):
    city_info = _request_summary_location_dict(summary.ip_location_json, 'city_info')
    country_info = _request_summary_location_dict(summary.ip_location_json, 'country_info')
    return (
        (summary.country_name or '').strip()
        or (city_info.get('country_name') or '').strip()
        or (country_info.get('country_name') or '').strip()
        or 'Unknown'
    )


def _request_summary_city(summary):
    city_info = _request_summary_location_dict(summary.ip_location_json, 'city_info')
    return (summary.city or '').strip() or (city_info.get('city') or '').strip() or 'Unknown'


def _request_summary_continent(summary):
    city_info = _request_summary_location_dict(summary.ip_location_json, 'city_info')
    country_info = _request_summary_location_dict(summary.ip_location_json, 'country_info')
    return (
        (summary.continent_name or '').strip()
        or (city_info.get('continent_name') or '').strip()
        or (country_info.get('continent_name') or '').strip()
        or 'Unknown'
    )


def _request_summary_timezone(summary):
    city_info = _request_summary_location_dict(summary.ip_location_json, 'city_info')
    return (city_info.get('time_zone') or '').strip() or 'Unknown'


def _request_summary_location_label(summary):
    city = _request_summary_city(summary)
    country = _request_summary_country(summary)
    if city != 'Unknown' and country != 'Unknown':
        return f"{city}, {country}"
    if country != 'Unknown':
        return country
    continent = _request_summary_continent(summary)
    return continent if continent != 'Unknown' else 'Unknown'


def _iter_request_summary_pages(pages_json):
    if not pages_json:
        return

    if isinstance(pages_json, dict):
        for page, count in pages_json.items():
            if page is None:
                continue
            try:
                count_int = int(count)
            except Exception:
                count_int = 1
            yield str(page), max(count_int, 0)
        return

    if isinstance(pages_json, (list, tuple, set)):
        for page in pages_json:
            if page is not None:
                yield str(page), 1


def _normalize_request_page(page):
    page = str(page or '').strip()
    if not page:
        return '/'
    path = urlsplit(page).path or page
    if not path.startswith('/'):
        path = f"/{path}"
    return path


def _request_page_display_name(page):
    path = _normalize_request_page(page)
    if path == '/':
        return 'Home'
    cleaned = unquote(path.strip('/'))
    cleaned = cleaned.replace('-', ' ').replace('_', ' ')
    return ' / '.join(part[:1].upper() + part[1:] for part in cleaned.split('/') if part)


def _is_public_request_page(page):
    path = _normalize_request_page(page).lower()
    internal_prefixes = (
        '/admin',
        '/api',
        '/static',
        '/media',
        '/favicon',
        '/robots.txt',
        '/sitemap.xml',
        '/__debug__',
        '/presentation/request-page-summary',
    )
    return not any(path.startswith(prefix) for prefix in internal_prefixes)


def _mask_request_ip(ip):
    ip = str(ip or '').strip()
    if not ip:
        return 'Unknown'
    if ip == '127.0.0.1':
        return 'Local test'
    if ':' in ip:
        parts = ip.split(':')
        visible = ':'.join(parts[:3])
        return f"{visible}:..."
    parts = ip.split('.')
    if len(parts) == 4:
        return '.'.join(parts[:3] + ['x'])
    return ip


def _summary_month_start(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def request_page_summary_charts(request):
    top_n = 12
    summaries = list(
        RequestPageSummary.objects.all().only(
            'requesting_ip',
            'ip_location_json',
            'city',
            'country_name',
            'continent_name',
            'pages_json',
            'total_requests',
            'unique_pages',
            'earliest_timesmtamp',
            'latest_timesmtamp',
        )
    )

    total_visitors = len(summaries)
    total_requests = sum(int(s.total_requests or 0) for s in summaries)
    total_page_reach = sum(int(s.unique_pages or 0) for s in summaries)
    repeat_visitors = sum(1 for s in summaries if int(s.total_requests or 0) > 1)
    multi_page_visitors = sum(1 for s in summaries if int(s.unique_pages or 0) > 1)

    dated_first_seen = [s.earliest_timesmtamp for s in summaries if s.earliest_timesmtamp]
    dated_latest_seen = [s.latest_timesmtamp for s in summaries if s.latest_timesmtamp]
    first_seen = min(dated_first_seen) if dated_first_seen else None
    latest_seen = max(dated_latest_seen) if dated_latest_seen else None
    data_window_days = 0
    if first_seen and latest_seen:
        data_window_days = max((latest_seen - first_seen).days + 1, 1)

    country_totals = defaultdict(int)
    country_visitors = defaultdict(int)
    continent_totals = defaultdict(int)
    city_totals = defaultdict(int)
    timezone_totals = defaultdict(int)
    first_month_requests = defaultdict(int)
    first_month_visitors = defaultdict(int)
    latest_month_visitors = defaultdict(int)
    page_request_totals = defaultdict(int)
    page_visitor_totals = defaultdict(int)
    public_request_total = 0
    public_page_names = set()
    depth_buckets = {
        '1 page': 0,
        '2-3 pages': 0,
        '4-7 pages': 0,
        '8+ pages': 0,
    }
    window_buckets = {
        '< 1 min': 0,
        '1-15 min': 0,
        '15-60 min': 0,
        '1-24 hrs': 0,
        '1+ days': 0,
    }

    for summary in summaries:
        requests_count = int(summary.total_requests or 0)
        unique_pages = int(summary.unique_pages or 0)

        country = _request_summary_country(summary)
        country_totals[country] += requests_count
        country_visitors[country] += 1

        continent_totals[_request_summary_continent(summary)] += requests_count
        city = _request_summary_city(summary)
        country_for_city = country if country != 'Unknown' else ''
        city_label = f"{city}, {country_for_city}".strip(', ') if city != 'Unknown' else 'Unknown'
        city_totals[city_label] += requests_count
        timezone_totals[_request_summary_timezone(summary)] += requests_count

        first_month = _summary_month_start(summary.earliest_timesmtamp)
        if first_month:
            first_month_requests[first_month] += requests_count
            first_month_visitors[first_month] += 1
        latest_month = _summary_month_start(summary.latest_timesmtamp)
        if latest_month:
            latest_month_visitors[latest_month] += 1

        if unique_pages <= 1:
            depth_buckets['1 page'] += 1
        elif unique_pages <= 3:
            depth_buckets['2-3 pages'] += 1
        elif unique_pages <= 7:
            depth_buckets['4-7 pages'] += 1
        else:
            depth_buckets['8+ pages'] += 1

        if summary.earliest_timesmtamp and summary.latest_timesmtamp:
            active_seconds = max((summary.latest_timesmtamp - summary.earliest_timesmtamp).total_seconds(), 0)
        else:
            active_seconds = 0

        if active_seconds < 60:
            window_buckets['< 1 min'] += 1
        elif active_seconds < 15 * 60:
            window_buckets['1-15 min'] += 1
        elif active_seconds < 60 * 60:
            window_buckets['15-60 min'] += 1
        elif active_seconds < 24 * 60 * 60:
            window_buckets['1-24 hrs'] += 1
        else:
            window_buckets['1+ days'] += 1

        pages_seen_by_visitor = set()
        for page, count in _iter_request_summary_pages(summary.pages_json):
            if count <= 0 or not _is_public_request_page(page):
                continue
            normalized_page = _normalize_request_page(page)
            page_request_totals[normalized_page] += int(count)
            public_request_total += int(count)
            public_page_names.add(normalized_page)
            pages_seen_by_visitor.add(normalized_page)

        for page in pages_seen_by_visitor:
            page_visitor_totals[page] += 1

    top_pages = sorted(
        page_request_totals.items(),
        key=lambda item: (-item[1], -page_visitor_totals.get(item[0], 0), item[0]),
    )[:10]
    top_countries = sorted(country_totals.items(), key=lambda item: (-item[1], item[0]))[:8]
    top_continents = sorted(continent_totals.items(), key=lambda item: (-item[1], item[0]))[:8]
    top_cities = sorted(city_totals.items(), key=lambda item: (-item[1], item[0]))[:8]
    top_timezones = sorted(timezone_totals.items(), key=lambda item: (-item[1], item[0]))[:8]

    top_summaries = sorted(
        summaries,
        key=lambda s: (
            int(s.total_requests or 0),
            s.latest_timesmtamp or datetime.min.replace(tzinfo=timezone.get_current_timezone()),
        ),
        reverse=True,
    )[:top_n]

    top_visitor_rows = []
    visitor_labels = []
    visitor_request_counts = []
    visitor_page_counts = []
    visitor_window_hours = []
    visitor_first_seen = []
    visitor_latest_seen = []
    for idx, summary in enumerate(top_summaries, start=1):
        top_page = None
        top_page_count = 0
        for page, count in _iter_request_summary_pages(summary.pages_json):
            if count > top_page_count and _is_public_request_page(page):
                top_page = page
                top_page_count = count

        if summary.earliest_timesmtamp and summary.latest_timesmtamp:
            hours_active = max((summary.latest_timesmtamp - summary.earliest_timesmtamp).total_seconds() / 3600.0, 0)
        else:
            hours_active = 0

        label = f"Visitor {idx}"
        visitor_labels.append(label)
        visitor_request_counts.append(int(summary.total_requests or 0))
        visitor_page_counts.append(int(summary.unique_pages or 0))
        visitor_window_hours.append(round(hours_active, 2))
        visitor_first_seen.append(_format_dashboard_datetime(summary.earliest_timesmtamp))
        visitor_latest_seen.append(_format_dashboard_datetime(summary.latest_timesmtamp))
        top_visitor_rows.append(
            {
                'label': label,
                'masked_ip': _mask_request_ip(summary.requesting_ip),
                'location': _request_summary_location_label(summary),
                'requests': _format_dashboard_number(summary.total_requests),
                'unique_pages': _format_dashboard_number(summary.unique_pages),
                'top_page': _request_page_display_name(top_page) if top_page else 'No public page',
                'first_seen': _format_dashboard_datetime(summary.earliest_timesmtamp),
                'latest_seen': _format_dashboard_datetime(summary.latest_timesmtamp),
            }
        )

    month_keys = sorted(set(first_month_requests.keys()) | set(first_month_visitors.keys()) | set(latest_month_visitors.keys()))
    month_labels = [month.strftime('%b %Y') for month in month_keys]

    top_page_rows = [
        {
            'page': _request_page_display_name(page),
            'path': page,
            'requests': _format_dashboard_number(total),
            'visitors': _format_dashboard_number(page_visitor_totals.get(page, 0)),
            'share': _format_dashboard_percent(total, public_request_total),
        }
        for page, total in top_pages[:6]
    ]

    country_rows = [
        {
            'country': country,
            'requests': _format_dashboard_number(total),
            'visitors': _format_dashboard_number(country_visitors.get(country, 0)),
            'share': _format_dashboard_percent(total, total_requests),
        }
        for country, total in top_countries[:6]
    ]

    top_country_name, top_country_requests = top_countries[0] if top_countries else ('No country data', 0)
    top_page_name, top_page_requests = top_pages[0] if top_pages else ('No public page data', 0)
    avg_requests = (total_requests / total_visitors) if total_visitors else 0
    avg_pages = (total_page_reach / total_visitors) if total_visitors else 0

    insight_cards = []
    if total_requests:
        insight_cards.append(
            f"{_format_dashboard_number(total_requests)} requests from {_format_dashboard_number(total_visitors)} tracked visitors show measurable audience demand."
        )
        insight_cards.append(
            f"{_format_dashboard_percent(repeat_visitors, total_visitors)} of visitors returned or made multiple requests, a useful signal for remarketing and partnerships."
        )
        if top_page_requests:
            insight_cards.append(
                f"{_request_page_display_name(top_page_name)} leads public page demand with {_format_dashboard_number(top_page_requests)} requests."
            )
        if top_country_requests:
            insight_cards.append(
                f"{top_country_name} is the strongest geography with {_format_dashboard_number(top_country_requests)} requests."
            )
    else:
        insight_cards.append(
            "No request summaries are available yet. Run the summarizer after traffic is collected to populate client-facing insights."
        )

    kpi_cards = [
        {
            'label': 'Tracked requests',
            'value': _format_dashboard_number(total_requests),
            'note': f"{_format_dashboard_decimal(avg_requests)} requests per visitor",
        },
        {
            'label': 'Visitors',
            'value': _format_dashboard_number(total_visitors),
            'note': f"{_format_dashboard_percent(repeat_visitors, total_visitors)} repeat signal",
        },
        {
            'label': 'Public page demand',
            'value': _format_dashboard_number(public_request_total),
            'note': f"{_format_dashboard_number(len(public_page_names))} public pages reached",
        },
        {
            'label': 'Pages per visitor',
            'value': _format_dashboard_decimal(avg_pages),
            'note': f"{_format_dashboard_percent(multi_page_visitors, total_visitors)} viewed multiple pages",
        },
        {
            'label': 'Top geography',
            'value': top_country_name,
            'note': f"{_format_dashboard_number(top_country_requests)} requests",
        },
        {
            'label': 'Data window',
            'value': f"{data_window_days} day" if data_window_days == 1 else f"{data_window_days} days",
            'note': f"Latest: {_format_dashboard_datetime(latest_seen, include_time=False)}",
        },
    ]

    chart_data = {
        'traffic': {
            'labels': month_labels,
            'requests': [int(first_month_requests.get(month, 0)) for month in month_keys],
            'newVisitors': [int(first_month_visitors.get(month, 0)) for month in month_keys],
            'activeVisitors': [int(latest_month_visitors.get(month, 0)) for month in month_keys],
        },
        'pages': {
            'labels': [_request_page_display_name(page) for page, _ in top_pages],
            'requests': [int(total) for _, total in top_pages],
            'visitors': [int(page_visitor_totals.get(page, 0)) for page, _ in top_pages],
        },
        'countries': {
            'labels': [country for country, _ in top_countries],
            'requests': [int(total) for _, total in top_countries],
            'visitors': [int(country_visitors.get(country, 0)) for country, _ in top_countries],
        },
        'continents': {
            'labels': [continent for continent, _ in top_continents],
            'requests': [int(total) for _, total in top_continents],
        },
        'cities': {
            'labels': [city for city, _ in top_cities],
            'requests': [int(total) for _, total in top_cities],
        },
        'timezones': {
            'labels': [tz for tz, _ in top_timezones],
            'requests': [int(total) for _, total in top_timezones],
        },
        'visitors': {
            'labels': visitor_labels,
            'requests': visitor_request_counts,
            'pages': visitor_page_counts,
            'hours': visitor_window_hours,
            'firstSeen': visitor_first_seen,
            'latestSeen': visitor_latest_seen,
        },
        'depth': {
            'labels': list(depth_buckets.keys()),
            'counts': list(depth_buckets.values()),
        },
        'windows': {
            'labels': list(window_buckets.keys()),
            'counts': list(window_buckets.values()),
        },
        'engagement': {
            'labels': ['Single request', 'Repeat requests'],
            'counts': [max(total_visitors - repeat_visitors, 0), repeat_visitors],
        },
    }

    return render(
        request,
        'home/request_page_summary_charts.html',
        {
            'top_n': top_n,
            'kpi_cards': kpi_cards,
            'insight_cards': insight_cards,
            'top_page_rows': top_page_rows,
            'country_rows': country_rows,
            'top_visitor_rows': top_visitor_rows,
            'chart_data': chart_data,
            'data_window_label': (
                f"{_format_dashboard_datetime(first_seen, include_time=False)} to {_format_dashboard_datetime(latest_seen, include_time=False)}"
                if first_seen and latest_seen
                else 'No traffic window yet'
            ),
            'latest_activity_label': _format_dashboard_datetime(latest_seen),
            'page_title': 'Request Summary Dashboard | Paratara',
            'meta_description': 'Internal Paratara request analytics dashboard.',
            'robots_meta': 'noindex, nofollow',
            'canonical_url': request.build_absolute_uri(reverse('home:request-page-summary-charts')),
        },
    )

@csrf_exempt
def record_visit(request, place_slug, spot_slug):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=400)
        place = get_object_or_404(Places_v2, slug=place_slug)
        spot = get_object_or_404(TouristSpot, place=place, slug=spot_slug)
        
        from django.utils import timezone
        today = timezone.now().date()

        if Visit.objects.filter(tourist_spot=spot, tourist=request.user, timestamp__date=today).exists():
            return JsonResponse({'error': 'You have already visited this spot today'}, status=400)
        
        Visit.objects.create(tourist_spot=spot, tourist=request.user)

        return JsonResponse({'status': 'visit recorded'})
    return JsonResponse({'error': 'POST method required'})

def remove_visit(request, place_slug, spot_slug):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=400)
        place = get_object_or_404(Places_v2, slug=place_slug)
        spot = get_object_or_404(TouristSpot, place=place, slug=spot_slug)
        
        from django.utils import timezone
        today = timezone.now().date()
        visit = Visit.objects.filter(tourist_spot=spot, tourist=request.user, timestamp__date=today).first()
        print('Visit: ',visit)
        print('User: ',request.user)
        if not visit:
            return JsonResponse({'error': 'No visit found for today'}, status=400)
        
        visit.delete()
        return JsonResponse({'status': 'visit removed'})
    return JsonResponse({'error': 'POST method required'})

# def todo let us know you exited the place TODO

def get_spot_details(request, place_slug, spot_slug):
    place = get_object_or_404(Places_v2, slug=place_slug)
    spot = get_object_or_404(TouristSpot, place=place, slug=spot_slug)
    return JsonResponse({
        'id': spot.id,
        'name': spot.name,
        'place': spot.place.placename,
        'desc': spot.desc,
        'img': spot.img,
        'url': spot.url,
    })


def get_visitor_stats(request, spot_id):
    spot = get_object_or_404(TouristSpot, id=spot_id)
    # Visitors today
    today = datetime.now().date()
    today_count = Visit.objects.filter(tourist_spot=spot, timestamp__date=today).count()
    # Visitors in the last hour
    from django.utils import timezone
    last_hour = timezone.now() - timezone.timedelta(hours=1)
    hour_count = Visit.objects.filter(tourist_spot=spot, timestamp__gte=last_hour).count()
    # Morning and afternoon counts (assuming morning 00:00-12:00, afternoon 12:00-23:59)
    from datetime import time
    morning_count = Visit.objects.filter(
        tourist_spot=spot, 
        timestamp__date=today, 
        timestamp__time__range=(time(0, 0), time(11, 59))
    ).count()
    afternoon_count = Visit.objects.filter(
        tourist_spot=spot, 
        timestamp__date=today, 
        timestamp__time__range=(time(12, 0), time(23, 59))
    ).count()
    # Per hour today
    from django.db.models import Count
    from django.db.models.functions import TruncHour
    hourly_counts = Visit.objects.filter(tourist_spot=spot, timestamp__date=today).annotate(hour=TruncHour('timestamp')).values('hour').annotate(count=Count('id')).order_by('hour')
    stats = {
        'today_total': today_count,
        'last_hour': hour_count,
        'morning_count': morning_count,
        'afternoon_count': afternoon_count,
        'hourly': list(hourly_counts)
    }
    return JsonResponse(stats)


def tourist_spots(request, place_slug):
    place = get_object_or_404(Places_v2, slug=place_slug)
    spots = place.tourist_spots.all()
    spot_data = []
    from django.utils import timezone
    today = timezone.now().date()
    for spot in spots:
        visit_count = spot.tourists.count()
        visited_today = False
        if request.user.is_authenticated:
            visited_today = Visit.objects.filter(tourist_spot=spot, tourist=request.user, timestamp__date=today).exists()
        spot_data.append({
            'spot': spot,
            'visit_count': visit_count,
            'visited_today': visited_today
        })
    return render(request, 'home/tourist_spots.html', {'place': place, 'spot_data': spot_data})


def all_tourist_spots(request):
    spots = TouristSpot.objects.all().select_related('place')
    spot_data = []
    from django.utils import timezone
    today = timezone.now().date()
    for spot in spots:
        visit_count = spot.tourists.count()
        visited_today = False
        if request.user.is_authenticated:
            visited_today = Visit.objects.filter(tourist_spot=spot, tourist=request.user, timestamp__date=today).exists()
        spot_data.append({
            'spot': spot,
            'visit_count': visit_count,
            'visited_today': visited_today
        })
    return render(request, 'home/all_tourist_spots.html', {'spot_data': spot_data})


def visit_spot(request, place_slug, spot_slug):
    from django.contrib.auth import login
    from django import forms

    if request.user.is_authenticated:
        return render(request, 'home/visit_recorded.html')
    class QuickRegisterForm(forms.Form):
        username = forms.CharField(max_length=150)
        password = forms.CharField(widget=forms.PasswordInput)
        contact_number = forms.CharField(max_length=128, help_text="Required contact number for emergency purposes")
        age_range = forms.ChoiceField(choices=[
            ('under_18', 'Under 18'),
            ('18_24', '18-24'),
            ('25_34', '25-34'),
            ('35_44', '35-44'),
            ('45_54', '45-54'),
            ('55_64', '55-64'),
            ('65_plus', '65+'),
            ('prefer_not_to_disclose', 'Prefer not to disclose')
        ], required=False, label="Age Range")
        gender = forms.ChoiceField(choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('prefer_not_to_disclose', 'Prefer not to disclose')
        ], required=False, label="Gender")
    
    
    if request.method == 'POST':
        form = QuickRegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            contact_number = form.cleaned_data.get('contact_number', '')
            age_range = form.cleaned_data.get('age_range', '')
            gender = form.cleaned_data.get('gender', '')
            
            if UserCredentials.objects.filter(username=username).exists():
                user = UserCredentials.objects.get(username=username)
                if user.check_password(password):
                    ensure_user_profile(
                        user,
                        contact=contact_number,
                        age_range=age_range,
                        gender=gender,
                    )
                    login(request, user)
                    return render(request, 'home/visit_recorded.html')
                else:
                    form.add_error('password', 'Incorrect password or username already exist')
            else:
                user, poster = create_user_with_profile(
                    username=username,
                    password=password,
                    profile_name=username,
                    contact=contact_number,
                    age_range=age_range,
                    gender=gender,
                )
                
                login(request, user)
                return render(request, 'home/visit_recorded.html')
    else:
        form = QuickRegisterForm()
    place = get_object_or_404(Places_v2, slug=place_slug)
    spot = get_object_or_404(TouristSpot, place=place, slug=spot_slug)
        
    return render(request, 'home/visit_spot.html', {'form': form, 'spot': spot})



def getSiargaoEvents(request):
    from . import scraperSiargao
    # scraperSiargao.SiargaoScrapper()
    from .models import SiargaoEventSchedule
    place = Places_v2.objects.get(placename="Siargao")
    # Path to your CSV
    import csv
    csv_file_path = "siargao_events.csv"
    with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Extract data
            title = row.get("Title", "").strip()
            link = row.get("Link", "").strip()
            background = row.get("Background", "").replace('url("', '').replace('")', '').strip()
            thumbnail = row.get("Thumbnail", "").strip()
            marker = row.get("Marker", "").strip()
            location_text = row.get("Location", "").strip()
            date_text = row.get("Date", "").strip()
            host_name = row.get("Host Name", "").strip() or "Anonymous"
            host_link = row.get("Host Link", "").strip()
            locations_json = row.get("Locations JSON", "[]").strip()
            
            try:
                locations = json.loads(locations_json)
            except json.JSONDecodeError:
                locations = []

            # Parse date
            try:
                event_datetime = datetime.strptime(date_text.split(" - ")[0].strip(), "%B %d, %Y %I:%M %p")
                dateN, monthN, yearN = event_datetime.day, event_datetime.month, event_datetime.year
            except:
                dateN, monthN, yearN = datetime.now().day, datetime.now().month, datetime.now().year

            event_obj, created = SiargaoEventSchedule.objects.get_or_create(
                scheduleTitle=title,  # field to check uniqueness
                defaults={
                    'posterName': host_name,
                    'exactDate': date_text,
                    'posterURL': host_link,
                    'scheduleWebsite': link,
                    'backgroundURL': background,
                    'thumbnailURL': thumbnail,
                    'markerURL': marker,
                    'schedulePlace': location_text,
                    'dateN': dateN,
                    'monthN': monthN,
                    'yearN': yearN,
                    'otherDetails': json.dumps(locations)
                }
            )
            place.eventSchedules.add(event_obj)

            print(f"Saved: {title}")

def searchplace(request):
    pass
    # query = request.GET.get("q")
    # results = []
    # if query:
    #     results = Places_v2.objects.annotate(
    #         similarity=TrigramSimilarity('placename', query)
    #     ).filter(similarity__gt=0.3).order_by('-similarity')
    # return render(request, "search.html", {"results": results})


    # from django.http import JsonResponse
    # import json
    # query = request.GET.get('q', '')
    # if query:
    #     places = Places_v2.objects.filter(placename__icontains=query).values()
    #     results = list(places)
    # else:
    #     results = []
    # return JsonResponse({'results': results})


def paypal_html(request):
    from django.conf import settings
    return render(request, "home/paypal_payment.html", {
        # "paypal_client_id": "YOUR_SANDBOX_CLIENT_ID",
        "paypal_client_id": settings.PAYPAL_CLIENT_ID
    })    


@csrf_exempt
def paypal_webhook(request):
    if request.method == "POST":
        payload = json.loads(request.body)

        event_type = payload.get("event_type")
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            order_id = payload["resource"]["id"]
            payer_email = payload["resource"]["payer"]["email_address"]
            amount = payload["resource"]["amount"]["value"]

            # ✅ Save into your DB (example: mark Blog as paid)
            print(f"✅ Payment {order_id} received: {amount} from {payer_email}")

        return JsonResponse({"status": "ok"})





def htmltest(request):
    return render(request, 'home/test.html')
    # return render(request, 'home/htmltest.html')
# Create your views here.
def autopopulate(request):
    return HttpResponse("Started Creating Random Schedules")
    from django.conf import settings
    import json
    import os
    import json
    import random
    import random

    first_names = ["Anna", "Jake", "Liam", "Sofia", "Noah", "Ella", "Mia", "Ethan", "Grace", "Leo"]
    last_names = ["Taylor", "Smith", "Rivera", "Lopez", "Brown", "Garcia", "Martin", "Lee", "Davis", "Young"]

    def generate_human_usernames():
        first = random.choice(first_names)
        last = random.choice(last_names)
        style = random.choice([
            f"{first}{last}",
            f"{first}.{last}",
            f"{first}_{last}",
            f"{first}{last[0]}",
            f"{first}{random.randint(1, 99)}",   # e.g. Jake45
            f"{first}{last}{random.choice(['', '01', '22', '99'])}"  # e.g. MiaLee22
        ])
        return style.lower()
    def generate_random_meetplace():
        return random.choice(data)["name"]

    poster = ensure_user_profile(request.user)


    print('\nMaking Cities')
    json_path = os.path.join(settings.BASE_DIR, 'data', 'cities.json')
    print('\nJSON PATH', json_path)
    with open(json_path, 'r') as f:
        data = json.load(f)
    target_provinces = {"MM", "BTG", "QUE"}
    data = [item for item in data if item["province"] in target_provinces]
    for d in data:
        try:
            checkedMunicipality = Places_v2.objects.get(placename = d['name'])
            print(d['name'],' Already Has')
        except:
            checkedMunicipality = Places_v2.objects.create(placename = d['name'])
            
            checkedMunicipality.placePhoto = getPlacePhoto(request, d['name'])
            
            checkedMunicipality.save()
            checkedMunicipality.placeID = checkedMunicipality.id
            checkedMunicipality.save()
            print('Saved ',d['name'])
        try:
            
            from resorts.models import resortItem as resort
            for r in resort.objects.all():
                if re.search(r.province, checkedMunicipality.placename, re.IGNORECASE):
                    checkedMunicipality.resortItem.add(r)
                    print('resort found',checkedMunicipality)
            print('try',end='')
        except:
            print('.',end='')


        detailsContact = '+639765514253'
        # additionalDetails = 'Looking for Shared'
        additionalDetails = ''
        otherDetails = 'Looking for pasahero'
        scheduleWebsite = 'https://treep.today'
        scheduleWebsite = ''


        for eachDate in range(random.randint(7, 14)):
            randomUsername = generate_human_usernames()
            meetPlace = generate_random_meetplace()            
            print(eachDate)
            # addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, poster=poster, posterID=request.user.id, posterName=request.user.username, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(1, 3), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', scheduleTypeAndMode=TheTravelType, additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
            addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, posterID=request.user.id, posterName=randomUsername, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(7, 9), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
            addedRandomSchedule.save()
            addedRandomSchedule.scheduleID = addedRandomSchedule.id
            addedRandomSchedule.save()

            checkedMunicipality.placesSchedules.add(addedRandomSchedule)
            checkedMunicipality.save()

        try:
            poster.posts.add(addedRandomSchedule)
            poster.reputations += 2
            poster.save()
        except:
            pass

        print('\n   Done Creating Dates for: ', checkedMunicipality, '\n\n\n')        

        
    print('\nEnd Making Cities\n\n')

    

    print('\n\nStarting ...\n\n')

    print('\n Getting User')

    # random.randint(283, 351)


    print('     Creating Travel Dates: ')
    

    # return HttpResponse("Done Creating Random Schedules")
    return redirect('home:home')
# def addSchedulesAndPlaces(request):
#     print('\n\nStarting ...\n\n')
#     import json
#     import random
#     from userProfile.models import userPoster
#     print('\n Getting User')
#     try:
#         poster = userPoster.objects.get(userID=request.user.id)
#     except:
#         poster = userPoster.objects.create(
#             userID=request.user.id, name=request.user.username, contact=request.user.email)

#     # random.randint(283, 351)
#     f = open('cebumunicipal.json')
#     data = json.load(f)
#     print('\n\n Looking for Municipalities: ...')
#     print('\n Found: ', len(data["CEBU"]
#           ["municipality_list"]), ' Municipalities\n\n')
#     for eachMunicipality in data["CEBU"]["municipality_list"]:
#         eachMunicipality = " ".join([eachMunicipality.capitalize(), 'Cebu'])
#         print('\n       Creating Schedule for:   ', eachMunicipality, '\n')
#         # First Check Municipality
#         try:
#             checkedMunicipality = Places_v2.objects.get(
#                 placename__iexact=eachMunicipality)
#         except:
#             checkedMunicipality = Places_v2.objects.create(
#                 placename=eachMunicipality)

#         checkedMunicipality.save()
#         checkedMunicipality.placeID = checkedMunicipality.id

#         print('     Creating Travel Dates: ')

#         try:
#             TheTravelType = SchedTypeAndMode.objects.get_or_create(modeName='carpool')[
#                 0]
#         except:
#             TheTravelType = SchedTypeAndMode.objects.filter(modeName='carpool')[
#                 0]
#         # Make Random
        
#         import random

#         first_names = ["Anna", "Jake", "Liam", "Sofia", "Noah", "Ella", "Mia", "Ethan", "Grace", "Leo"]
#         last_names = ["Taylor", "Smith", "Rivera", "Lopez", "Brown", "Garcia", "Martin", "Lee", "Davis", "Young"]

#         def generate_human_usernames():
#             first = random.choice(first_names)
#             last = random.choice(last_names)
#             style = random.choice([
#                 f"{first}{last}",
#                 f"{first}.{last}",
#                 f"{first}_{last}",
#                 f"{first}{last[0]}",
#                 f"{first}{random.randint(1, 99)}",   # e.g. Jake45
#                 f"{first}{last}{random.choice(['', '01', '22', '99'])}"  # e.g. MiaLee22
#             ])
#             return style.lower()

#         randomUsername = generate_human_usernames()
#         meetPlace = 'Near Munisipyo'
#         detailsContact = '+639765514253'
#         # additionalDetails = 'Looking for Shared'
#         additionalDetails = ''
#         otherDetails = 'Looking for pasahero'
#         scheduleWebsite = 'https://treep.today'
#         scheduleWebsite = ''


#         for eachDate in range(random.randint(7, 14)):
#             print(eachDate)
#             # addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, poster=poster, posterID=request.user.id, posterName=request.user.username, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(1, 3), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', scheduleTypeAndMode=TheTravelType, additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
#             addedRandomSchedule = allSchedules(schedulePlace=checkedMunicipality, posterID=request.user.id, posterName=randomUsername, posterVerified=poster.verified, posterReputation=poster.reputations, dateN=random.randint( 1, 27), monthN=random.randint(7, 9), yearN=2025, meetPlace=meetPlace, detailsContact=detailsContact, MakerOrLooker='Make', additionalDetails=additionalDetails, otherDetails=otherDetails, posterImageURL=poster.photo, scheduleWebsite=scheduleWebsite)
#             addedRandomSchedule.save()
#             addedRandomSchedule.scheduleID = addedRandomSchedule.id
#             addedRandomSchedule.save()

#             checkedMunicipality.placesSchedules.add(addedRandomSchedule)
#             checkedMunicipality.save()

#         try:
#             poster.posts.add(addedRandomSchedule)
#             poster.reputations += 2
#             poster.save()
#         except:
#             pass

#         print('\n   Done Creating Dates for: ', checkedMunicipality, '\n\n\n')
#     return HttpResponse("Done Creating Random Schedules")

def addSchedulesAndPlaces(request):
    pass
def addReviewstoSchedules(request):
    import random

    ScheduleObjectLists = allSchedules.objects.all()
    for i in ScheduleObjectLists:
        i.reviewCount = random.randint(3, 16)
        i.save()

    PlaceObjectLists = Places_v2.objects.all()
    for i in PlaceObjectLists:
        i.__dict__.update(reviewCount=random.randint(3, 12))
        i.save()

    return HttpResponse("Done Creating Reviews")



class RecipesListView(ListView):
    model = allSchedules
    template_name = "home/schedule_list.html"


class RecipesDetailView(DetailView):
    model = allSchedules
    template_name = "home/schedule_detail.html"


class ResortsDetailView(DetailView):
    from resorts.models import resortItem
    model = resortItem
    template_name = "home/resort_list.html"

class ResortsDetailView(DetailView):
    from resorts.models import resortItem
    model = resortItem
    template_name = "home/resort_detail.html"

# def ads(request):


def googleadsense(request):
    # from django.http import HttpResponse
    print('Viewing ads\n\n')
# def readfile(request):
    # openit = open("D86D3E0B01797CC0A936E2472CF4FB91.txt", 'r')
    # openit = open("4575618483167828.txt", 'r')
    # return HttpResponse('google.com, pub-4575618483167828, DIRECT, f08c47fec0942fa0')
    return HttpResponse(
    'google.com, pub-4843007524416588, DIRECT, f08c47fec0942fa0\n',
    content_type='text/plain'
)
    # hhhhh = openit.read()
    # print('Viewing ads')
    # return HttpResponse(hhhhh)
    # return render(request, 'home/ads.txt')
def calendar_html(request):
    return render(request, 'home/place_calendar.html')
@xframe_options_exempt
def carpool(request, message=False):
    request.session.setdefault('how_many_visits', 0)
    request.session['how_many_visits'] += 1
    buttons = {
        # 'allDestinations': Places_v2.objects.all(),
        'message': message,
        'include_schedule_modal': True,
    }
    return render(request, 'home/index.html', buttons)


def carpoolJOSN(request):
    # objectRecords = schedule.comments.values()
    placeJSONED = Places_v2.objects.all().values()
    return JsonResponse({"PlacesList": list(placeJSONED)})

@xframe_options_exempt
def home(request, message=False):
    # return redirect('home:checkPlaceSlug', slug='bohol-island')
    request.session.setdefault('how_many_visits', 0)
    request.session['how_many_visits'] += 1
    buttons = {
        'allDestinations': Places_v2.objects.all(),
        'message': message,
        'include_schedule_modal': True,
        'page_title': 'Paratara | Travel Guides, Carpool Schedules & Resorts',
        'meta_description': 'Find destination guides, resort stays, local events, travel notes, and shared carpool schedules with Paratara.',
        'canonical_url': request.build_absolute_uri(reverse('home:home')),
    }
    return render(request, 'home/index.html', buttons)    

# def home(request):
#     from SinglePage.views import SinglePageHome
#     return SinglePageHome(request)



def viewAllForms(request):
    return render(request, 'home/form.html')


def refreshSchedules_v2(request):
    from . import ImageGetSearch
    from datetime import date
    import time
    today = date.today()
    currentYear = int(today.year)
    currentDate = int(today.day)
    currentMonth = int(today.month)
    everySchedules = allSchedules.objects.all()
    allPlace = Places_v2.objects.all()
    for schedule in everySchedules:

        if schedule.yearN < currentYear:
            schedule.delete()
            break
        if (schedule.yearN == currentYear):
            if (schedule.monthN < currentMonth):
                schedule.delete()
                # continue
            # elif(schedule.monthN == currentMonth):
            #     if (schedule.dateN < currentDate):
            #         schedule.delete()
            elif (schedule.monthN < currentMonth):
                # if (schedule.dateN < currentDate):
                schedule.delete()
                # continue
        if (schedule.monthN == currentMonth):
            if (schedule.dateN < currentDate):
                schedule.delete()
    for eachPlace in allPlace:
        # time.sleep(2)
        if int(eachPlace.placesSchedules.count()) <= 0:
            if int(eachPlace.resortItem.count() <= 0):
                eachPlace.delete()
        elif eachPlace.placePhoto == '':
            newPhoto = ImageGetSearch.get_google_img(str(eachPlace.placename))
            eachPlace.placePhoto = newPhoto
            eachPlace.save()
            # time.sleep(2)
    return redirect('home:home')

 
def placeCalendarJSON_v2(request, id, month=None, year=None):
    """
    Get place calendar data filtered by optional month/year.
    URL: /place/<id>/ or /place/<id>/<month>/<year>/
    Returns only events and schedules for the specified month to reduce payload.
    """
    place = Places_v2.objects.get(pk=id)

    placetoCheck = place
    placetoCheck.reviewCount += 1
    placetoCheck.save()    
    
    from django.core import serializers
    from datetime import date
    
    # If month/year not provided, use current month
    if month is None or year is None:
        today = date.today()
        month = month or today.month
        year = year or today.year
    
    # Filter schedules by month and year

    scheduleList = place.placesSchedules.filter(
        monthN=month,
        yearN=year
    ).order_by('dateN')
    # scheduleList = allSchedules.objects.filter(
    #     schedulePlace=id,
    #     monthN=month,
    #     yearN=year
    # ).order_by('dateN')
    # Filter events by month and year
    event_objs = place.eventList.filter(monthN=month, yearN=year).order_by('dateN')
    # Resorts: keep payload light (only name + link)
    resorts_qs = place.resortList.values('RealName', 'name', 'slug', 'websiteURL')
    
    data = serializers.serialize('json', scheduleList, indent=2,
                                 use_natural_foreign_keys=False, use_natural_primary_keys=True)
    schedule_list = json.loads(data)
    

    # Removed Resorts
    # Optimize: Get only essential resort fields without heavy M2M relationships
    # Format as Django serializer output to match frontend expectations
    # resorts_qs = place.resortList.all().values(
    #     'id', 'name', 'RealName', 'address', 'description', 
    #     'contactNumber', 'contactEmail', 'headerImage', 
    #     'latitude', 'longitude', 'reviews', 'slug', 'websiteURL'
    # )
    
    # # Convert to Django serializer format: [{model: ..., pk: ..., fields: {...}}]
    # resort_list = [
    #     {
    #         'model': 'resorts.resortitem',
    #         'pk': resort['id'],
    #         'fields': {
    #             'name': resort['name'],
    #             'RealName': resort['RealName'],
    #             'address': resort['address'],
    #             'description': resort['description'],
    #             'contactNumber': resort['contactNumber'],
    #             'contactEmail': resort['contactEmail'],
    #             'headerImage': resort['headerImage'],
    #             'latitude': resort['latitude'],
    #             'longitude': resort['longitude'],
    #             'reviews': resort['reviews'],
    #             'slug': resort['slug'],
    #             'websiteURL': resort['websiteURL']
    #         }
    #     }
    #     for resort in resorts_qs
    # ]     
    

    def _is_http_url(val) -> bool:
        return bool(val) and isinstance(val, str) and (val.startswith('http://') or val.startswith('https://'))

    resort_list = []
    for r in resorts_qs:
        display_name = (r.get('RealName') or r.get('name') or '').strip() or 'Resort'
        resort_slug = (r.get('slug') or r.get('name') or '').strip()
        if _is_http_url(r.get('websiteURL')):
            link = r.get('websiteURL')
        elif place.slug and resort_slug:
            link = reverse('home:resort_by_slugs', kwargs={'place_slug': place.slug, 'resort_slug': resort_slug})
        else:
            link = None

        resort_list.append({'name': display_name, 'link': link})
    event_data = serializers.serialize(
        'json',
        event_objs,
        use_natural_foreign_keys=False,
        use_natural_primary_keys=True
    )
    event_list = json.loads(event_data)
    
    response_data = {
        'placeSchedule': schedule_list,
        'placeName': place.placename,
        'placeResorts': resort_list,
        'placeEvents': event_list,
        'month': month,
        'year': year,
        'scheduleCount': len(schedule_list),
        'eventCount': len(event_list),
        'resortCount': len(resort_list)
    }    
    return HttpResponse(json.dumps(response_data, indent=2), content_type="application/json")


@require_POST
def create_schedule_for_place(request, place_id):
    trace_id = uuid.uuid4().hex[:8]
    print(f"Creating schedule for place {place_id} ({trace_id})")
    try:
        place = Places_v2.objects.get(pk=place_id)
    except Places_v2.DoesNotExist:
        print(f"Place {place_id} not found ({trace_id})")
        return JsonResponse({'error': 'Place not found'}, status=404)

    try:
        payload = json.loads(request.body or '{}') if request.body else {}
    except json.JSONDecodeError:
        print(f"Invalid JSON, using POST data ({trace_id})")
        payload = {}

    def _get(key, default=None):
        return payload.get(key, request.POST.get(key, default)) if isinstance(payload, dict) else request.POST.get(key, default)

    valid_types = {choice[0] for choice in allSchedules.SCHEDULE_TYPE_CHOICES}
    schedule_type = (_get('scheduleTypeAndMode') or '').strip()
    if schedule_type and schedule_type not in valid_types:
        print(f"Invalid schedule type: {schedule_type} ({trace_id})")
        return JsonResponse({'error': 'Invalid scheduleTypeAndMode'}, status=400)

    def _to_int(val, default):
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    today = datetime.now()
    dateN = _to_int(_get('dateN'), today.day)
    monthN = _to_int(_get('monthN'), today.month)
    yearN = _to_int(_get('yearN'), today.year)
    meetPlace = (_get('meetPlace') or '').strip()
    endPlace = (_get('endPlace') or '').strip()
    meetTime = (_get('meetTime') or '').strip()
    details_contact = (_get('detailsContact') or '').strip()
    maker_or_looker = (_get('MakerOrLooker') or 'Make').strip()
    print(f"Schedule date: {monthN}/{dateN}/{yearN} ({trace_id})")

    if not meetPlace:
        print(f"Missing meet place ({trace_id})")
        return JsonResponse({'error': 'meetPlace is required'}, status=400)
    if not endPlace:
        print(f"Missing end place ({trace_id})")
        return JsonResponse({'error': 'endPlace is required'}, status=400)

    poster = request.user if request.user.is_authenticated else None
    poster_name = poster.username if poster else 'Anonymous'
    poster_id = poster.id if poster else 0

    print(f"Saving schedule for {place.placename} ({trace_id})")
    new_schedule = allSchedules.objects.create(
        scheduleTypeAndMode=schedule_type or None,
        dateN=dateN,
        monthN=monthN,
        yearN=yearN,
        schedulePlace=place,
        meetPlace=meetPlace,
        endPlace=endPlace,
        meetTime=meetTime or None,
        poster=poster,
        posterName=poster_name,
        posterID=poster_id,
        MakerOrLooker=maker_or_looker or 'Make',
        scheduleTravelType=schedule_type or 'carpool',
        detailsContact=details_contact,
    )
    new_schedule.scheduleID = new_schedule.id
    new_schedule.save(update_fields=['scheduleID'])
    
    place.placesSchedules.add(new_schedule)
    place.save()

    place_schedule_count = place.placesSchedules.count()
    print(f"Created schedule {new_schedule.id} ({trace_id})")
    
    # Verify the schedule was actually saved with proper relationships
    # verify_schedule = allSchedules.objects.filter(id=new_schedule.id).select_related('schedulePlace').first()
    # if verify_schedule:
    #     print(f"[create_schedule_for_place:{trace_id}] verified: schedule exists, place={verify_schedule.schedulePlace.placename if verify_schedule.schedulePlace else 'None'}")
    print(f"Meet time: {new_schedule.meetTime or 'N/A'} ({trace_id})")
    return JsonResponse(
        {
            'id': new_schedule.id,
            'message': 'Schedule created',
            'scheduleTypeAndMode': new_schedule.scheduleTypeAndMode,
            'dateN': new_schedule.dateN,
            'monthN': new_schedule.monthN,
            'yearN': new_schedule.yearN,
            'meetTime': new_schedule.meetTime,
            'placeScheduleCount': place_schedule_count,
        },
        status=201,
    )

# from webSchedule.utils import getPlacePhoto
from imageapp.imageuploader import getPlacePhoto
# # Make list_of_tourist_spot a key object where each list of tourist spots should be [{'name':'namevalue','latitude':'latvalue','longitude':'longvalue','picture':'picturevalue'}]
def make_list_of_tourist_place(placename):
    """
    Return tourist spots as:
    [
        {
            'name': 'Spot Name',
            'latitude': '0.000',
            'longitude': '0.000',
        }
    ]
    """

    prompt = f"""
            List all most famous and under rated tourist spots in {placename}. maximum of 10

            Return ONLY a valid Python list like this:

            [
                {{
                    "name": "Spot Name",
                    "latitude": "0.000",
                    "longitude": "0.000",
                    
                }}
            ]

            No explanation.
            """

    try:
        response = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Return ONLY a valid Python list of dictionaries."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            temperature=0.3,
            max_tokens=2048,
        )

        gpt_reply = response.choices[0].message.content.strip()
        usage = getattr(response, 'usage', None)

        if usage is not None:
            print("Prompt tokens:", usage.prompt_tokens)
            print("Completion tokens:", usage.completion_tokens)
            print("TOURIST PLACES Total tokens:", usage.total_tokens)
        else:
            print("TOURIST PLACES usage info not available")
        print('-----------------')      


        import ast

        # Remove markdown code blocks
        gpt_reply = gpt_reply.strip("` \n")

        if gpt_reply.startswith("python"):
            gpt_reply = gpt_reply[6:].strip()

        places = ast.literal_eval(gpt_reply)

        if not isinstance(places, list):
            return []

        cleaned_places = []

        for place in places:
            if isinstance(place, dict):
                cleaned_places.append({
                    "name": str(place.get("name", "")).strip(),
                    "latitude": str(place.get("latitude", "")).strip(),
                    "longitude": str(place.get("longitude", "")).strip(),
                    "picture": getPlacePhoto(None,str(place.get("name", "")).strip()),
                    
                })

        return cleaned_places

    except Exception as e:
        print(f"[GPT-PLACES] Error: {e}")

        return [
            {
                "name": f"{placename} Main Attraction",
                "latitude": "",
                "longitude": "",
                "picture": "",
            }
        ]

def get_image_url_from_search(query):
    from ddgs import DDGS

    # 'max_results' set to 1 to get the top hit
    with DDGS() as ddgs:
        results = [r for r in ddgs.images(query, max_results=1)]
        if results:
            return results[0]['image']
    return None


    # import requests
    # from bs4 import BeautifulSoup
    # from urllib.parse import urljoin, urlparse
    # # Format the query for a DuckDuckGo image search
    # search_url = f"https://duckduckgo.com{query}&t=h_&iax=images&ia=images"
    
    # # Use a common User-Agent to prevent being immediately blocked
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    # }

    # print(f"Searching DuckDuckGo for: {query}")
    
    # try:
    #     response = requests.get(search_url, headers=headers, timeout=10)
    #     response.raise_for_status() # Raise an exception for bad status codes

    #     soup = BeautifulSoup(response.content, 'html.parser')

    #     # DuckDuckGo wraps its main images in <img> tags inside <div> with specific classes
    #     # The specific CSS selectors can change over time, but this is a common pattern:
    #     # We look for a common HTML pattern where the image source is stored.
        
    #     # A specific snippet from search results suggests the image URL is sometimes
    #     # stored in an attribute like 'data-src' or is a relative URL starting with '//'

    #     # Trying to find the first large image link:
    #     first_img_tag = soup.find('img', {'class': 'tile--img__img'})
        
    #     if first_img_tag and 'src' in first_img_tag.attrs:
    #         relative_url = first_img_tag['src']
    #         # Ensure we have an absolute URL
    #         if relative_url.startswith('//'):
    #             full_url = f"https:{relative_url}"
    #             return full_url
    #         elif relative_url.startswith('http'):
    #             return relative_url

    # except requests.exceptions.RequestException as e:
    #     print(f"Error during request: {e}")
    #     return None
    # except Exception as e:
    #     print(f"An error occurred during parsing: {e}")
    #     return None

    # return "Could not find a suitable image URL. Selectors might be outdated."


@csrf_exempt
def fill_tourist_spot_images(request):
    """Admin helper: populate `TouristSpot.img` using `getPlacePhoto`.

    - Staff-only: returns HTTP 403 if not staff.
    - Iterates all TouristSpot objects; for those with empty `img`, attempts
      to fetch a photo using `getPlacePhoto(request, "<spot> <place>")` and
      saves it.
    - Returns a JSON summary of updated records.
    """
    from django.http import HttpResponseForbidden
    from .models import TouristSpot



    if not getattr(request, 'user', None) or not request.user.is_staff:
        return HttpResponseForbidden('staff only')

    updated = []
    for spot in TouristSpot.objects.select_related('place').all():
        try:
            print(f"Processing TouristSpot id={spot.id} name={spot.name!r} place={getattr(spot.place,'placename','')!r}")

            if spot.img:
                print(f"  Skipping: already has img -> {spot.img}")
                continue

            # Prefer spot name first, then "<spot> <place>". If still none,
            # fall back to `get_image_url_from_search` which scrapes an image URL.
            photo = None

            # 1) Try spot name via getPlacePhoto
            print("  Attempt 1: getPlacePhoto(spot.name)")
            try:
                photo = getPlacePhoto(request, spot.name)
                print("   -> result:", "FOUND" if photo else "None")
            except Exception as e:
                photo = None
                print("   -> exception:", repr(e))

            # 2) Try "<spot> <place>" via getPlacePhoto
            if not photo:
                query = f"{spot.name} {getattr(spot.place, 'placename', '')}".strip()
                if query:
                    print(f"  Attempt 2: getPlacePhoto(query={query!r})")
                    try:
                        photo = getPlacePhoto(request, query)
                        print("   -> result:", "FOUND" if photo else "None")
                    except Exception as e:
                        photo = None
                        print("   -> exception:", repr(e))

            # 3) Fallback to local HTML search utility if still no photo
            if not photo:
                print(f"  Attempt 3: get_image_url_from_search(spot.name={spot.name!r})")
                try:
                    photo = get_image_url_from_search(spot.name)
                    print("   -> result:", "FOUND" if photo else "None")
                except Exception as e:
                    photo = None
                    print("   -> exception:", repr(e))

            if not photo:
                query = f"{spot.name} {getattr(spot.place, 'placename', '')}".strip()
                if query:
                    print(f"  Attempt 4: get_image_url_from_search(query={query!r})")
                    try:
                        photo = get_image_url_from_search(query)
                        print("   -> result:", "FOUND" if photo else "None")
                    except Exception as e:
                        photo = None
                        print("   -> exception:", repr(e))

            if photo:
                spot.img = photo
                spot.save(update_fields=['img'])
                updated.append({'id': spot.id, 'name': spot.name, 'img': photo})
                print(f"  Updated TouristSpot {spot.id} {spot.name!r} -> {photo}")
            else:
                print(f"  No photo found for TouristSpot {spot.id}: {spot.name}")
        except Exception as e:
            print(f"Error updating TouristSpot {getattr(spot, 'id', 'unknown')}: {e}")

    return JsonResponse({'updated_count': len(updated), 'updated': updated})


@csrf_exempt
def viaje_v2(request):
    if not request.user.is_authenticated:
        return redirect('userProfile:profile')
    if request.method == 'POST':
        print(request.POST)
        place = request.POST.get('placenameschedule')

        try:
            newPlace = Places_v2.objects.get(placename__iexact=place)
        except:
            print('place could not be found,\n.   creating new place: \n       ', place)
            # if failed to save add placeID=1
            place = ' '.join([f.capitalize() for f in place.split(' ')])
            newPlace = Places_v2.objects.create(placename=place)
            try:
                import re
                from resorts.models import resortItem as resort
                for r in resort.objects.all():
                    if re.search(r.province, newPlace.placename, re.IGNORECASE):
                        newPlace.resortItem.add(r)
            except:
                pass
            # End Adding Resort
            # getPlacePhoto(request, place)
            newPlace.placePhoto = getPlacePhoto(request, place)
            
            print("new place photo")
            print('Photo URL: ', newPlace.placePhoto)
            import time
            time.sleep(5)
            newPlace.save()
            newPlace.placeID = newPlace.id
            newPlace.save()
            # Finding / Adding Resort

            # list_of_tourist_spots = make_list_of_tourist_place(place)
            # # Make list_of_tourist_spot a key object where each list of tourist spots should be [{'name':'namevalue','latitude':'latvalue','longitude':'longvalue','picture':'picturevalue'}]
            # for idx, tourist_spot in enumerate(list_of_tourist_spots):
            #     print(f"[TOURIST-SPOT] ({idx+1}/{len(list_of_tourist_spots)}) Preparing to add: {tourist_spot}")
            #     data = request.POST.copy()
            #     print(f"[TOURIST-SPOT] Copied POST data: {dict(data)}")
            #     data['place'] = newPlace.id

                
            #     print(f"[TOURIST-SPOT] Set to: {tourist_spot}")
            #     # print(f"[TOURIST-SPOT] Calling create_tourist_spot with data: {{'place': {data['place']}, 'name': {data['name']}}}")
            #     data.method = 'POST'
            #     data.META = request.META
            #     data['name'] = tourist_spot['name']
            #     data['latitude'] = tourist_spot['latitude']
            #     data['longitude'] = tourist_spot['longitude']
            #     create_tourist_spot(data)
            #     print(f"[TOURIST-SPOT] Finished create_tourist_spot for: {tourist_spot}\n")


        allMeetDate = request.POST.getlist('meetDate')

        poster = ensure_user_profile(request.user)
        for eachDate in allMeetDate:

            newSchedule = allSchedules()
            newSchedule.posterVerified = poster.verified
            newSchedule.posterReputation = poster.reputations
            departureDate = eachDate
            departureDate = departureDate.split('-')
            try:
                newSchedule.posterName = request.user.username
                newSchedule.posterID = request.user.id
                newSchedule.poster = poster
                if poster.photo:
                    newSchedule.posterImageURL = poster.photo
                poster.posts.add(newSchedule)

            except:
                pass
            # meet_date_str = request.POST.get('meetDate')
            
            dt = datetime.fromisoformat(eachDate)

            newSchedule.yearN = dt.year
            newSchedule.monthN = dt.month
            newSchedule.dateN = dt.day
            # newSchedule.meetTime = str(dt.time())  
            print("DATE AND TIME: ", dt, type(dt), dt.time()    )
            newSchedule.meetTime = dt.strftime("%I:%M %p")          
            # print("DATE AND TIME: ", dt, type(dt), dt.time()    )
            # newSchedule.meetTime = departureDate['time']
            # newSchedule.dateN = departureDate[2]
            # newSchedule.monthN = departureDate[1]
            # newSchedule.yearN = departureDate[0]
            newSchedule.meetPlace = request.POST.get('meetPlace').title()

            if request.POST.get('scheduleCost'):
                newSchedule.scheduleCost = request.POST.get('scheduleCost')
            if request.POST.get('theDetails'):
                newSchedule.otherDetails = request.POST.get('theDetails')
            if request.POST.get('instagramUsername'):
                newSchedule.posterInstagram = request.POST.get(
                    'instagramUsername') 
            # try:
            #     newSchedule.detailsContact = request.user.email
            # except:
            newSchedule.detailsContact = request.POST.get('detailsContact')
            newSchedule.schedulePlace = newPlace
            if request.POST.get('MakerOrLooker'):
                newSchedule.MakerOrLooker = request.POST.get('MakerOrLooker')
            # if request.POST.get('meetTime') != '':
            #     newSchedule.meetTime = request.POST.get('meetTime')
            if request.POST.get('additionalDetails'):
                newSchedule.additionalDetails = request.POST.get(
                    'additionalDetails')
            try:
                newSchedule.scheduleWebsite = request.POST.get(
                    'scheduleWebsite')
            except:
                pass
            newSchedule.scheduleTravelType = request.POST.get(
                'scheduleTravelType')  # RIDE BIKE options
            newSchedule.save()
            # try:
            #     theType = SchedTypeAndMode.objects.get_or_create(
            #         modeName=newSchedule.scheduleTravelType)[0]
            # except: 
            #     theType = SchedTypeAndMode.objects.filter(
            #         modeName=newSchedule.scheduleTravelType)[0]
            # theType.scheduleObject.add(newSchedule)  # adding to types and mode
            # theType.save()
            newSchedule.scheduleTypeAndMode = request.POST.get('scheduleTypeAndMode')
            newSchedule.scheduleID = newSchedule.id
            # newSchedule.scheduleTypeAndMode = theType
            newSchedule.save()
            newPlace.placesSchedules.add(newSchedule)
            try:
                poster.posts.add(newSchedule)
                poster.reputations += 2
                poster.save()
            except:
                pass

        from datetime import date
        today = date.today()
        return redirect('home:place', newPlace.id, int(today.month), int(today.year))


def destinations_v2(request):
    from datetime import date
    today = date.today()
    currentYear = int(today.year)
    items = {
        'allDestinations': Places_v2.objects.all(),
        'currentMonth': int(today.month),
        'currentYear': int(today.year)
    }
    if request.method == 'POST':
        place = request.POST.get('place')
        if place == '':
            return redirect('home:destinations')
        # if failed to save add placeID=0
        currentMonth = int(today.month)
        newPlace = Places_v2.objects.create(placename=place)
        newPlace.placePhoto = getPlacePhoto(request, place)
        newPlace.save()
        newPlace.placeID = newPlace.id
        newPlace.save()
        return redirect('home:place', newPlace.id, currentMonth, currentYear)
    return render(request, 'home/destination.html', items)

def checkPlace_v2(request, placename=None, slug=None):
    print('Checking Place v2              ---------- ', placename, slug)
    if slug:
        place = get_object_or_404(Places_v2, slug=slug)
    elif placename:
        place = get_object_or_404(Places_v2, placename=placename)    
# def checkPlace_v2(request, placename):
    import calendar
    from datetime import date
    today = date.today()
    todayMonth = int(today.month)
    todayYear = int(today.year)
    try:

        placetoCheck = place
        placetoCheck.reviewCount += 1
        placetoCheck.save()
    except:
        return carpool(request, placename)
        # return redirect('home:home',message='Empty')
    return redirect('home:place', placetoCheck.id, todayMonth, todayYear)


# def place_v2(request, id, currentMonth, currentYear):
def place_url(request, placenameURL=None):
    from datetime import date
    today = date.today()

    cp = Places_v2.objects.get(slug=placenameURL)
    return place_v2(
        request,
        placenameURL=placenameURL,
        id=cp.id,
        currentMonth=int(today.month),
        currentYear=int(today.year),
    )

def place_by_slug(request, place_slug, year=None, month=None):
    from datetime import date
    today = date.today()
    render_month = month or today.month
    render_year = year or today.year
    place = get_object_or_404(Places_v2, slug=place_slug)
    return place_v2(
        request,
        placenameURL=place_slug,
        id=place.id,
        currentMonth=render_month,
        currentYear=render_year,
    )


def place_v2(request, placenameURL=None ,id=None, currentMonth=1, currentYear=1):
    
    import calendar
    from datetime import date
    thisMonth = calendar.HTMLCalendar(calendar.SUNDAY)
    today = date.today()
    todaysMonth = int(today.month)
    currentDate = int(today.day)
    place = None
    if id:
        place = Places_v2.objects.filter(id=id).first()
    if not place and placenameURL:
        place = Places_v2.objects.filter(slug=placenameURL).first()
    if place:
        placenameURL = placenameURL or place.slug
        id = id or place.id
    if (currentMonth >= 13):
        currentMonth = 1
        currentYear += 1
    elif (currentMonth <= 0):
        currentMonth = 12
        currentYear -= 1
    prev_month = currentMonth - 1
    prev_year = currentYear
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    next_month = currentMonth + 1
    next_year = currentYear
    if next_month > 12:
        next_month = 1
        next_year += 1
    showCalendar = thisMonth.formatmonth(currentYear, currentMonth)

    # Resorts can be linked in two ways in this codebase:
    # 1) Place.resortItem (M2M)
    # 2) ResortItem.place (FK, reverse name: EstablishmentPlace)
    # Older records sometimes only have the FK populated, so we merge both.
    # place_resorts = []
    # if place:
    #     try:
    #         place_resorts = (place.resortItem.all() | place.EstablishmentPlace.all()).distinct()
    #     except Exception:
    #         place_resorts = place.resortItem.all()

    context = {
        'todaysMonth': todaysMonth,
        'calendar': showCalendar,
        'placeid': id,
        'currentMonth': currentMonth, 
        'currentDate': currentDate,
        'nextMonth': next_month,
        'previousMonth': prev_month,
        'currentYear': currentYear,
        'nextYear': next_year,
        'previousYear': prev_year,
        'placeResorts': ['asd','asds'],
        'place_slug': placenameURL or (place.slug if place else None),
    }
    if place:
        place_url_path = reverse('home:place_by_slug', kwargs={'place_slug': place.slug})
        place_photo_url = _absolute_public_url(request, place.placePhoto)
        context.update({
            'place': place,
            'page_title': f'{place.placename} Travel Guide, Resorts & Schedules | Paratara',
            'meta_description': (
                f'Discover {place.placename} travel guides, resort options, local events, '
                'tourist spots, and shared trip schedules with Paratara.'
            ),
            'canonical_url': request.build_absolute_uri(place_url_path),
            'meta_image_url': place_photo_url or DEFAULT_META_IMAGE_URL,
            'image_alt': f'Travel planning for {place.placename} on Paratara',
        })
 
    try:
        from .models import CommunityBulletinPost

        if place and place.id:
            community_bulletins = (
                CommunityBulletinPost.objects
                .filter(place_id=place.id)
                .prefetch_related('images')
                .order_by('-created_at')[:20]
            )
        else:
            community_bulletins = []
        context['community_bulletins'] = community_bulletins
    except Exception:
        context['community_bulletins'] = []

    return render(request, 'home/place.html', context)
    # did not made the new schedule form ,, Make it from a new functino
# MAKE FUNCTION FOR NEW SCHEDULE FROM THE FORM


def addScheduleReview(request, scheduleID):
    try:
        toAddReview = allSchedules.objects.get(scheduleID=scheduleID)
        toAddReview.reviewCount += 1
        toAddReview.save()
        return HttpResponse('Added', content_type="application/json")
    except:
        return HttpResponse('Failed', content_type="application/json")


def community_bulletin_list(request, place_id: int):
    # If place_id is a string (not an integer), try to find the place by placename and set place_id to its id
    print('community_bulletin_list called with place_id:', place_id)
    if isinstance(place_id, str) and not place_id.isdigit():
        from .models import Places_v2
        place_obj = Places_v2.objects.filter(placename__iexact=place_id).first()
        if place_obj:
            place_id = place_obj.id
        else:
            return JsonResponse({'error': 'Place not found'}, status=404)
    # ...existing code...
    from .models import CommunityBulletinPost
    print('Fetching CommunityBulletinPost for place_id:', place_id)
    posts = (
        CommunityBulletinPost.objects
        .filter(place_id=place_id)
        .prefetch_related('images')
        .order_by('-created_at')[:50]
    )

    data = []
    print('Processing posts for JSON response...')
    for p in posts:
        data.append(
            {
                'id': p.id,
                'place_id': p.place_id,
                'ip_address': p.ip_address,
                'ai_title': p.ai_title,
                'ai_description': p.ai_description,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'images': [img.image_url for img in p.images.all() if img.image_url],
            }
        )

    return JsonResponse({'posts': data})


@require_POST
def community_bulletin_upload(request, place_id: int):
    print('community_bulletin_upload called with place_id:', place_id)
    from .models import Places_v2, CommunityBulletinPost, CommunityBulletinImage
    try:
        from .community_bulletin_ai import analyze_bulletin_post_from_images
    except Exception:
        analyze_bulletin_post_from_images = None
    from webSchedule.utils import upload_to_imgbb, upload_to_imgbb_with_metadata
    from django.http import HttpResponseForbidden
    print('Checking authentication for user:', getattr(request.user, 'username', None))
    if not request.user.is_authenticated:
        print('User not authenticated; returning 403')
        return HttpResponseForbidden('Login required')

    place = get_object_or_404(Places_v2, id=place_id)
    print('Found place:', place.placename)
    uploaded = request.FILES.getlist('images')
    if not uploaded:
        return _redirect_back_with_params(request, cb_error='no_images')

    ip = _get_client_ip(request)

    # Read bytes first (before saving) so AI generation has access.
    image_bytes_list = []
    print('Reading uploaded files for AI analysis...')
    for f in uploaded[:4]:
        try:
            image_bytes_list.append(f.read())
        except Exception:
            image_bytes_list.append(b'')
        try:
            f.seek(0)
        except Exception:
            pass

    if analyze_bulletin_post_from_images:
        analysis = analyze_bulletin_post_from_images(image_bytes_list)
    else:
        analysis = {
            'title': 'Community bulletin',
            'description': 'Photos shared by the community.',
            'has_words': True,
            'is_spam': False,
        }
    print('AI analysis result:', analysis)
    if analysis.get('is_spam'):
        print('AI flagged as spam; rejecting upload')
        return _redirect_back_with_params(request, cb_error='spam')
    if not analysis.get('has_words'):
        print('AI analysis found no words; rejecting upload')
        return _redirect_back_with_params(request, cb_error='no_words')

    title = (analysis.get('title') or 'Community bulletin')
    description = (analysis.get('description') or '')
    print(' Creating CommunityBulletinPost with title:', title)
    post = CommunityBulletinPost.objects.create(
        place=place,
        ip_address=ip,
        ai_title=title,
        ai_description=description,
    )

    for f in uploaded:
        try:
            meta = upload_to_imgbb_with_metadata(f)
            url = meta.get('url') if isinstance(meta, dict) else None
            if not url:
                url = upload_to_imgbb(f)
                meta = {}
            if url:
                CommunityBulletinImage.objects.create(
                    post=post,
                    image_url=url,
                    imgbb_delete_hash=(meta.get('delete_hash') if isinstance(meta, dict) else None),
                    imgbb_delete_url=(meta.get('delete_url') if isinstance(meta, dict) else None),
                )
        except Exception:
            continue

    return _redirect_back_with_params(request, cb_success='1')


@require_POST
def community_bulletin_delete(request, place_id: int, post_id: int):
    from .models import CommunityBulletinPost
    from webSchedule.utils import delete_imgbb_image
    from django.http import HttpResponseForbidden

    if not request.user.is_authenticated:
        return HttpResponseForbidden('Login required')

    post = get_object_or_404(CommunityBulletinPost, id=post_id, place_id=place_id)

    # Best-effort remote delete; if we don't have delete_hash (older posts), we can only delete the DB records.
    try:
        for img in post.images.all():
            if getattr(img, 'imgbb_delete_hash', None):
                delete_imgbb_image(img.imgbb_delete_hash)
    except Exception:
        pass

    post.delete()


def facebook_posts(request):
    """Render Facebook posts imported into home.FacebookPagePost."""
    from .models import FacebookPagePost

    posts = FacebookPagePost.objects.all().order_by('-created_time', '-imported_at')[:50]
    return render(request, 'home/facebook_posts.html', {
        'posts': posts,
        'page_title': 'Facebook Posts | Paratara',
        'meta_description': 'Recent Facebook posts imported into Paratara.',
        'canonical_url': request.build_absolute_uri(reverse('home:facebook_posts')),
        'robots_meta': 'noindex, follow',
    })


@csrf_exempt
def Comment(request, postID):
    from .models import Comment
    schedule = allSchedules.objects.get(scheduleID=postID)
    from django.http import JsonResponse
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        userName = request.user.username
        if not request.user.username:
            userName = 'Anonymous'
        commentObject = Comment.objects.create(senderID=request.user.id, sender=request.user, message=data.get(
            'message'), messanger=userName, schedule=schedule)
        schedule.comment.add(commentObject)
        schedule.save()
    elif request.method == 'GET':
        # RETURN SCHEDULE COMMENTS
        # from django.core import serializers
        # data = serializers.serialize('json', schedule.comments)
        objectRecords = schedule.comments.values()
        return JsonResponse({"commentList": list(objectRecords)})




@csrf_exempt
def discussion_new(request, placeID):
    print('Discussion NEW depreciated')
    return
    try:
        place = Places_v2.objects.get(placeID=placeID)
    except Places_v2.DoesNotExist:
        return JsonResponse({"error": "Place not found"}, status=404)

    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "").strip()
        if not message:
            return JsonResponse({"error": "Message is empty"}, status=400)

        if request.user.is_authenticated:
            ensure_user_profile(request.user)

        # Save user discussion
        discuss = PlaceDiscussion.objects.create(
            discuss=message,
            place=place,
            discusserName=request.user.username if request.user.is_authenticated else "Anonymous"
        )
        place.discussion.add(discuss)

        # OpenAI response based on place name
        prompt = f"""
You are a travel assistant specialized in the place: {place.name}.
A user asked: "{message}"
Respond concisely (max 150 words) and informatively.
"""

        try:
            ai_response = client.chat.completions.create(
                model=settings.GROK_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )
            ai_message = ai_response.choices[0].message.content.strip()

            # Save AI response as discussion
            ai_discuss = PlaceDiscussion.objects.create(
                discuss=ai_message,
                discusserName="AI Bot",
                place=place
            )
            place.discussion.add(ai_discuss)

        except Exception as e:
            ai_message = f"Error getting AI response: {str(e)}"

        # Return all discussions (latest first)
        objectRecords = place.discussions.order_by('-id').values()
        return JsonResponse({"response": list(objectRecords)})

    elif request.method == "GET":
        objectRecords = place.discussions.order_by('-id').values()
        return JsonResponse({"response": list(objectRecords)})

# def _legacy_grok_discussion_unused(request, placeID):
#     from datetime import timedelta
#     from django.utils import timezone
#     import uuid
#     from openai import OpenAI
#     def _step(description):
#         print(f"[Discussion] {description}")
#     _step(f"START method={request.method}")
    
#     client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
#     _step("OpenAI client initialized")

#     _step("Parsing request body as JSON")
#     data = json.loads(request.body)
#     _step(f"Parsed JSON keys={list(data.keys())}")

#     _step("Loading place by placeID")
#     place = Places_v2.objects.get(placeID=placeID)
#     _step(f"Loaded place placename={getattr(place, 'placename', None) or getattr(place, 'name', None)}")

#     if data.get('message') != '':
#         if request.method == 'POST':
#             message_content = data.get('message', '').strip()
            
#             # Basic validation
#             if len(message_content) < 2:
#                 return JsonResponse({"error": "Message too short", "response": []}, status=400)
            
#             if len(message_content) > 1000:
#                 return JsonResponse({"error": "Message too long", "response": []}, status=400)

#             # SPAM PROTECTION 1: Rate limiting - max 5 messages per minute
#             one_minute_ago = timezone.now() - timedelta(minutes=1)
#             _step("SpamCheck#1: rate limit window=1min")
#             recent_messages = PlaceDiscussion.objects.filter(
#                 place=place,
#                 timestamp__gte=one_minute_ago
#             )            
#             # Get user identifier (IP or userID)
#             user_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR', '')
#             user_identifier = data.get('userID') or user_ip
#             _step(f"User identified via {'userID' if data.get('userID') else 'ip'}")
            

            
#             # Count messages from this user/IP
#             user_recent_count = recent_messages.filter(
#                 discusserName=data.get('username', 'Anonymous')
#             ).count()
#             _step(f"SpamCheck#1: recent_count={user_recent_count}")
            
#             if user_recent_count >= 5:
#                 _step("Rate limited: >=5 messages/min")
#                 return JsonResponse({"error": "Rate limit exceeded. Please wait before sending more messages.", "response": []}, status=429)
            
#             # SPAM PROTECTION 2: Duplicate message detection (within 5 minutes)
#             five_minutes_ago = timezone.now() - timedelta(minutes=5)
#             _step("SpamCheck#2: duplicate window=5min")
#             duplicate_exists = PlaceDiscussion.objects.filter(
#                 place=place,
#                 discuss__iexact=message_content,
#                 timestamp__gte=five_minutes_ago
#             ).exists()
#             _step(f"SpamCheck#2: duplicate_exists={duplicate_exists}")
            
#             if duplicate_exists:
#                 _step("Blocked: duplicate message")
#                 return JsonResponse({"error": "Duplicate message detected. Please wait before sending the same message.", "response": []}, status=400)
            
#             # SPAM PROTECTION 3: Minimum time between messages from same user (10 seconds)
#             ten_seconds_ago = timezone.now() - timedelta(seconds=10)
#             _step("SpamCheck#3: min interval=10s")
#             recent_user_message = recent_messages.filter(
#                 discusserName=data.get('username', 'Anonymous'),
#                 timestamp__gte=ten_seconds_ago
#             ).exists()
#             _step(f"SpamCheck#3: recent_user_message={recent_user_message}")
            
#             if recent_user_message:
#                 _step("Rate limited: sent message <10s ago")
#                 return JsonResponse({"error": "Please wait 10 seconds between messages.", "response": []}, status=429)
            


#             # Early local check: Is user asking something or just chatting?
#             _step("Early local check: determining message type")
#             print(f'Received message: "{message_content}"')
#             print('---')
            
#             # Initialize variables to avoid UnboundLocalError if early check fails
#             is_about_blogs = False
#             blog_context = ""
#             message_lower = message_content.lower()
            
#             try:


#                 # Check response type
#                 message_lower = message_content.lower()
            
#                 def Checkblog(human_message_prompt,place):
#                     # Combined AI processing with one call
#                     blog_keywords = ['create a blog','make a guide', 'make a blog']
#                     _step('is about blog')
#                     is_about_blogs = any(keyword in human_message_prompt for keyword in blog_keywords)
#                     # If user explicitly asks to create a blog/article, we should generate a new one
#                     # even if generic words match existing blog titles (e.g., "guide").
#                     create_blog_verbs = ['make', 'create', 'write', 'generate']
#                     create_blog_phrases = ['make a blog', 'create a blog', 'write a blog', 'generate a blog', 'make blog', 'create blog', 'write blog', 'generate blog']
#                     wants_new_blog = (
#                         any(p in human_message_prompt for p in create_blog_phrases)
#                         or ('blog' in human_message_prompt and any(v in human_message_prompt for v in create_blog_verbs))
#                         or ('article' in human_message_prompt and any(v in human_message_prompt for v in create_blog_verbs))
#                     )
                    
#                     if is_about_blogs or wants_new_blog:
#                         _step("Its About Blogs/Articles")
#                         import re
#                         from difflib import SequenceMatcher
#                         blogs = list(place.blogs.all())
#                         matched_blogs = []
#                         created_or_matched_blog_url = ""
#                         # direct token and n-gram matching
#                         _step(f"Checking blog:   {message_lower}")
#                         print('---')
#                         for b in blogs:
#                             text = f"{getattr(b,'title','')} {getattr(b,'summarize','') or ''}".lower()
#                             sim = SequenceMatcher(a=message_lower, b=text).ratio()
#                             _step(f"          Checking blog:   {sim}    {b.title}")
#                             if sim > 0.7:
#                                 matched_blogs.append((b, [f'fuzzy:{sim:.2f}']))
#                                 _step(f"DEBUG: fuzzy matched {b.title} (sim={sim:.2f})")
#                                 _step('---------Adding to Existing Blog')
#                         max_match_blog = 1
#                         _step(f"Checking if blog matched is >= {max_match_blog}")
#                         if len(matched_blogs) >= max_match_blog:
#                             print('\n\nMatched Blogs: ',matched_blogs)
#                             _step(f"Blog flow: matched {len(matched_blogs)} existing blog(s)")
#                             print(f"Found {len(matched_blogs)} relevant blogs/articles.\n\n")
#                             blog_context = "\n\nAvailable Blogs & Articles:\n"
#                             current_domain = request.build_absolute_uri('/').rstrip('/')
#                             from django.utils.text import slugify
                            
#                             for blog_obj, matches in matched_blogs:
#                                 blog_context += f"📝 {blog_obj.title}"
                                
#                                 # Try to construct URL from various sources
#                                 blog_url = None
#                                 if hasattr(blog_obj, 'localurlpath') and blog_obj.localurlpath:
#                                     blog_url = f"{current_domain}{blog_obj.localurlpath}"
#                                 elif hasattr(blog_obj, 'url') and blog_obj.url:
#                                     blog_url = blog_obj.url
#                                     if 'http://127.0.0.1:8000' in blog_url:
#                                         blog_url = blog_url.replace('http://127.0.0.1:8000', current_domain)
#                                     elif 'localhost:8000' in blog_url:
#                                         blog_url = blog_url.replace('http://localhost:8000', current_domain)
#                                 elif hasattr(blog_obj, 'blogplace') and blog_obj.blogplace:
#                                     # Construct URL from place and blog title
#                                     place_slug = slugify(blog_obj.blogplace.slug or blog_obj.blogplace.placename)
#                                     title_slug = slugify(blog_obj.title)
#                                     blog_url = f"{current_domain}/pages/blog/{place_slug}/{title_slug}/"
                                
#                                 if blog_url:
#                                     if not created_or_matched_blog_url:
#                                         created_or_matched_blog_url = blog_url
#                                     blog_context += f" - URL: {blog_url}\n"
#                                 else:
#                                     blog_context += "\n"
#                         else:
#                             # No relevant existing blog found — generate a short guide blog and save it
#                             try:
#                                 # _step('No relevant blogs found, generating a new blog/article...')
#                                 # _step('Attempting to ASK AI for BLOG')
#                                 # _step('from this put it as a thread in task.py process_creating_blog(request,place,title) and make it so that it can be called from here and also from the admin panel when creating a new place')
#                                 # user_request_text = message_content
#                                 # prompt_blog = f"""
#                                 #     User message: "{user_request_text}"
#                                 #     - Produce a JSON object with keys: title, body_html, summary, category
#                                 #     (Title): short (<=60 chars). 
#                                 #     (Summary): one sentence if there is a link provided/included, use highlighted <a href="URL">name of the linked item</a> and do not include the URL in the text.  (<=140 chars) .
#                                 #     (body_html): valid HTML fragment only (no <html> wrapper). 
#                                 #     Include content appropriate to the user's request and double check if user is asking for a specific topic/subject and gave a url if so create a simple promotion 
#                                 #         !important  insert icons, links, and content relevant to the user's request and {place.placename}
                                    
#                                 #     Category: based on user message determine its category from the following 'Guide','Story','Tip and Trick','Explore','Product'

#                                 #     HTML content using body_html structure:
                                    
#                                 #     - A numbered step-by-step guide tailored to the user's request
#                                 #         <article class="blog-post">                                        
#                                 #             <div class="intro-section">
#                                 #                 <h2>[emoji then (Title) ]</h2>
#                                 #                 <p>[(Summary)] [image if provided]</p>
#                                 #             </div>
#                                 #             <p>[(body_html)]</p> 
#                                 #             <div class="content-section">
#                                 #                 <div>
#                                 #                 - insert a reason for why and what in {place.placename}
#                                 #                 </div>
#                                 #             </div>
#                                 #             <div class="content-section">
#                                 #                 <h2>💰 Budget Breakdown</h2>
#                                 #                 - If relevant, a clear cost breakdown list using PHP currency symbol ₱ with approximate costs (transport, fare, food, 1-night budget)
#                                 #                 <div class="tip-box">
#                                 #                 <p><strong>💡 [Category]:</strong></p>
#                                 #                 <ul><li>...</li></ul>
                                                
#                                 #                 </div>
#                                 #             </div>
#                                 #         </article>                                        
                                                                                
#                                 #     Keep the whole body concise . Do not produce extraneous text.
#                                 #     Place name: {place.placename}
#                                 #     Return only the JSON object.
#                                 #     """

#                                 # ai_resp = client.chat.completions.create(
#                                 #     model=settings.GROK_MODEL_NAME_EXPENSIVE,
#                                 #     messages=[{"role": "user", "content": prompt_blog}],
#                                 # )
#                                 # _step("Blog flow: received OpenAI response for blog")
#                                 # usage = ai_resp.usage

#                                 # print("Prompt tokens:", usage.prompt_tokens)
#                                 # print("Completion tokens:", usage.completion_tokens)
#                                 # print("Total tokens:", usage.total_tokens)  
#                                 # print('-----------------')                              
#                                 # print('-----------------')                              
#                                 # print('-----------------')                              

#                                 # ai_text = ai_resp.choices[0].message.content.strip()

#                                 # # Robust JSON parsing with fallback attempts
#                                 # blog_json = None
#                                 # try:
#                                 #     blog_json = json.loads(ai_text)
#                                 # except Exception:
#                                 #     import re
#                                 #     m = re.search(r"(\{.*\})", ai_text, re.DOTALL)
#                                 #     if m:
#                                 #         try:
#                                 #             blog_json = json.loads(m.group(1))
#                                 #         except Exception:
#                                 #             blog_json = None

#                                 # if not blog_json:
#                                 #     _step("Blog flow: JSON parse failed; retrying with stricter prompt")
#                                 #     retry_prompt = prompt_blog + "\n\nIMPORTANT: Return ONLY a single JSON object and nothing else. Use the exact keys: title, body_html, summary."
#                                 #     ai_resp2 = client.chat.completions.create(
#                                 #         model=settings.GROK_MODEL_NAME,
#                                 #         messages=[{"role": "user", "content": retry_prompt}],
#                                 #     )
#                                 #     ai_text2 = ai_resp2.choices[0].message.content.strip()
#                                 #     try:
#                                 #         blog_json = json.loads(ai_text2)
#                                 #     except Exception:
#                                 #         import re
#                                 #         m2 = re.search(r"(\{.*\})", ai_text2, re.DOTALL)
#                                 #         if m2:
#                                 #             try:
#                                 #                 blog_json = json.loads(m2.group(1))
#                                 #             except Exception:
#                                 #                 blog_json = None

#                                 # if not blog_json:
#                                 #     _step("Blog flow: failed to parse blog JSON after retry")
#                                 #     raise ValueError('Failed to parse blog JSON from AI response')

#                                 # body_html = blog_json.get('body_html', '')
#                                 # summary = blog_json.get('summary', '')
#                                 # blogcategory = blog_json.get('category', '')
#                                 # title = blog_json.get('title', '').strip()
                                
#                                 # Ensure title is never None or empty
#                                 # if not title:
#                                 #     if blogcategory:
#                                 #         title = f"{blogcategory} for {place.placename}"
#                                 #     else:
#                                 #         title = f"Guide to {place.placename}"
#                                 #     _step(f"Blog flow: title was empty, using fallback: {title!r}")
#                                 # else:
#                                 #     _step(f"Blog flow: title from AI response: {title!r}")

#                                 blog_thread_result = {"url": "", "error": None}

#                                 def run_blog_creation():
#                                     try:
#                                         blog_thread_result["url"] = process_creating_blog(
#                                             request,
#                                             place,
#                                             None,
#                                             message_lower,
#                                         ) or ""
#                                     except Exception as exc:
#                                         blog_thread_result["error"] = exc

#                                 blog_thread = threading.Thread(target=run_blog_creation)
#                                 blog_thread.start()
#                                 blog_thread.join()

#                                 if blog_thread_result["error"] is not None:
#                                     raise blog_thread_result["error"]

#                                 created_or_matched_blog_url = blog_thread_result["url"]
#                                 # # FROM
#                                 # blog_obj = generate_blog_object(
#                                 #     request,
#                                 #     place_name=place.placename,
#                                 #     title=title,
#                                 #     text_content=body_html,
#                                 #     summary=summary, 
#                                 #     category=blogcategory,
#                                 # )
#                                 # _step(f"Blog flow: saved new blog title={getattr(blog_obj,'title',None)!r}")
                                


#                             except Exception as e:
#                                 print('Blog generation error:', e)
#                                 _step(f"Blog flow: error {type(e).__name__}")
#                         print('Blog URL to be returned:', created_or_matched_blog_url)
#                         return {
#                             "is_about_blogs": True,
#                             "blog_url": created_or_matched_blog_url,
#                         }
#                     else:
#                         _step("Not about blog")
#                         return {
#                             "is_about_blogs": False,
#                             "blog_url": "",
#                         }


#                 blog_check = Checkblog(message_lower, place)
#                 is_about_blogs = blog_check.get("is_about_blogs", False)

#                 print('\n\n is_about_blogs:', is_about_blogs)
#                 if is_about_blogs:
#                     print('Message classified as about blogs/articles; returning blog context')
#                     return JsonResponse({
#                         "response": [],
#                         "blog_url": blog_check.get("blog_url", ""),
#                         "message": "Blog Created or Matched",
#                     })
#                     # return HttpResponse("Blog Created or Matched")
#                     # return JsonResponse({"response": 'Blog Created  or Matched'})
#                 _step("Early check: running local message classifier")
#                 # Save user message when it is a real question or a non-question statement.

                
#                 early_result = _classify_discussion_message(message_content)
                
#                 _step(f"Early local check result: {early_result}")
                
#                 if early_result == "OFFENSIVE":
#                     _step("Local classifier marked message as OFFENSIVE")
#                     return JsonResponse({"response": " "})

#                 elif early_result == "QUESTION":
#                     _step("Early check: QUESTION - proceeding with full processing")

#                     # Continue to full processing (no return here)

#                 elif early_result == "NOT_QUESTION":
#                     _step("Early check: NOT_QUESTION - saving message and returning")
#                     # Save user message
#                     username_to_use = data.get('username') or (request.user.username if request.user.is_authenticated else 'Anonymous')
#                     try:
#                         if request.user.is_authenticated:
#                             ensure_user_profile(request.user)
#                         discuss = PlaceDiscussion.objects.create(discuss=message_content,
#                             place=place, discusserName=username_to_use)
#                     except:
#                         discuss = PlaceDiscussion.objects.create( 
#                             discuss=message_content, place=place, discusserName=username_to_use)
#                     place.discussion.add(discuss)
#                     # Return latest discussions
#                     objectRecords = place.discussions.order_by('-id').values()[:5]
#                     _step("Local classifier marked message as NOT_QUESTION; returning latest discussions")
                    
#                     return JsonResponse({"response": list(objectRecords)})
                
#                 # Saving User Sent Message
#                 try:
#                     username_to_use = data.get('username') or (request.user.username if request.user.is_authenticated else 'Anonymous')
#                     _step(f"Resolved username={username_to_use!r} authenticated={request.user.is_authenticated}")
#                     if request.user.is_authenticated:
#                         ensure_user_profile(request.user)
#                         _step("UserPoster synchronized")
#                     discuss = PlaceDiscussion.objects.create(discuss=message_content,
#                         place=place, discusserName=username_to_use)
#                     _step("Saved user discussion (with userPoster)")
#                 except:
#                     discuss = PlaceDiscussion.objects.create( 
#                         discuss=message_content, place=place, discusserName=username_to_use)
#                     _step("Saved user discussion (anonymous/fallback)")
                
#                 place.discussion.add(discuss)
#                 _step("Attached discussion to place.discussion")

#                 try:
#                     _step("RAG: attempting model-backed answer")
#                     rag_message = _discussion_model_backed_response(message_content, place, request, _step)
#                 except Exception as rag_error:
#                     rag_message = ""
#                     _step(f"RAG: failed with {type(rag_error).__name__}; falling back to legacy flow")

#                 if rag_message:
#                     ai_discuss = PlaceDiscussion.objects.create(
#                         discuss=rag_message,
#                         discusserName="Assistant",
#                         place=place
#                     )
#                     place.discussion.add(ai_discuss)
#                     _step("RAG: saved assistant response and returning")
#                     objectRecords = place.discussions.order_by('-id').values()[:2]
#                     return JsonResponse({"response": list(objectRecords)})


#             except Exception as e:
#                 _step(f"Early local check failed: {type(e).__name__} - proceeding with full flow")
#                 # If early check fails, continue with full processing
            

#             # NOW CHECKING THE MESSAGE
            
#             event_keywords = ['event', 'events', 'happening', 'schedule', 'festival', 'activity', 'activities', 'what to do', 'whats on']
#             resort_keywords = ['resort', 'resorts', 'hotel', 'hotels', 'stay', 'accommodation', 'accommodations', 'lodge', 'where to stay', 'promotion', 'promotions', 'deal', 'deals', 'booking', 'room', 'rooms', 'tour', 'tours', 'package', 'packages', 'activity', 'activities']
#             # Tour guide keywords (kept separate from generic "guide" blog intent)
#             tour_guide_keywords = [
#                 'tour guide', 'tourguide', 'tour guide in', 'tour guide for',
#                 'local guide', 'hire a guide', 'need a guide', 'looking for a guide',
#                 'guided tour', 'private guide', 'tourist guide'
#             ]
#             # Narrow blog keywords to avoid matching on generic question words
            

#             # Food-specific keywords (checked before generic blog keywords)
#             food_keywords = ['food', 'restaurant', 'eat', 'dining', 'menu', 'dish', 'meal', 'cuisine', 'seafood', 'where to eat','drink','milk','tea','coffee','breakfast','lunch','dinner','snack','snacks','cafeteria','cafe','bakery','barbecue','bbq','grill']

#             # Activity-specific keywords

#             activity_keywords = [
#                 'what to do', 'what can i do', 'activities', 'activity', 'things to do',
#                 'adventure', 'tour', 'tours', 'ride', 'sports', 'surf', 'snorkel',
#                 'rental', 'rentals', 'rent', 'looking','play'
#             ] 

#             is_about_events = any(keyword in message_lower for keyword in event_keywords)
#             is_about_resorts = any(keyword in message_lower for keyword in resort_keywords)
#             # Require tour-guide intent; avoid triggering on generic "guide" alone
#             is_about_tour_guides = (
#                 any(keyword in message_lower for keyword in tour_guide_keywords)
#                 or (
#                     'guide' in message_lower
#                     and any(x in message_lower for x in ['tour', 'tourist', 'island', 'siargao'])
#                 )
#             )



#             _step(
#                 "Topic flags computed "
#                 # f"events={is_about_events} resorts={is_about_resorts} blogs={is_about_blogs} "
#                 # f"food={is_about_food} activities={is_about_activities} tour_guides={is_about_tour_guides} wants_new_blog={wants_new_blog}"
#             )

#             # Prefer specific topic when specific keywords are present to avoid generic-word misclassification
#             is_about_food = any(keyword in message_lower for keyword in food_keywords)
#             is_about_activities = any(keyword in message_lower for keyword in activity_keywords)            
#             if is_about_food:
#                 is_about_blogs = False
#             if is_about_activities:
#                 is_about_blogs = False
#             if is_about_resorts:
#                 is_about_blogs = False
#             if is_about_tour_guides:
#                 is_about_blogs = False
#                 # Avoid pulling resort/package context just because the word "tour" appears.
#                 if not any(x in message_lower for x in ['resort', 'hotel', 'accommodation', 'room', 'rooms', 'stay']):
#                     is_about_resorts = False

#             # Debug final topic flags
#             # print(f"Topic flags -> events:{is_about_events}, resorts:{is_about_resorts}, tour_guides:{is_about_tour_guides}, blogs:{is_about_blogs}, wants_new_blog:{wants_new_blog}, food:{is_about_food}, activities:{is_about_activities}")

#             # Build context efficiently
#             context_info = ""
#             MAX_CONTEXT_CHARS = 4800
            
#             # Only fetch blogs if the question might be answered by them
#             blog_context = ""


#             if is_about_events:
#                 _step("Events flow: building upcoming events context")
#                 from datetime import datetime
#                 from django.utils import timezone
#                 from django.db.models import Q
#                 current_date = timezone.now().date()
#                 current_month = datetime.now().month
#                 current_year = datetime.now().year
#                 current_day = current_date.day
                
#                 # Filter events: future years OR (current year AND future months) OR (current year AND current month AND future/today dates)
#                 events = place.eventList.filter(
#                     Q(yearN__gt=current_year) |
#                     Q(yearN=current_year, monthN__gt=current_month) |
#                     Q(yearN=current_year, monthN=current_month, dateN__gte=current_day)
#                 ).filter(
#                     monthN__lte=current_month + 2
#                 ).only('scheduleTitle', 'exactDate', 'schedulePlace').order_by('yearN', 'monthN', 'dateN')[:10]
                
#                 if events:
#                     context_info += "\n\nUpcoming Events:\n"
#                     for event in events:
#                         context_info += f"- {event.scheduleTitle} on {event.exactDate}"
#                         if event.schedulePlace:
#                             context_info += f" at {event.schedulePlace}"
#                         context_info += "\n"
#                 _step(f"Events flow: events_found={bool(events)}")
            
#             elif is_about_resorts:
#                 _step("Resorts flow: building resort/package context")
#                 # Check for specific amenity/feature keywords in the user's message
#                 amenity_keywords = {
#                     'wifi': ['wifi', 'wi-fi', 'internet', 'wireless'],
#                     'pool': ['pool', 'swimming', 'swimming pool'],
#                     'bidet': ['bidet', 'bidet shower'],
#                     'parking': ['parking', 'parking space', 'car park', 'garage'],
#                     'restaurant': ['restaurant', 'dining', 'dine-in', 'on-site restaurant'],
#                     'bar': ['bar', 'lounge', 'bar lounge', 'drinks'],
#                     'spa': ['spa', 'massage', 'spa services', 'wellness'],
#                     'gym': ['gym', 'fitness', 'fitness center', 'workout'],
#                     'beach_access': ['beach', 'beachfront', 'beach access', 'direct beach'],
#                     'air_conditioning': ['aircon', 'air-con', 'air con', 'airconditioned', 'ac', 'a/c', 'air conditioning'],
#                     'hot_water': ['hot water', 'hot shower', 'heater'],
#                     'breakfast': ['breakfast', 'morning meal', 'complimentary breakfast'],
#                     'laundry': ['laundry', 'laundry service', 'washing'],
#                     'pet_friendly': ['pet', 'pets', 'pet-friendly', 'pet friendly', 'dog', 'cat', 'animals'],
#                     'family_friendly': ['family', 'family-friendly', 'family friendly', 'kids', 'children'],
#                     'generator': ['generator', 'backup power', 'power backup', 'emergency power']
#                 }
                
#                 room_feature_keywords = {
#                     'fan': ['fan', 'electric fan'],
#                     'view': ['view', 'ocean view', 'sea view'],
#                     'private': ['private', 'ensuite', 'en-suite'],
#                     'bathroom': ['bathroom', 'shower', 'toilet', 'cr'],
#                     'double': ['double', 'queen', 'king'],
#                     'single': ['single', 'twin'],
#                     'cheap': ['cheap', 'affordable', 'budget', 'inexpensive'],
#                     'expensive': ['luxury', 'premium', 'deluxe']
#                 }
                
#                 # Identify which amenities the user is asking about
#                 requested_amenities = []
#                 for amenity, keywords in amenity_keywords.items():
#                     if any(keyword in message_lower for keyword in keywords):
#                         requested_amenities.append(amenity)
                
#                 # Identify which features the user is asking about
#                 mentioned_features = []
#                 for feature, keywords in room_feature_keywords.items():
#                     if any(keyword in message_lower for keyword in keywords):
#                         mentioned_features.append(feature)
#                 _step(f"Resorts flow: requested_amenities={requested_amenities}, mentioned_features={mentioned_features}")
                
#                 # Optimized query with prefetch_related and amenity fields
#                 resorts = place.resortList.prefetch_related(
#                     'resortAccomodations__subPackages',
#                     'resortActivities__subPackages',
#                     'resortTour__subPackages'
#                 ).only(
#                     'RealName', 'name', 'contactNumber', 'contactEmail', 'websiteURL',
#                     'has_wifi', 'has_pool', 'has_bidet', 'has_parking', 'has_restaurant',
#                     'has_bar', 'has_spa', 'has_gym', 'has_beach_access', 'has_air_conditioning',
#                     'has_hot_water', 'has_breakfast', 'has_laundry', 'pet_friendly', 
#                     'family_friendly', 'has_generator'
#                 )
                
#                 # Filter and score resorts based on requested amenities
#                 resort_matches = []
#                 for resort in resorts:
#                     match_score = 0
#                     matched_amenities = []
                    
#                     if requested_amenities:
#                         # Check which requested amenities this resort has
#                         for amenity in requested_amenities:
#                             # Map amenity key to model field
#                             field_name = f'has_{amenity}' if not amenity.endswith('_friendly') else amenity
#                             if hasattr(resort, field_name) and getattr(resort, field_name):
#                                 match_score += 1
#                                 matched_amenities.append(amenity)
                        
#                         # Only include resorts that match at least one requested amenity
#                         if match_score > 0:
#                             resort_matches.append((resort, match_score, matched_amenities))
#                     else:
#                         # No specific amenities requested, include all resorts
#                         resort_matches.append((resort, 0, []))
                
#                 # Sort by match score (highest first)
#                 resort_matches.sort(key=lambda x: x[1], reverse=True)
                
#                 # Limit to top 8 resorts
#                 resort_matches = resort_matches[:8]
                
#                 if resort_matches:
#                     context_info += "\n\nAvailable Resorts"
#                     if requested_amenities:
#                         amenity_labels = {
#                             'wifi': 'WiFi', 'pool': 'Pool', 'bidet': 'Bidet', 'parking': 'Parking',
#                             'restaurant': 'Restaurant', 'bar': 'Bar', 'spa': 'Spa', 'gym': 'Gym',
#                             'beach_access': 'Beach Access', 'air_conditioning': 'Air Conditioning',
#                             'hot_water': 'Hot Water', 'breakfast': 'Breakfast', 'laundry': 'Laundry',
#                             'pet_friendly': 'Pet Friendly', 'family_friendly': 'Family Friendly',
#                             'generator': 'Generator'
#                         }
#                         requested_labels = [amenity_labels.get(a, a.replace('_', ' ').title()) for a in requested_amenities]
#                         context_info += f" with {', '.join(requested_labels)}:\n"
#                     else:
#                         context_info += ":\n"
                    
#                     for resort, score, matched_amenities in resort_matches:
#                         resort_name = resort.RealName if resort.RealName else resort.name
#                         context_info += f"\n{resort_name}"
                        
#                         # Show which requested amenities this resort has
#                         if matched_amenities:
#                             amenity_icons = {
#                                 'wifi': '📶', 'pool': '🏊', 'bidet': '🚿', 'parking': '🅿️',
#                                 'restaurant': '🍽️', 'bar': '🍹', 'spa': '💆', 'gym': '🏋️',
#                                 'beach_access': '🏖️', 'air_conditioning': '❄️', 'hot_water': '♨️',
#                                 'breakfast': '🍳', 'laundry': '🧺', 'pet_friendly': '🐾',
#                                 'family_friendly': '👨‍👩‍👧‍👦', 'generator': '⚡'
#                             }
#                             amenity_list = [f"{amenity_icons.get(a, '✓')} {a.replace('_', ' ').title()}" 
#                                           for a in matched_amenities]
#                             context_info += f" (✓ {', '.join(amenity_list)})"
                        
#                         context_info += ":\n"
                        
#                         # Show all amenities this resort has
#                         all_amenities = []
#                         amenity_map = {
#                             'has_wifi': '📶 WiFi', 'has_pool': '🏊 Pool', 'has_bidet': '🚿 Bidet',
#                             'has_parking': '🅿️ Parking', 'has_restaurant': '🍽️ Restaurant',
#                             'has_bar': '🍹 Bar', 'has_spa': '💆 Spa', 'has_gym': '🏋️ Gym',
#                             'has_beach_access': '🏖️ Beach Access', 'has_air_conditioning': '❄️ AC',
#                             'has_hot_water': '♨️ Hot Water', 'has_breakfast': '🍳 Breakfast',
#                             'has_laundry': '🧺 Laundry', 'pet_friendly': '🐾 Pet Friendly',
#                             'family_friendly': '👨‍👩‍👧‍👦 Family Friendly', 'has_generator': '⚡ Generator'
#                         }
                        
#                         for field, label in amenity_map.items():
#                             if hasattr(resort, field) and getattr(resort, field):
#                                 all_amenities.append(label)
                        
#                         if all_amenities:
#                             context_info += f"  Amenities: {', '.join(all_amenities)}\n"
                        
#                         if resort.contactNumber or resort.contactEmail:
#                             context_info += "  Contact: "
#                             if resort.contactNumber:
#                                 context_info += f" {resort.contactNumber}"
#                             if resort.contactEmail:
#                                 if resort.contactNumber:
#                                     context_info += " | "
#                                 context_info += f" {resort.contactEmail}"
#                             context_info += "\n"
                        
#                         if resort.websiteURL:
#                             context_info += f"   {resort.websiteURL}\n"
                        
#                         # Process accommodations with detailed room info
#                         accommodations = resort.resortAccomodations.all()
#                         if accommodations:
#                             context_info += f"  Room Options:\n"
#                             for accom in accommodations[:3]:  # Show top 3 accommodations
#                                 for sub in accom.subPackages.all()[:4]:  # Show up to 4 rooms per accommodation
#                                     # Check if this room matches user's query features
#                                     room_desc_lower = (sub.description or '').lower()
#                                     room_title_lower = (sub.title or '').lower()
#                                     room_text = f"{room_title_lower} {room_desc_lower}"
                                    
#                                     # If user asked about specific features, prioritize matching rooms
#                                     is_relevant = True
#                                     if mentioned_features:
#                                         is_relevant = any(
#                                             any(keyword in room_text for keyword in room_feature_keywords.get(feature, []))
#                                             for feature in mentioned_features
#                                         )
                                    
#                                     if is_relevant:
#                                         context_info += f"    • {sub.title}"
#                                         if sub.price > 0:
#                                             context_info += f" - ₱{sub.price}"
#                                         if sub.description:
#                                             # Extract key amenities from description
#                                             desc = sub.description[:150]
#                                             context_info += f"\n      Features: {desc}"
#                                             if len(sub.description) > 150:
#                                                 context_info += "..."
#                                         context_info += "\n"
#                         # Process activities and tours (less detail if room query)
#                         if not mentioned_features or 'activity' in message_lower or 'tour' in message_lower:
#                             for pkg_type, pkg_list, label in [
#                                 ('resortActivities', resort.resortActivities.all()[:2], 'Activities'),
#                                 ('resortTour', resort.resortTour.all()[:2], 'Tours')
#                             ]:
#                                 if pkg_list:
#                                     context_info += f"  {label}:\n"
#                                     for pkg in pkg_list:
#                                         for sub in pkg.subPackages.all()[:2]:
#                                             context_info += f"    • {sub.title}"
#                                             if sub.price > 0:
#                                                 context_info += f" - ₱{sub.price}"
#                                             if sub.description:
#                                                 context_info += f": {sub.description[:60]}..."
#                                             context_info += "\n"

#                 _step(f"Resorts flow: found {len(resort_matches)} resorts")

#             # If user asked for a tour guide, suggest from TourGuide model (prefer guides for this place)
#             elif is_about_tour_guides:
#                 _step("TourGuide flow: building tour guide suggestions")
#                 try:
#                     guides_qs = (
#                         TourGuide.objects.filter(is_active=True)
#                         .select_related('user', 'primary_place')
#                     )

#                     # Prefer guides whose primary_place matches the current place.
#                     place_guides = guides_qs.filter(primary_place=place)
#                     if place_guides.exists():
#                         guides_to_show = place_guides[:6]
#                     else:
#                         # Fallback: show any active guides (still helpful when primary_place isn't set).
#                         guides_to_show = guides_qs[:6]

#                     if guides_to_show:
#                         context_info += "\n\nAvailable Tour Guides:\n"
#                         for g in guides_to_show:
#                             username = getattr(getattr(g, 'user', None), 'username', '') or 'Tour Guide'
#                             email = getattr(getattr(g, 'user', None), 'email', '') or ''
#                             context_info += f"\n{username}:\n"
#                             if getattr(g, 'mobile_number', '') or email:
#                                 context_info += "  Contact: "
#                                 if getattr(g, 'mobile_number', ''):
#                                     context_info += f" {g.mobile_number}"
#                                 if email:
#                                     if getattr(g, 'mobile_number', ''):
#                                         context_info += " | "
#                                     context_info += f" {email}"
#                                 context_info += "\n"
#                             if getattr(g, 'experience_years', 0):
#                                 context_info += f"  Experience: {g.experience_years} year(s)\n"
#                             if getattr(g, 'bio', ''):
#                                 bio = (g.bio or '').strip()
#                                 if bio:
#                                     context_info += f"  Bio: {bio[:140]}"
#                                     if len(bio) > 140:
#                                         context_info += "..."
#                                     context_info += "\n"
#                     _step(f"TourGuide flow: guides_found={bool(guides_to_show)}")
#                 except Exception as e:
#                     print('TourGuide suggestions error:', e)
#                     _step(f"TourGuide flow: error {type(e).__name__}")
            
#             # Supplemental: if the user asked about food, prefer local resort food packages when available
#             elif is_about_food:
#                 _step("Food flow: building food/dining context")
#                 try:
#                     from django.db.models import Prefetch, Q
#                     from django.utils import timezone
#                     from resorts.models import resortPackages, Packages

#                     MAX_RESORTS = 6
#                     MAX_PACKAGES_PER_RESORT = 3
#                     MAX_SUBPACKAGES_PER_PACKAGE = 4
#                     import re
#                     # Tokenize the user's message to build a backend query.
#                     tokens = re.findall(r"[a-z0-9]{3,}", message_lower)
#                     stop_tokens = {
#                         'what', 'can', 'you', 'please', 'plz', 'the', 'and', 'or', 'for', 'to', 'in', 'on', 'at',
#                         'with', 'from', 'near', 'around', 'need', 'want', 'looking', 'find', 'where', 'how',
#                         'get', 'buy', 'have', 'offer', 'available',
#                         # broad terms that don't help matching specific items
#                         'food', 'foods', 'eat', 'eats', 'eating', 'dining', 'menu', 'restaurant', 'restaurants',
#                         'dish', 'dishes', 'meal', 'meals', 'drink', 'drinks',
#                         # location/app noise
#                         'siargao', 'resort', 'resorts'
#                     }
#                     query_tokens = [t for t in tokens if t not in stop_tokens]

#                     # De-dupe while preserving order
#                     seen = set()
#                     query_tokens = [t for t in query_tokens if not (t in seen or seen.add(t))]

#                     def _format_resort_header(resort_obj) -> tuple[str, str, str]:
#                         resort_name_local = resort_obj.RealName if resort_obj.RealName else resort_obj.name
#                         contact_items = []
#                         if getattr(resort_obj, 'contactNumber', ''):
#                             contact_items.append(f" {resort_obj.contactNumber}")
#                         if getattr(resort_obj, 'contactEmail', ''):
#                             contact_items.append(f" {resort_obj.contactEmail}")
#                         contact_line_local = " | ".join(contact_items)
#                         website_line_local = f" {resort_obj.websiteURL}" if getattr(resort_obj, 'websiteURL', '') else ""
#                         return resort_name_local, contact_line_local, website_line_local

#                     # Backend filtering first: only fetch packages/subpackages that match user keywords.
#                     now = timezone.now()
#                     if query_tokens:
#                         rel_q = Q()
#                         sub_q = Q()
#                         for t in query_tokens:
#                             rel_q |= (
#                                 Q(PackageTitle__icontains=t)
#                                 | Q(subPackages__title__icontains=t)
#                                 | Q(subPackages__description__icontains=t)
#                                 | Q(subPackages__information__icontains=t)
#                             )
#                             sub_q |= (
#                                 Q(title__icontains=t)
#                                 | Q(description__icontains=t)
#                                 | Q(information__icontains=t)
#                             )

#                         matching_subs_qs = (
#                             Packages.objects.filter(sub_q, is_available=True)
#                             .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
#                             .only('title', 'description', 'information', 'price', 'website')
#                             .distinct()
#                         )
#                         matching_pkgs_qs = (
#                             resortPackages.objects.filter(rel_q)
#                             .only('PackageTitle')
#                             .distinct()
#                             .prefetch_related(
#                                 Prefetch('subPackages', queryset=matching_subs_qs, to_attr='matching_subpackages')
#                             )
#                         )

#                         food_resorts_qs = (
#                             place.resortList.filter(resortFood__in=matching_pkgs_qs)
#                             .distinct()
#                             .prefetch_related(
#                                 Prefetch('resortFood', queryset=matching_pkgs_qs, to_attr='food_packages')
#                             )
#                         )

#                         if food_resorts_qs.exists():
#                             context_info += "\n\nRecommended Food (matched to your request):\n"
#                             for resort in food_resorts_qs[:MAX_RESORTS]:
#                                 resort_name, contact_line, website_line = _format_resort_header(resort)
#                                 context_info += f"\n{resort_name}:\n"
#                                 if contact_line:
#                                     context_info += f"  Contact: {contact_line}\n"
#                                 if website_line:
#                                     context_info += f"  {website_line}\n"

#                                 food_packages = getattr(resort, 'food_packages', None) or []
#                                 shown_pkg = 0
#                                 for pkg in food_packages:
#                                     if shown_pkg >= MAX_PACKAGES_PER_RESORT:
#                                         break

#                                     pkg_title = getattr(pkg, 'PackageTitle', '') or ''
#                                     matching_subs = getattr(pkg, 'matching_subpackages', None) or []
#                                     if not pkg_title and not matching_subs:
#                                         continue

#                                     if pkg_title:
#                                         context_info += f"  {pkg_title}:\n"
#                                     shown_sub = 0
#                                     for sub in matching_subs:
#                                         if shown_sub >= MAX_SUBPACKAGES_PER_PACKAGE:
#                                             break
#                                         context_info += f"    • {sub.title}"
#                                         if getattr(sub, 'price', 0) and sub.price > 0:
#                                             context_info += f" - ₱{sub.price}"
#                                         if getattr(sub, 'website', ''):
#                                             context_info += f" (link: {sub.website})"
#                                         if getattr(sub, 'description', ''):
#                                             desc = (sub.description or '')[:60]
#                                             if desc:
#                                                 context_info += f"\n      {desc}"
#                                                 if len(sub.description or '') > 60:
#                                                     context_info += "..."
#                                         context_info += "\n"
#                                         shown_sub += 1
#                                     shown_pkg += 1
#                         else:
#                             context_info += "\n\nNo matching food items found. Try a more specific keyword.\n"
#                     else:
#                         # No meaningful tokens: keep a compact generic list.
#                         food_resorts_qs = (
#                             place.resortList.filter(resortFood__isnull=False)
#                             .distinct()
#                             .prefetch_related(Prefetch('resortFood', to_attr='food_packages'))
#                         )
#                         if food_resorts_qs.exists():
#                             context_info += "\n\nAvailable Food & Dining:\n"
#                             for resort in food_resorts_qs[:MAX_RESORTS]:
#                                 resort_name, contact_line, website_line = _format_resort_header(resort)
#                                 context_info += f"\n{resort_name}:\n"
#                                 if contact_line:
#                                     context_info += f"  Contact: {contact_line}\n"
#                                 if website_line:
#                                     context_info += f"  {website_line}\n"
#                                 food_packages = getattr(resort, 'food_packages', None) or resort.resortFood.all()
#                                 shown_pkg = 0
#                                 for pkg in food_packages:
#                                     if shown_pkg >= MAX_PACKAGES_PER_RESORT:
#                                         break
#                                     pkg_title = getattr(pkg, 'PackageTitle', '') or ''
#                                     if pkg_title:
#                                         context_info += f"  {pkg_title}\n"
#                                     shown_pkg += 1
#                 except Exception as e:
#                     print('Food suggestions error:', e)
#                     _step(f"Food flow: error {type(e).__name__}")

#             # If user asked about activities, prefer resort activity packages and tours
#             elif is_about_activities:
#                 _step("Activities flow: building activities/tours context")
#                 try:
#                     from django.db.models import Prefetch, Q
#                     from django.utils import timezone
#                     from resorts.models import resortPackages, Packages
#                     import re

#                     MAX_RESORTS = 6
#                     MAX_PACKAGES_PER_RESORT = 3
#                     MAX_SUBPACKAGES_PER_PACKAGE = 4

#                     # Tokenize the user's message to build a backend query.
#                     tokens = re.findall(r"[a-z0-9]{3,}", message_lower)
#                     stop_tokens = {
#                         'what', 'can', 'you', 'please', 'plz', 'the', 'and', 'or', 'for', 'to', 'in', 'on', 'at',
#                         'with', 'from', 'near', 'around', 'need', 'want', 'looking', 'find', 'where', 'how',
#                         'get', 'book', 'price', 'cost', 'available', 'offer', 'offered',
#                         'activity', 'activities', 'things', 'thing', 'do', 'doing',
#                         # broad app/location noise
#                         'siargao', 'resort', 'resorts'
#                     }
#                     query_tokens = [t for t in tokens if t not in stop_tokens]

#                     # De-dupe while preserving order
#                     seen = set()
#                     query_tokens = [t for t in query_tokens if not (t in seen or seen.add(t))]

#                     def _format_resort_header(resort_obj) -> tuple[str, str, str]:
#                         resort_name_local = resort_obj.RealName if resort_obj.RealName else resort_obj.name
#                         contact_items = []
#                         if getattr(resort_obj, 'contactNumber', ''):
#                             contact_items.append(f" {resort_obj.contactNumber}")
#                         if getattr(resort_obj, 'contactEmail', ''):
#                             contact_items.append(f" {resort_obj.contactEmail}")
#                         contact_line_local = " | ".join(contact_items)
#                         website_line_local = f" {resort_obj.websiteURL}" if getattr(resort_obj, 'websiteURL', '') else ""
#                         return resort_name_local, contact_line_local, website_line_local

#                     now = timezone.now()

#                     if query_tokens:
#                         rel_q = Q()
#                         sub_q = Q()
#                         for t in query_tokens:
#                             rel_q |= (
#                                 Q(PackageTitle__icontains=t)
#                                 | Q(subPackages__title__icontains=t)
#                                 | Q(subPackages__description__icontains=t)
#                                 | Q(subPackages__information__icontains=t)
#                             )
#                             sub_q |= (
#                                 Q(title__icontains=t)
#                                 | Q(description__icontains=t)
#                                 | Q(information__icontains=t)
#                             )

#                         matching_subs_qs = (
#                             Packages.objects.filter(sub_q, is_available=True)
#                             .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
#                             .only('title', 'description', 'information', 'price', 'website')
#                             .distinct()
#                         )
#                         matching_pkgs_qs = (
#                             resortPackages.objects.filter(rel_q)
#                             .only('PackageTitle')
#                             .distinct()
#                             .prefetch_related(
#                                 Prefetch('subPackages', queryset=matching_subs_qs, to_attr='matching_subpackages')
#                             )
#                         )

#                         activity_resorts_qs = (
#                             place.resortList.filter(
#                                 Q(resortActivities__in=matching_pkgs_qs) | Q(resortTour__in=matching_pkgs_qs)
#                             )
#                             .distinct()
#                             .prefetch_related(
#                                 Prefetch('resortActivities', queryset=matching_pkgs_qs, to_attr='activity_packages'),
#                                 Prefetch('resortTour', queryset=matching_pkgs_qs, to_attr='tour_packages'),
#                             )
#                         )

#                         if activity_resorts_qs.exists():
#                             context_info += "\n\nRecommended Activities & Tours (matched to your request):\n"
#                             for resort in activity_resorts_qs[:MAX_RESORTS]:
#                                 resort_name, contact_line, website_line = _format_resort_header(resort)
#                                 context_info += f"\n{resort_name}:\n"
#                                 if contact_line:
#                                     context_info += f"  Contact: {contact_line}\n"
#                                 if website_line:
#                                     context_info += f"  {website_line}\n"

#                                 activity_pkgs = getattr(resort, 'activity_packages', None) or []
#                                 tour_pkgs = getattr(resort, 'tour_packages', None) or []

#                                 # Prefer showing direct subpackage matches; keep it small.
#                                 def _render_pkg_list(label: str, pkgs: list):
#                                     nonlocal context_info
#                                     shown_pkg = 0
#                                     for pkg in pkgs:
#                                         if shown_pkg >= MAX_PACKAGES_PER_RESORT:
#                                             break
#                                         pkg_title = getattr(pkg, 'PackageTitle', '') or ''
#                                         matching_subs = getattr(pkg, 'matching_subpackages', None) or []
#                                         if not pkg_title and not matching_subs:
#                                             continue

#                                         context_info += f"  {label}: {pkg_title}\n" if pkg_title else f"  {label}:\n"
#                                         shown_sub = 0
#                                         for sub in matching_subs:
#                                             if shown_sub >= MAX_SUBPACKAGES_PER_PACKAGE:
#                                                 break
#                                             context_info += f"    • {sub.title}"
#                                             if getattr(sub, 'price', 0) and sub.price > 0:
#                                                 context_info += f" - ₱{sub.price}"
#                                             if getattr(sub, 'website', ''):
#                                                 context_info += f" (link: {sub.website})"
#                                             if getattr(sub, 'description', ''):
#                                                 desc = (sub.description or '')[:60]
#                                                 if desc:
#                                                     context_info += f"\n      {desc}"
#                                                     if len(sub.description or '') > 60:
#                                                         context_info += "..."
#                                             context_info += "\n"
#                                             shown_sub += 1
#                                         shown_pkg += 1

#                                 if activity_pkgs:
#                                     _render_pkg_list('Activity', activity_pkgs)
#                                 if tour_pkgs:
#                                     _render_pkg_list('Tour', tour_pkgs)
#                         else:
#                             context_info += "\n\nNo matching activities found. Try a more specific keyword (e.g., surf, snorkel, island hopping).\n"
#                     else:
#                         # No meaningful tokens: keep a compact generic list.
#                         activity_resorts_qs = (
#                             place.resortList.filter(Q(resortActivities__isnull=False) | Q(resortTour__isnull=False))
#                             .distinct()
#                             .prefetch_related(
#                                 Prefetch('resortActivities', to_attr='activity_packages'),
#                                 Prefetch('resortTour', to_attr='tour_packages'),
#                             )
#                         )
#                         if activity_resorts_qs.exists():
#                             context_info += "\n\nAvailable Activities & Tours:\n"
#                             for resort in activity_resorts_qs[:MAX_RESORTS]:
#                                 resort_name, contact_line, website_line = _format_resort_header(resort)
#                                 context_info += f"\n{resort_name}:\n"
#                                 if contact_line:
#                                     context_info += f"  Contact: {contact_line}\n"
#                                 if website_line:
#                                     context_info += f"  {website_line}\n"
#                                 shown = 0
#                                 for pkg in (getattr(resort, 'activity_packages', None) or resort.resortActivities.all())[:4]:
#                                     if shown >= 4:
#                                         break
#                                     title = getattr(pkg, 'PackageTitle', '') or ''
#                                     if title:
#                                         context_info += f"  Activity: {title}\n"
#                                         shown += 1
#                                 shown = 0
#                                 for pkg in (getattr(resort, 'tour_packages', None) or resort.resortTour.all())[:4]:
#                                     if shown >= 3:
#                                         break
#                                     title = getattr(pkg, 'PackageTitle', '') or ''
#                                     if title:
#                                         context_info += f"  Tour: {title}\n"
#                                         shown += 1
#                 except Exception as e:
#                     print('Activities suggestions error:', e)
#                     _step(f"Activities flow: error {type(e).__name__}")

#             # Add blog context to main context
#             context_info += blog_context

#             # Hard cap: keep prompt small to avoid token bloat.
#             if len(context_info) > MAX_CONTEXT_CHARS:
#                 context_info = context_info[:MAX_CONTEXT_CHARS].rsplit('\n', 1)[0]
#                 context_info += "\n\n(Additional results omitted for brevity.)"
#             _step(f"Context built chars={len(context_info)}")
#             print('Context Info:', context_info)
            
#             # Single AI call with combined safety check, question detection, and response
#             context_text = f'\n\nUse this context to answer:\n{context_info}' if context_info else ''

#             prompt = f"""
#                 You are a travel assistant for {place.placename}.
#                 User message: "{data.get('message')}"
#                 SAFETY CHECK:
#                 If offensive → respond ONLY with: OFFENSIVE
#                 Response (max 80 words):
#                 - Use <strong> tags for emphasis (NOT markdown **bold**)
#                 - if resort is recommended always include contact details (phone/email/website put it in html input element readonly and onclick="this.select()")  if available and their link like <a href="URL" target="_blank" rel="noopener">TITLE</a>
#                 - If tour guides exist in context and user asked for a tour guide, include 1-2 tour guide suggestions with their contact details
#                 - When blogs exist in context, your response recommend the blog in <a> tag with exact URL'
#                 - ALWAYS copy URLs exactly from context
#                 {context_text}
#                 """
            
#             try:
#                 _step("Calling OpenAI for assistant response")
#                 ai_response = client.chat.completions.create(
#                     model=settings.GROK_MODEL_NAME,
#                     messages=[{"role": "user", "content": prompt}],
#                 )
#                 ai_message = ai_response.choices[0].message.content.strip()
#                 _step(f"OpenAI responded chars={len(ai_message)}")
                
#                 # Convert any remaining markdown bold to HTML (failsafe)
#                 import re
#                 ai_message = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', ai_message)
                
#                     # Save AI response
#                 ai_discuss = PlaceDiscussion.objects.create(
#                     discuss=ai_message,
#                     discusserName="Assistant",
#                     place=place
#                 )
#                 place.discussion.add(ai_discuss)
#                 _step("Saved AI response discussion")
#             except Exception as e:
#                 print(f"AI Error: {e}")
#                 _step(f"AI call failed: {type(e).__name__}")
            
#             objectRecords = place.discussions.order_by('-id').values()[:2]
#             _step("Returning latest 5 discussions")
#             return JsonResponse({"response": list(objectRecords)})
    
#     _step("No message provided; returning latest discussions")
#     objectRecords = place.discussions.order_by('-id').values()[:5]
#     return JsonResponse({"response": list(objectRecords)})
 

def _discussion_records(place, limit=5):
    return list(place.discussions.order_by("-id").values()[:limit])


def _discussion_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _discussion_username(request, data):
    username = data.get("username") if isinstance(data, dict) else ""
    if not username and getattr(request, "user", None) is not None and request.user.is_authenticated:
        username = request.user.username
    if not username:
        username = data.get("userID") if isinstance(data, dict) else ""
    if not username:
        username = _discussion_client_ip(request) or "Anonymous"
    return html.escape(str(username).strip()[:64] or "Anonymous", quote=True)


def _save_place_discussion(place, discuss, discusser_name):
    record = PlaceDiscussion.objects.create(
        discuss=discuss,
        place=place,
        discusserName=discusser_name,
    )
    place.discussion.add(record)
    return record


def _discussion_local_view(request, placeID):
    from datetime import timedelta

    if request.method not in {"GET", "POST"}:
        return JsonResponse({"error": "Method not allowed", "response": []}, status=405)

    if placeID is None:
        return JsonResponse({"error": "Missing placeID", "response": []}, status=400)

    try:
        place = Places_v2.objects.get(placeID=placeID)
    except Places_v2.DoesNotExist:
        return JsonResponse({"error": "Place not found", "response": []}, status=404)

    if request.method == "GET":
        return JsonResponse({"response": _discussion_records(place)})

    try:
        body_text = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(body_text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid JSON body", "response": []}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid JSON body", "response": []}, status=400)

    message_content = str(data.get("message") or "").strip()
    if not message_content:
        return JsonResponse({"response": _discussion_records(place)})

    if len(message_content) < 2:
        return JsonResponse({"error": "Message too short", "response": []}, status=400)
    if len(message_content) > 1000:
        return JsonResponse({"error": "Message too long", "response": []}, status=400)

    def Checkblog(human_message_prompt,place):
        # Combined AI processing with one call
        blog_keywords = ['create a blog','make a guide', 'make a blog']

        is_about_blogs = any(keyword in human_message_prompt for keyword in blog_keywords)
        # If user explicitly asks to create a blog/article, we should generate a new one
        # even if generic words match existing blog titles (e.g., "guide").
        create_blog_verbs = ['make', 'create', 'write', 'generate']
        create_blog_phrases = ['make a blog', 'create a blog', 'write a blog', 'generate a blog', 'make blog', 'create blog', 'write blog', 'generate blog']
        wants_new_blog = (
            any(p in human_message_prompt for p in create_blog_phrases)
            or ('blog' in human_message_prompt and any(v in human_message_prompt for v in create_blog_verbs))
            or ('article' in human_message_prompt and any(v in human_message_prompt for v in create_blog_verbs))
        )
        
        if is_about_blogs or wants_new_blog:
            import re
            from difflib import SequenceMatcher
            blogs = list(place.blogs.all())
            matched_blogs = []
            created_or_matched_blog_url = ""
            # direct token and n-gram matching

            print('---')
            for b in blogs:
                text = f"{getattr(b,'title','')} {getattr(b,'summarize','') or ''}".lower()
                sim = SequenceMatcher(a=human_message_prompt, b=text).ratio()
                if sim > 0.7:
                    matched_blogs.append((b, [f'fuzzy:{sim:.2f}']))
            max_match_blog = 1
            if len(matched_blogs) >= max_match_blog:
                print('\n\nMatched Blogs: ',matched_blogs)
                print(f"Found {len(matched_blogs)} relevant blogs/articles.\n\n")
                blog_context = "\n\nAvailable Blogs & Articles:\n"
                current_domain = request.build_absolute_uri('/').rstrip('/')
                from django.utils.text import slugify
                
                for blog_obj, matches in matched_blogs:
                    blog_context += f"📝 {blog_obj.title}"
                    
                    # Try to construct URL from various sources
                    blog_url = None
                    if hasattr(blog_obj, 'localurlpath') and blog_obj.localurlpath:
                        blog_url = f"{current_domain}{blog_obj.localurlpath}"
                    elif hasattr(blog_obj, 'url') and blog_obj.url:
                        blog_url = blog_obj.url
                        if 'http://127.0.0.1:8000' in blog_url:
                            blog_url = blog_url.replace('http://127.0.0.1:8000', current_domain)
                        elif 'localhost:8000' in blog_url:
                            blog_url = blog_url.replace('http://localhost:8000', current_domain)
                    elif hasattr(blog_obj, 'blogplace') and blog_obj.blogplace:
                        # Construct URL from place and blog title
                        place_slug = slugify(blog_obj.blogplace.slug or blog_obj.blogplace.placename)
                        title_slug = slugify(blog_obj.title)
                        blog_url = f"{current_domain}/pages/blog/{place_slug}/{title_slug}/"
                    
                    if blog_url:
                        if not created_or_matched_blog_url:
                            created_or_matched_blog_url = blog_url
                        blog_context += f" - URL: {blog_url}\n"
                    else:
                        blog_context += "\n"
            else:
                try:
                    blog_thread_result = {"url": "", "error": None}
                    def run_blog_creation():
                        from home.tasks import process_creating_blog
                        
                        try:
                            blog_thread_result["url"] = process_creating_blog(
                                request,
                                place,
                                None,
                                human_message_prompt,
                            ) or ""
                        except Exception as exc:
                            blog_thread_result["error"] = exc
                    import threading
                    blog_thread = threading.Thread(target=run_blog_creation)
                    blog_thread.start()
                    blog_thread.join()

                    if blog_thread_result["error"] is not None:
                        raise blog_thread_result["error"]

                    created_or_matched_blog_url = blog_thread_result["url"]


                except Exception as e:
                    print('Blog generation error:', e)
            print('Blog URL to be returned:', created_or_matched_blog_url)
            return {
                "is_about_blogs": True,
                "blog_url": created_or_matched_blog_url,
            }
        else:
            return {
                "is_about_blogs": False,
                "blog_url": "",
            }


    blog_check = Checkblog(message_content, place)
    is_about_blogs = blog_check.get("is_about_blogs", False)

    print('\n\n is_about_blogs:', is_about_blogs)
    if is_about_blogs:
        print('Message classified as about blogs/articles; returning blog context')
        return JsonResponse({
            "response": [],
            "blog_url": blog_check.get("blog_url", ""),
            "message": "Blog Created or Matched",
        })

    username_to_use = _discussion_username(request, data)
    now = timezone.now()
    one_minute_ago = now - timedelta(minutes=1)
    recent_messages = PlaceDiscussion.objects.filter(place=place, timestamp__gte=one_minute_ago)

    user_recent_count = recent_messages.filter(discusserName=username_to_use).count()
    if user_recent_count >= 5:
        return JsonResponse(
            {"error": "Rate limit exceeded. Please wait before sending more messages.", "response": []},
            status=429,
        )

    five_minutes_ago = now - timedelta(minutes=5)
    duplicate_exists = PlaceDiscussion.objects.filter(
        place=place,
        discuss__iexact=message_content,
        timestamp__gte=five_minutes_ago,
    ).exists()
    if duplicate_exists:
        return JsonResponse(
            {"error": "Duplicate message detected. Please wait before sending the same message.", "response": []},
            status=400,
        )

    ten_seconds_ago = now - timedelta(seconds=10)
    recent_user_message = recent_messages.filter(
        discusserName=username_to_use,
        timestamp__gte=ten_seconds_ago,
    ).exists()
    if recent_user_message:
        return JsonResponse({"error": "Please wait 10 seconds between messages.", "response": []}, status=429)

    message_type = classify_local_discussion_message(message_content)
    if message_type == "OFFENSIVE":
        return JsonResponse({"response": " "})

    safe_user_message = sanitize_user_message(message_content)
    if request.user.is_authenticated:
        try:
            ensure_user_profile(request.user)
        except Exception:
            pass

    _save_place_discussion(place, safe_user_message, username_to_use)

    if message_type == "NOT_QUESTION":
        return JsonResponse({"response": _discussion_records(place)})

    try:
        assistant_message = answer_discussion_message(message_content, place, request=request)
    except Exception:
        assistant_message = "I don't have enough local information about that yet."

    if assistant_message:
        _save_place_discussion(place, assistant_message, "Assistant")

    return JsonResponse({"response": _discussion_records(place, limit=2)})


discussion = _discussion_csrf(_discussion_local_view)


@csrf_exempt
def resortDB(request, resortID):  # not Used
    from django.http import JsonResponse
    from django.http import HttpResponse
    from .models import ResortMessages
    import json
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('guestMessage')
        contact = data.get('guestContact')
        webID = data.get('webID')
        # data = ResortMessages.objects.create(resortID=resortID,guestMessage=message,guestContact=contact)
        data = ResortMessages()
        data.resortID = resortID
        data.guestMessage = message
        data.guestContact = contact
        data.save()
        return

        # return HttpResponse(data, content_type="application/json")
        # return JsonResponse({"response": data},safe=False)
    elif request.method == 'GET':
        data = ResortMessages.objects.values()
        return JsonResponse({"messages": list(data)})

        # return JsonResponse({"response": f'RESPONSE DONE {resortID}'},safe=False)
    # return HttpResponse(f"Requested Path: ")
    # return HttpResponse('data', content_type="application/json")


def rooms(request):
    return render(request, 'rooms/rooms.html')


def exploreResort(request, id):
    return render(request, 'rooms/rooms.html')


def bad_request(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def permission_denied(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def page_not_found(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def server_error(request, exception=None):
    # return render(request, '500.html')
    # return HttpResponse('Failed', content_type="application/json")
    return redirect('/')


def scrappePage(request):
    from . import StandOnRunner as scraper
    # from StandOnRunner import testStandOn
    data = 'Put request method to PUT'
    # if request.method=='PUT':
    datas = scraper.testStandOn()

    variables = {
        'datas': datas
    }

    return render(request, 'home/ScrappingPage.html', variables)


def surfFacebookPostDirectly(request):
    from . import StandOnRunner as scraper
    scraper().surfData()

    return render(request, 'home/ScrappingPage.html')



# def scrape_siargao_events(request):
#     import requests
#     from bs4 import BeautifulSoup
#     from django.http import JsonResponse    
#     url = "https://siargaovibes.com/wp-admin/admin-ajax.php"

#     payload = {
#         "action": "get_listings",
#         "listing_type": "event",
#         "page": 1,
#         "per_page": 20,
#         "orderby": "rand",
#     }

#     headers = {
#         "User-Agent": "Mozilla/5.0",
#         "X-Requested-With": "XMLHttpRequest",
#         "Referer": "https://siargaovibes.com/explore/?type=event",
#     }

#     r = requests.post(url, data=payload, headers=headers, timeout=15)

#     # DEBUG – uncomment once
#     # print(r.text[:1000])

#     soup = BeautifulSoup(r.text, "html.parser")
#     print("STATUS:", r.status_code)
#     print("TEXT LENGTH:", len(r.text))
#     print("RAW RESPONSE:")
#     print(r.text[:1000])
#     results = []

#     # NOTE: grid-item EXISTS HERE
#     for item in soup.select(".grid-item"):
#         title = item.select_one(".listing-preview-title")
#         link = item.select_one("a[href]")

#         results.append({
#             "title": title.get_text(strip=True) if title else None,
#             "url": link["href"] if link else None,
#         })

#     return JsonResponse({
#         "count": len(results),
#         "results": results,
#     })


@csrf_exempt
def add_tour_guide(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=400)
        
        guide_username = request.POST.get('guide_username', '').strip()
        if not guide_username:
            return JsonResponse({'error': 'Guide username is required'}, status=400)
        
        try:
            from userProfile.models import TourGuide
            guide = TourGuide.objects.get(user__username=guide_username)
            guide.guided_tourists.add(request.user)
            guide.save()
            return JsonResponse({'success': True, 'message': f'Added to tour guide {guide_username}\'s guided tourists'})
        except TourGuide.DoesNotExist:
            return JsonResponse({'error': 'Tour guide not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def _strip_html_tags(html: str) -> str:
    return re.sub('<[^<]+?>', '', html or '')

def place_current_visitors(request, place_slug):
    """Show all tourists currently visiting tourist spots in a place"""
    from django.utils import timezone
    from datetime import timedelta
    from userProfile.models import TourGuide
    
    # Get the place
    place = get_object_or_404(Places_v2, slug=place_slug)
    
    # Get all tourist spots in this place
    tourist_spots = TouristSpot.objects.filter(place=place)
    
    # Get visits from the last 24 hours (considering them as "current visitors")
    # Since we don't have exit times, we'll show recent visits
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    current_visits = Visit.objects.filter(
        tourist_spot__in=tourist_spots,
        timestamp__gte=cutoff_time
    ).select_related('tourist_spot', 'tourist').order_by('-timestamp')
    
    # Group visits by tourist to avoid duplicates and include tour guide info
    tourists_by_spot = {}
    for visit in current_visits:
        spot_name = visit.tourist_spot.name
        if spot_name not in tourists_by_spot:
            tourists_by_spot[spot_name] = []
        
        # Check if this tourist has an active tour guide
        tour_guide = None
        try:
            # Find if this tourist is currently being guided
            guide_assignment = TourGuide.objects.filter(
                guided_tourists=visit.tourist
            ).first()
            if guide_assignment:
                tour_guide = guide_assignment
        except:
            pass
        
        # Check if visit is more than 24 hours old
        visit_time_local = timezone.localtime(visit.timestamp)
        is_overdue = (timezone.now() - visit.timestamp).total_seconds() > 24 * 3600
        # is_overdue = (timezone.now() - visit.timestamp).total_seconds() > 1 * 1
        
        
        tourists_by_spot[spot_name].append({
            'tourist': visit.tourist,
            'visit_time': visit.timestamp,
            'visit_time_local': visit_time_local,
            'tour_guide': tour_guide,
            'is_overdue': is_overdue
        })
    
    context = {
        'place': place,
        'tourists_by_spot': tourists_by_spot,
        'total_visitors': sum(len(tourists) for tourists in tourists_by_spot.values()),
        'cutoff_hours': 24
    }
    
    return render(request, 'home/place_current_visitors.html', context)
@csrf_exempt
def search_tourist_spots_by_placename(request, place_slug):
    """Accepts a placename, finds the place, and lists all tourist spots for that place."""
    from django.shortcuts import render, get_object_or_404
    from .models import Places_v2, TouristSpot

    context = {}
    # if request.method == 'POST':
    placename = request.POST.get('placename', '').strip()
    if not placename:
        context['error'] = 'Please enter a placename.'
    else:
        place = Places_v2.objects.filter(placename__iexact=placename).first()
        if not place:
            context['error'] = f'No place found with name "{placename}".'
        else:
            spots = TouristSpot.objects.filter(place=place)
            spots = place.tourist_spots.all()
            context['place'] = place
            context['spots'] = spots
            context['placename'] = placename
    return render(request, 'home/tourist_spots.html', context)
     


@csrf_exempt
def create_tourist_spot(request):


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

#         if not name or not place_id:
#             return render(request, "home/tourist_spot_create.html", {
#                 "places": Places_v2.objects.all(),
#                 "resorts": ResortItem.objects.all(),
#                 "error": "Place and Name are required"
#             })

#         coords = None
#         if latitude and longitude:
#             try:
#                 coords = {
#                     "latitude": float(latitude),
#                     "longitude": float(longitude)
#                 }
#             except:
#                 pass
# # ----------- Processing Spot
#         if not desc:
#             try:
#                 print(f"   ⏳ Generating description...")
#                 prompt = f"Write a short 1-2 sentence tourist description of {name} in {place.placename}"
#                 res = client.chat.completions.create(
#                     model=settings.GROK_MODEL_NAME,
#                     messages=[{"role": "user", "content": prompt}],
#                     max_tokens=100
#                 )
#                 desc = res.choices[0].message.content.strip()
#                 # spot.save()
#                 print(f"   ✅ Description saved")
#             except Exception as e:
#                 print("DESC ERROR:", e)
#         else:
#             print(f"   ✅ Description already exists")
#         if not picture:
#             try:
#                 print(f"   ⏳ Fetching image...")

#                 from webSchedule.utils import upload_to_imgbb
                
#                 image = getPlacePhoto(None, name)
#                 if picture:
#                     try:
#                         print(f"   ⏳ Uploading image to imgbb...")
#                         picture = upload_to_imgbb(image)
#                     except:
#                         print("     Failed to upload in IMBB saving as url instead")
#                         picture = image

#                     print("   ✅ Image saved")
#                 else:
#                     print(f"   ⚠️  No image found for {name}")
#             except Exception as e:
#                 print("IMG ERROR:", e)
#         else:
#             print(f"   ✅ Image already exists")

#         # ✅ Create immediately (FAST)
#         spot = TouristSpot.objects.create(
#             place=place,
#             name=name,
#             slug=slug,
#             desc=desc or "",
#             coords=coords,
#             img=picture
#         )
 
#         if not spot.spot_id:
#             spot.spot_id = f"SPOT-{spot.id}"
#             spot.save()

#         if resort_ids:
#             resorts = ResortItem.objects.filter(id__in=resort_ids)
#             spot.resortItem.set(resorts)

        # ✅ Run heavy tasks in background
        threading.Thread(
            target=process_creating_blog,
            args=(request,place,name,None,True,),
            daemon=True
        ).start()

        return render(request, "home/tourist_spot_create.html", {
            "places": Places_v2.objects.all(),
            "resorts": ResortItem.objects.all(),
            # "success_message": f'{spot.name} created successfully (processing in background)'
            "success_message": f'created successfully (processing in background)'
        })

    return render(request, "home/tourist_spot_create.html", {
        "places": Places_v2.objects.all(),
        "resorts": ResortItem.objects.all()
    })

def get_tour_guide_info(request, username):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from userProfile.models import TourGuide
        guide = TourGuide.objects.select_related('user__additionalCreds').get(user__username=username)
        photo = guide.user.additionalCreds.photo if guide.user.additionalCreds.photo else None
        name = guide.user.additionalCreds.name or guide.user.username
        return JsonResponse({'photo': photo, 'name': name})
    except TourGuide.DoesNotExist:
        return JsonResponse({'error': 'Tour guide not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_place_latest_visit_timestamp(request, place_slug):
    """Get the latest visit timestamp for a place to check for updates"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        from home.models import TouristVisit, Places_v2
        place = Places_v2.objects.get(slug=place_slug)
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        
        latest_visit = TouristVisit.objects.filter(
            spot__place=place,
            timestamp__gte=cutoff_time
        ).order_by('-timestamp').first()
        
        if latest_visit:
            return JsonResponse({
                'latest_timestamp': latest_visit.timestamp.isoformat(),
                'has_visitors': True
            })
        else:
            return JsonResponse({
                'latest_timestamp': None,
                'has_visitors': False
            })
    except Places_v2.DoesNotExist:
        return JsonResponse({'error': 'Place not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def resort_by_slugs(request, place_slug, resort_slug):
    """Handle resort URLs in the format /<place-slug>/<resort-slug>/"""
    from resorts.views import getResortBySlug
    return getResortBySlug(request, place_slug, resort_slug)


@require_POST
def join_schedule(request, schedule_id):
    """Handle user joining a schedule"""
    from .models import Joiner
    import json
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'You must be logged in to join', 'logged_in': False}, status=401)
    
    try:
        schedule = allSchedules.objects.get(id=schedule_id)
    except allSchedules.DoesNotExist:
        return JsonResponse({'error': 'Schedule not found'}, status=404)
    
    # Check if user already joined
    existing = Joiner.objects.filter(user=request.user, schedule=schedule).first()
    if existing:
        return JsonResponse({
            'message': 'You have already joined this schedule',
            'already_joined': True,
            'joiner_id': existing.id
        }, status=200)
    
    # Get optional pick location from request
    pick_location = request.POST.get('pickLocation', '').strip()
    pick_coordinate_str = request.POST.get('pickCoordinate', '').strip()
    pick_contact = request.POST.get('pickContact', '').strip()
    ip_address = get_client_ip(request)
    print(f"User {request.user.username} pick location {pick_location} joining schedule {schedule.id} from IP {ip_address}")
    # Parse pick_coordinate if it's JSON
    pick_coordinate = ''
    if pick_coordinate_str:
        try:
            coord_data = json.loads(pick_coordinate_str)
            # Format as "lat,lng" or store as JSON string
            pick_coordinate = json.dumps(coord_data)
        except json.JSONDecodeError:
            pick_coordinate = pick_coordinate_str
    
    # Create the joiner
    joiner = Joiner.objects.create(
        user=request.user,
        schedule=schedule,
        pickLocation=pick_location,
        pickCoordinate=pick_coordinate,
        ip_address=ip_address,
        contact=pick_contact,
    )
    
    return JsonResponse({
        'message': 'Successfully joined the schedule!',
        'success': True,
        'joiner_id': joiner.id,
        'schedule_id': schedule.id,
        'location_recorded': bool(pick_coordinate)
    }, status=201)


@require_POST
def delete_schedule(request, schedule_id):
    """Delete a schedule (poster-only)."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'You must be logged in to delete a schedule', 'logged_in': False}, status=401)

    try:
        schedule = allSchedules.objects.get(id=schedule_id)
    except allSchedules.DoesNotExist:
        return JsonResponse({'error': 'Schedule not found'}, status=404)

    # Allow by FK (preferred) and also by posterID (legacy) for safety
    is_owner_by_fk = (schedule.poster == request.user)
    is_owner_by_id = (schedule.posterID and str(schedule.posterID) == str(getattr(request.user, 'id', None)))
    if not (is_owner_by_fk or is_owner_by_id):
        return JsonResponse({'error': 'You do not have permission to delete this schedule'}, status=403)

    schedule.delete()
    return JsonResponse({'success': True, 'message': 'Schedule deleted', 'schedule_id': schedule_id}, status=200)


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_schedule_joiners(request, schedule_id):
    """Get all joiners for a specific schedule"""
    from .models import Joiner
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'You must be logged in to view joiners', 'logged_in': False}, status=401)
    
    try:
        schedule = allSchedules.objects.get(id=schedule_id)
    except allSchedules.DoesNotExist:
        return JsonResponse({'error': 'Schedule not found'}, status=404)
    
    # Check if the user is the poster of this schedule
    if schedule.poster != request.user:
        return JsonResponse({'error': 'You do not have permission to view joiners for this schedule'}, status=403)
    
    # Get all joiners for this schedule
    joiners = Joiner.objects.filter(schedule=schedule).select_related('user')
    
    joiner_list = []
    for joiner in joiners:
        joiner_list.append({
            'id': joiner.id,
            'userName': joiner.user.username if joiner.user else 'Anonymous',
            'userEmail': joiner.user.email if joiner.user else '',
            'pickLocation': joiner.pickLocation,
            'pickCoordinate': joiner.pickCoordinate,
            'contact': joiner.contact,
            'timestamp': joiner.timestamp.isoformat() if joiner.timestamp else ''
        })
    
    return JsonResponse({
        'success': True,
        'schedule_id': schedule_id,
        'schedule_title': schedule.scheduleTitle,
        'total_joiners': len(joiner_list),
        'joiners': joiner_list
    }, status=200)


def add_facebook_page(request):
    if request.method == 'POST':
        form = FacebookPageForm(request.POST)
        if form.is_valid():
            fb_page = form.save()
            place = form.cleaned_data['place']
            place.facebook_pages.add(fb_page)
            return redirect('home:add_facebook_page')  # Or some success message
    else:
        form = FacebookPageForm()
    return render(request, 'home/add_facebook_page.html', {'form': form})

def storeproducts_management(request):
    return render(request, 'home/storeproducts.html')


def robots_txt(request):
    """
    Serve robots.txt file.
    Instructs search engines how to crawl the site.
    """
    return render(request, 'robots.txt', content_type='text/plain')


def privacy_policy(request):
    """
    Render privacy policy page.
    """
    return render(request, 'privacy_policy.html')

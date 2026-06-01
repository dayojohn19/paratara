import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from ai_chat.models import PlaceKnowledgeEmbedding
from ai_chat.services.embedding_service import cosine_similarity, embed_text, embed_texts


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeDocument:
    source_type: str
    source_id: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)

    @property
    def content_hash(self):
        payload = {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "text": self.text,
            "metadata": self.metadata,
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


STOP_TOKENS = {
    "what", "where", "when", "which", "who", "how", "can", "you", "please", "the",
    "and", "for", "with", "near", "around", "from", "into", "about", "that",
    "this", "there", "have", "has", "any", "are", "available", "looking", "need",
    "want", "find", "give", "show", "tell", "list", "best", "good", "your",
    "here", "place", "places",
}


def clean_text(value, limit=None):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].strip() + "..."
    return text


def safe_url(value):
    url = str(value or "").strip()
    if url.startswith(("http://", "https://", "/")):
        return url
    return ""


def _public_base_url(request=None):
    if request is not None:
        try:
            return request.build_absolute_uri("/").rstrip("/")
        except Exception:
            pass
    return str(
        getattr(settings, "AI_DISCUSSION_PUBLIC_BASE_URL", "")
        or getattr(settings, "DJANGO_PAYMENT_BASE_URL", "")
        or ""
    ).rstrip("/")


def blog_url(blog_obj, request=None):
    base_url = _public_base_url(request)
    local_path = str(getattr(blog_obj, "localurlpath", "") or "").strip()
    if local_path:
        if local_path.startswith(("http://", "https://")):
            return local_path
        if not local_path.startswith("/"):
            local_path = f"/{local_path}"
        return f"{base_url}{local_path}" if base_url else local_path

    external_url = str(getattr(blog_obj, "url", "") or "").strip()
    if external_url:
        if base_url:
            external_url = external_url.replace("http://127.0.0.1:8000", base_url)
            external_url = external_url.replace("http://localhost:8000", base_url)
        return external_url

    blog_place = getattr(blog_obj, "blogplace", None)
    if blog_place:
        place_slug = slugify(getattr(blog_place, "slug", "") or getattr(blog_place, "placename", ""))
        title_slug = slugify(getattr(blog_obj, "title", ""))
        if place_slug and title_slug:
            path = f"/pages/blog/{place_slug}/{title_slug}/"
            return f"{base_url}{path}" if base_url else path
    return ""


def _add_document(docs, source_type, source_id, title, text_parts, metadata=None):
    text = "\n".join(clean_text(part) for part in text_parts if clean_text(part))
    title = clean_text(title, 255)
    if not title and not text:
        return

    metadata = dict(metadata or {})
    metadata.setdefault("kind", source_type)
    metadata.setdefault("source_type", source_type)
    metadata.setdefault("source_id", str(source_id))
    metadata.setdefault("title", title)

    docs.append(
        KnowledgeDocument(
            source_type=source_type,
            source_id=str(source_id)[:100],
            title=title,
            text=text,
            metadata=metadata,
        )
    )


def _resort_amenities(resort):
    fields = {
        "has_wifi": "WiFi",
        "has_pool": "Pool",
        "has_bidet": "Bidet",
        "has_parking": "Parking",
        "has_restaurant": "Restaurant",
        "has_bar": "Bar",
        "has_spa": "Spa",
        "has_gym": "Gym",
        "has_beach_access": "Beach access",
        "has_air_conditioning": "Air conditioning",
        "has_hot_water": "Hot water",
        "has_breakfast": "Breakfast",
        "has_laundry": "Laundry",
        "pet_friendly": "Pet friendly",
        "family_friendly": "Family friendly",
        "has_generator": "Generator",
    }
    return [label for field_name, label in fields.items() if getattr(resort, field_name, False)]


def _package_documents(docs, resort, relation_name, source_type, label, now):
    resort_name = clean_text(getattr(resort, "RealName", "") or getattr(resort, "name", ""))
    phone = clean_text(getattr(resort, "contactNumber", ""))
    email = clean_text(getattr(resort, "contactEmail", ""))
    resort_website = safe_url(getattr(resort, "websiteURL", ""))

    try:
        packages = getattr(resort, relation_name).all()
    except AttributeError:
        return

    for package in packages[:30]:
        package_title = clean_text(getattr(package, "PackageTitle", ""))
        subpackages = list(getattr(package, "subPackages", []).all()[:30])
        if not subpackages:
            _add_document(
                docs,
                source_type,
                f"{getattr(resort, 'pk', '')}:{relation_name}:{getattr(package, 'pk', '')}",
                package_title,
                [
                    f"Kind: {label}",
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
            expires_at = getattr(sub, "expires_at", None)
            if getattr(sub, "is_available", True) is False:
                continue
            if expires_at and expires_at <= now:
                continue

            sub_title = clean_text(getattr(sub, "title", ""))
            description = clean_text(getattr(sub, "description", ""), 320)
            information = clean_text(getattr(sub, "information", ""), 320)
            price = getattr(sub, "price", 0) or ""
            item_website = safe_url(getattr(sub, "website", ""))
            _add_document(
                docs,
                source_type,
                f"{getattr(resort, 'pk', '')}:{relation_name}:{getattr(package, 'pk', '')}:{getattr(sub, 'pk', '')}",
                sub_title or package_title,
                [
                    f"Kind: {label}",
                    f"Resort: {resort_name}",
                    f"Package: {package_title}",
                    f"Title: {sub_title}",
                    f"Description: {description}",
                    f"Information: {information}",
                    f"Price: {price}",
                    f"Item website: {item_website}",
                    f"Contact phone: {phone}",
                    f"Contact email: {email}",
                    f"Resort website: {resort_website}",
                ],
                {
                    "kind_label": label,
                    "resort": resort_name,
                    "package_title": package_title,
                    "summary": description or information,
                    "price": str(price) if price else "",
                    "url": item_website,
                    "phone": phone,
                    "email": email,
                    "website": resort_website,
                },
            )


def collect_place_knowledge_documents(place, request=None):
    docs = []
    place_name = clean_text(getattr(place, "placename", "") or getattr(place, "name", ""))
    now = timezone.now()

    _add_document(
        docs,
        "place",
        getattr(place, "pk", "") or getattr(place, "placeID", ""),
        place_name,
        [
            "Kind: Place destination overview",
            f"Place: {place_name}",
            f"Slug: {getattr(place, 'slug', '')}",
        ],
        {"kind_label": "Place", "summary": place_name},
    )

    try:
        from apis.models import Blogs

        blogs = Blogs.objects.filter(Q(blogplace=place) | Q(bloglists=place)).distinct().order_by("-timestamp")[:40]
    except Exception:
        blogs = []

    for blog in blogs:
        title = clean_text(getattr(blog, "title", ""))
        summary = clean_text(getattr(blog, "summarize", ""), 260)
        body = clean_text(getattr(blog, "textContent", ""), 900)
        url = safe_url(blog_url(blog, request))
        _add_document(
            docs,
            "blog",
            getattr(blog, "pk", ""),
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
                "url": url,
                "summary": summary or body,
            },
        )

    try:
        resorts = place.resortList.prefetch_related(
            "resortAccomodations__subPackages",
            "resortActivities__subPackages",
            "resortTour__subPackages",
            "resortFood__subPackages",
        )
    except Exception:
        resorts = []

    for resort in list(resorts[:50]):
        resort_name = clean_text(getattr(resort, "RealName", "") or getattr(resort, "name", ""))
        description = clean_text(getattr(resort, "description", ""), 420)
        address = clean_text(getattr(resort, "address", ""))
        phone = clean_text(getattr(resort, "contactNumber", ""))
        email = clean_text(getattr(resort, "contactEmail", ""))
        website = safe_url(getattr(resort, "websiteURL", ""))
        amenities = _resort_amenities(resort)
        amenities_text = ", ".join(amenities)
        _add_document(
            docs,
            "resort",
            getattr(resort, "pk", ""),
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
        _package_documents(docs, resort, "resortAccomodations", "accommodation", "Room", now)
        _package_documents(docs, resort, "resortFood", "food", "Food", now)
        _package_documents(docs, resort, "resortActivities", "activity", "Activity", now)
        _package_documents(docs, resort, "resortTour", "tour", "Tour", now)

    try:
        events = place.eventList.all().order_by("yearN", "monthN", "dateN")[:80]
    except Exception:
        events = []

    for event in events:
        title = clean_text(getattr(event, "scheduleTitle", ""))
        exact_date = clean_text(getattr(event, "exactDate", ""))
        event_place = clean_text(getattr(event, "schedulePlace", ""))
        details = clean_text(getattr(event, "additionalDetails", "") or getattr(event, "otherDetails", ""), 360)
        website = safe_url(getattr(event, "scheduleWebsite", ""))
        cost = clean_text(getattr(event, "scheduleCost", ""))
        _add_document(
            docs,
            "event",
            getattr(event, "pk", ""),
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
                "summary": " ".join(part for part in [exact_date, event_place] if part),
                "price": cost,
            },
        )

    try:
        from userProfile.models import TourGuide

        guides = (
            TourGuide.objects.filter(is_active=True)
            .filter(Q(primary_place=place) | Q(tourist_spots__place=place))
            .select_related("user", "primary_place")
            .distinct()[:30]
        )
    except Exception:
        guides = []

    for guide in guides:
        user = getattr(guide, "user", None)
        username = clean_text(getattr(user, "username", "") or "Tour Guide")
        email = clean_text(getattr(user, "email", ""))
        phone = clean_text(getattr(guide, "mobile_number", ""))
        bio = clean_text(getattr(guide, "bio", ""), 360)
        certifications = clean_text(getattr(guide, "certifications", ""), 240)
        experience = getattr(guide, "experience_years", 0) or 0
        _add_document(
            docs,
            "tour_guide",
            getattr(guide, "pk", ""),
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

    try:
        tourist_spots = place.tourist_spots.all()[:50]
    except Exception:
        tourist_spots = []

    for spot in tourist_spots:
        name = clean_text(getattr(spot, "name", ""))
        desc = clean_text(getattr(spot, "desc", ""), 420)
        url = safe_url(getattr(spot, "url", ""))
        _add_document(
            docs,
            "tourist_spot",
            getattr(spot, "pk", ""),
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

    try:
        from home.models import PlaceDiscussion

        discussions = (
            PlaceDiscussion.objects.filter(Q(place=place) | Q(discussionsLists=place))
            .exclude(discusserName__iexact="Assistant")
            .distinct()
            .order_by("-id")[:40]
        )
    except Exception:
        discussions = []

    for discussion in discussions:
        message = clean_text(getattr(discussion, "discuss", ""), 500)
        if not message:
            continue
        _add_document(
            docs,
            "discussion",
            getattr(discussion, "pk", ""),
            clean_text(getattr(discussion, "discusserName", "Discussion"), 80),
            [
                "Kind: Previous local discussion message",
                f"Place: {place_name}",
                f"Message: {message}",
            ],
            {
                "kind_label": "Discussion",
                "summary": message,
            },
        )

    return docs


def query_tokens(message):
    tokens = re.findall(r"[a-z0-9]{3,}", (message or "").lower())
    seen = set()
    return [
        token
        for token in tokens
        if token not in STOP_TOKENS and not (token in seen or seen.add(token))
    ]


def intent_kinds(message):
    lower = (message or "").lower()
    if any(term in lower for term in ["tour guide", "tourguide", "local guide", "private guide", "hire a guide"]):
        return ["tour_guide"]
    if any(term in lower for term in ["food", "restaurant", "eat", "dining", "menu", "breakfast", "lunch", "dinner", "coffee", "drink"]):
        return ["food", "resort"]
    if any(term in lower for term in ["room", "stay", "hotel", "resort", "accommodation", "booking"]):
        return ["accommodation", "resort"]
    if any(term in lower for term in ["event", "events", "festival", "schedule", "happening"]):
        return ["event"]
    if any(term in lower for term in ["activity", "activities", "things to do", "what to do", "tour", "surf", "snorkel", "rent"]):
        return ["activity", "tour", "tourist_spot"]
    if any(term in lower for term in ["blog", "article"]):
        return ["blog"]
    return []


def lexical_matches(message, docs, top_k=6):
    tokens = query_tokens(message)
    preferred_kinds = intent_kinds(message)

    if not tokens and preferred_kinds:
        return [
            _match_from_doc(doc, score=0.1)
            for doc in docs
            if doc.metadata.get("kind") in preferred_kinds
        ][:top_k]

    scored = []
    phrase = clean_text(message).lower()
    for doc in docs:
        metadata = doc.metadata
        title = str(metadata.get("title", "")).lower()
        kind = str(metadata.get("kind", "")).lower()
        text = str(doc.text or "").lower()
        haystack = f"{kind} {title} {text}"
        score = 0.0

        if preferred_kinds and metadata.get("kind") in preferred_kinds:
            score += 2.5

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
            scored.append(_match_from_doc(doc, score=score))

    scored.sort(key=lambda item: item["score"], reverse=True)
    return dedupe_matches(scored[:top_k])


def _match_from_doc(doc, score=0.0):
    metadata = dict(doc.metadata or {})
    metadata.setdefault("title", doc.title)
    metadata.setdefault("kind", doc.source_type)
    return {
        "text": doc.text,
        "metadata": metadata,
        "score": float(score),
        "source_type": doc.source_type,
        "source_id": doc.source_id,
        "title": doc.title,
    }


def _match_from_record(record, score=0.0):
    metadata = dict(record.metadata or {})
    metadata.setdefault("title", record.title)
    metadata.setdefault("kind", record.source_type)
    return {
        "text": record.text,
        "metadata": metadata,
        "score": float(score),
        "source_type": record.source_type,
        "source_id": record.source_id,
        "title": record.title,
    }


def dedupe_matches(matches):
    deduped = []
    seen = set()
    for match in matches:
        metadata = match.get("metadata", {})
        key = (
            match.get("source_type") or metadata.get("kind", ""),
            match.get("source_id") or metadata.get("source_id", ""),
            metadata.get("title", ""),
            metadata.get("resort", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
    return deduped


def retrieve_semantic_context(message, place, top_k=None, min_score=None):
    top_k = top_k or getattr(settings, "AI_DISCUSSION_TOP_K", 6)
    min_score = min_score if min_score is not None else getattr(settings, "AI_DISCUSSION_MIN_SCORE", 0.25)

    try:
        records = list(PlaceKnowledgeEmbedding.objects.filter(place=place))
    except (OperationalError, ProgrammingError) as exc:
        logger.warning("Discussion knowledge table unavailable: %s", exc)
        return []

    if not records:
        return []

    query_vector = embed_text(message)
    scored = []
    for record in records:
        score = cosine_similarity(query_vector, record.embedding)
        if score >= min_score:
            scored.append(_match_from_record(record, score=score))

    scored.sort(key=lambda item: item["score"], reverse=True)
    return dedupe_matches(scored[:top_k])


def retrieve_deterministic_context(message, place, request=None, top_k=None):
    docs = collect_place_knowledge_documents(place, request=request)
    return lexical_matches(message, docs, top_k=top_k or getattr(settings, "AI_DISCUSSION_TOP_K", 6))


def retrieve_discussion_context(message, place, request=None, top_k=None):
    top_k = top_k or getattr(settings, "AI_DISCUSSION_TOP_K", 6)
    semantic_matches = []
    try:
        semantic_matches = retrieve_semantic_context(message, place, top_k=top_k)
    except Exception as exc:
        logger.warning("Semantic discussion retrieval failed: %s", exc)

    deterministic_matches = retrieve_deterministic_context(message, place, request=request, top_k=top_k)
    combined = semantic_matches + deterministic_matches
    combined = dedupe_matches(combined)
    combined.sort(key=lambda item: item.get("score", 0), reverse=True)
    return combined[:top_k]


def index_place_knowledge(place, request=None, delete_stale=True):
    docs = collect_place_knowledge_documents(place, request=request)
    current_keys = {(doc.source_type, doc.source_id) for doc in docs}
    created = 0
    updated = 0
    skipped = 0
    deleted = 0

    pending_docs = []
    for doc in docs:
        existing = PlaceKnowledgeEmbedding.objects.filter(
            place=place,
            source_type=doc.source_type,
            source_id=doc.source_id,
        ).only("id", "content_hash").first()
        if existing and existing.content_hash == doc.content_hash:
            skipped += 1
            continue
        pending_docs.append((doc, existing is None))

    batch_size = getattr(settings, "AI_DISCUSSION_EMBEDDING_BATCH_SIZE", 16)
    for start in range(0, len(pending_docs), batch_size):
        batch = pending_docs[start:start + batch_size]
        vectors = embed_texts([doc.text for doc, _is_new in batch])
        for (doc, is_new), vector in zip(batch, vectors):
            PlaceKnowledgeEmbedding.objects.update_or_create(
                place=place,
                source_type=doc.source_type,
                source_id=doc.source_id,
                defaults={
                    "title": doc.title,
                    "text": doc.text,
                    "embedding": vector,
                    "metadata": doc.metadata,
                    "content_hash": doc.content_hash,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

    if delete_stale:
        existing = PlaceKnowledgeEmbedding.objects.filter(place=place).only("id", "source_type", "source_id")
        for record in existing:
            if (record.source_type, record.source_id) not in current_keys:
                record.delete()
                deleted += 1

    return {
        "placeID": getattr(place, "placeID", None),
        "documents": len(docs),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "deleted": deleted,
    }


import html
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser

from django.conf import settings

from ai_chat.services.discussion_retrieval_service import (
    blog_url,
    clean_text,
    intent_kinds,
    retrieve_discussion_context,
    safe_url,
)
from ai_chat.services.local_llm_service import discussion_backend, generate_local_llm_answer


logger = logging.getLogger(__name__)

NOT_ENOUGH_INFORMATION = "I don't have enough local information about that yet."


@dataclass(frozen=True)
class BlogIntentResult:
    is_about_blogs: bool
    blog_url: str = ""
    matched_title: str = ""


class _AllowedHTMLParser(HTMLParser):
    allowed_tags = {"strong", "a", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "strong":
            self.parts.append("<strong>")
        elif tag == "br":
            self.parts.append("<br>")
        elif tag == "a":
            attrs_dict = dict(attrs)
            href = safe_url(attrs_dict.get("href", ""))
            if href:
                self.parts.append(
                    '<a href="{}" target="_blank" rel="noopener">'.format(
                        html.escape(href, quote=True)
                    )
                )

    def handle_endtag(self, tag):
        if tag in {"strong", "a"}:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(html.escape(data, quote=True))

    def get_html(self):
        return "".join(self.parts)


def sanitize_html_fragment(value):
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", str(value or ""))
    parser = _AllowedHTMLParser()
    parser.feed(value)
    return parser.get_html().strip()


def sanitize_user_message(value):
    return html.escape(clean_text(value, 1000), quote=True)


def classify_discussion_message(message):
    lower = (message or "").strip().lower()
    if not lower:
        return "NOT_QUESTION"

    offensive_terms = [
        "fuck", "shit", "bitch", "asshole", "kill yourself", "kys",
    ]
    if any(term in lower for term in offensive_terms):
        return "OFFENSIVE"

    create_verbs = ["make", "create", "write", "generate"]
    if (
        any(phrase in lower for phrase in ["make a blog", "create a blog", "write a blog", "generate a blog"])
        or ("blog" in lower and any(verb in lower for verb in create_verbs))
        or ("article" in lower and any(verb in lower for verb in create_verbs))
    ):
        return "BLOG"

    greeting_only = {
        "hi", "hello", "hey", "thanks", "thank you", "salamat", "ok", "okay",
        "nice", "good morning", "good afternoon", "good evening",
    }
    if lower in greeting_only:
        return "NOT_QUESTION"

    question_terms = [
        "?", "what", "where", "when", "which", "who", "how", "can i", "can you",
        "do you", "is there", "are there", "looking for", "need", "want", "find",
        "recommend", "suggest", "available", "price", "cost", "book", "contact",
    ]
    topic_terms = [
        "resort", "hotel", "stay", "room", "accommodation", "booking", "food",
        "restaurant", "eat", "dining", "menu", "activity", "activities", "things to do",
        "tour", "event", "schedule", "festival", "tour guide", "local guide", "blog",
        "article", "spot", "visit", "where to",
    ]
    if any(term in lower for term in question_terms) or any(term in lower for term in topic_terms):
        return "QUESTION"

    return "NOT_QUESTION"


def check_blog_intent(message, place, request=None):
    lower = (message or "").strip().lower()
    if not lower:
        return BlogIntentResult(False)
    if "tour guide" in lower or "local guide" in lower:
        return BlogIntentResult(False)

    create_verbs = ["make", "create", "write", "generate"]
    explicit_create = (
        any(phrase in lower for phrase in ["make a blog", "create a blog", "write a blog", "generate a blog"])
        or ("blog" in lower and any(verb in lower for verb in create_verbs))
        or ("article" in lower and any(verb in lower for verb in create_verbs))
    )
    about_blog = explicit_create or any(term in lower for term in ["blog", "article", "travel guide"])
    if not about_blog:
        return BlogIntentResult(False)

    try:
        from apis.models import Blogs

        blogs = Blogs.objects.filter(bloglists=place).distinct()
        blogs = blogs | Blogs.objects.filter(blogplace=place).distinct()
    except Exception as exc:
        logger.warning("Blog lookup failed for discussion: %s", exc)
        blogs = []

    best_blog = None
    best_score = 0.0
    message_tokens = set(re.findall(r"[a-z0-9]{3,}", lower))
    for blog in blogs:
        title = clean_text(getattr(blog, "title", ""))
        summary = clean_text(getattr(blog, "summarize", ""))
        text = f"{title} {summary}".lower()
        sequence_score = SequenceMatcher(a=lower, b=text).ratio()
        blog_tokens = set(re.findall(r"[a-z0-9]{3,}", text))
        overlap_score = len(message_tokens & blog_tokens) / max(len(message_tokens), 1)
        score = max(sequence_score, overlap_score)
        if score > best_score:
            best_score = score
            best_blog = blog

    if best_blog is not None and best_score >= 0.35:
        return BlogIntentResult(True, blog_url=safe_url(blog_url(best_blog, request)), matched_title=best_blog.title)

    # Discussion no longer calls paid/cloud AI to create blogs. The frontend keeps
    # the same response shape and can decide how to handle an empty blog_url.
    if explicit_create:
        return BlogIntentResult(True)

    return BlogIntentResult(False)


def _link_html(url, title):
    url = safe_url(url)
    if not url:
        return ""
    return (
        f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">'
        f"{html.escape(clean_text(title, 80), quote=True)}</a>"
    )


def _short_summary(value, limit=140):
    summary = clean_text(value, limit)
    return html.escape(summary, quote=True) if summary else ""


def _format_contact(metadata):
    parts = []
    phone = clean_text(metadata.get("phone", ""))
    email = clean_text(metadata.get("email", ""))
    website = safe_url(metadata.get("website", ""))
    if phone:
        parts.append(f"Phone: {html.escape(phone, quote=True)}")
    if email:
        parts.append(f"Email: {html.escape(email, quote=True)}")
    if website:
        parts.append(_link_html(website, "Website"))
    return " ".join(part for part in parts if part)


def _format_match_html(match):
    metadata = match.get("metadata", {})
    kind = metadata.get("kind", match.get("source_type", ""))
    kind_label = metadata.get("kind_label") or kind.replace("_", " ").title() or "Result"
    title = clean_text(metadata.get("title") or match.get("title") or "", 90)
    resort = clean_text(metadata.get("resort", ""), 80)
    summary = _short_summary(metadata.get("summary") or match.get("text", ""), 140)
    price = clean_text(metadata.get("price", ""))

    title_text = html.escape(title, quote=True)
    if resort and kind not in {"resort", "tour_guide"}:
        title_text = f"{title_text} at <strong>{html.escape(resort, quote=True)}</strong>"

    parts = [f"<strong>{html.escape(kind_label, quote=True)}: {title_text}</strong>"]
    if summary:
        parts.append(summary)
    if price:
        parts.append(f"Price: {html.escape(price, quote=True)}")

    contact = _format_contact(metadata)
    if contact and kind in {"resort", "accommodation", "food", "activity", "tour", "tour_guide"}:
        parts.append(f"Contact: {contact}")

    url = metadata.get("url") or metadata.get("item_website")
    link_title = "Read article" if kind == "blog" else "Open link"
    link = _link_html(url, link_title)
    if link:
        parts.append(link)

    return ". ".join(part for part in parts if part)


def _preferred_matches(message, matches):
    preferred = intent_kinds(message)
    if not preferred:
        return matches
    filtered = [match for match in matches if match.get("metadata", {}).get("kind") in preferred]
    return filtered or matches


def _word_count_html(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return len(re.findall(r"\b\w+\b", text))


def generate_template_answer(message, place, matches):
    matches = _preferred_matches(message, matches)
    if not matches:
        return NOT_ENOUGH_INFORMATION

    place_name = html.escape(clean_text(getattr(place, "placename", "") or "this place"), quote=True)
    rendered = [_format_match_html(match) for match in matches[:2]]
    rendered = [item for item in rendered if item]
    if not rendered:
        return NOT_ENOUGH_INFORMATION

    answer = f"..._ " + " ".join(rendered)
    if _word_count_html(answer) > 80 and len(rendered) > 1:
        answer = f"For <strong>{place_name}</strong>, try this: {rendered[0]}"
    return sanitize_html_fragment(answer)


def answer_discussion_message(message, place, request=None):
    matches = retrieve_discussion_context(message, place, request=request)
    if not matches:
        return NOT_ENOUGH_INFORMATION

    backend = discussion_backend()
    if backend in {"ollama", "llama_cpp"}:
        place_name = clean_text(getattr(place, "placename", "") or "this place")
        try:
            llm_answer = generate_local_llm_answer(message, place_name, matches)
            llm_answer = sanitize_html_fragment(llm_answer)
            if llm_answer:
                return llm_answer
        except Exception as exc:
            logger.warning("Local LLM backend failed; using template fallback: %s", exc)

    return generate_template_answer(message, place, matches)

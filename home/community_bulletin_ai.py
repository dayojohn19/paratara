import base64
import json
import re
import io
from typing import Dict, Iterable, Tuple

from django.conf import settings


def _count_meaningful_words(text: str) -> int:
    if not text:
        return 0
    words = re.findall(r"[A-Za-z]{2,}", text)
    return len(words)


def _basic_spam_check(text: str) -> Tuple[bool, str]:
    """Heuristic spam check based on extracted text."""

    if not text:
        return (False, "")

    t = " ".join(text.lower().split())

    # Links / contact funnels (common in spam).
    if re.search(r"https?://|www\.|\.com\b|\.ph\b|bit\.ly\b|t\.me\b", t):
        return (True, "contains_link")
    if re.search(r"\b(whatsapp|telegram|viber|wechat|line)\b", t):
        return (True, "contains_messaging_app")
    if re.search(r"\b(loan|cash\s*loan|casino|betting|crypto|bitcoin|investment|forex)\b", t):
        return (True, "contains_spam_keywords")

    # Phone numbers (very rough): 9+ digits total.
    digits = re.findall(r"\d", t)
    if len(digits) >= 9:
        return (True, "contains_phone_number")

    # Repeated characters / junk.
    if re.search(r"(.)\1{6,}", t):
        return (True, "repeated_characters")

    return (False, "")


def analyze_bulletin_post_from_images(image_bytes_list: Iterable[bytes]) -> Dict[str, object]:
    print("Analyzing bulletin post from images...")  # Debug log
    """Analyze images to generate title/description and detect no-text or spam.

    Returns dict keys:
      - title (str)
      - description (str)
      - extracted_text (str)
      - has_words (bool)
      - is_spam (bool)
      - spam_reason (str)
    """

    images = [b for b in image_bytes_list if b]
    if not images:
        return {
            "title": "Community bulletin",
            "description": "",
            "extracted_text": "",
            "has_words": False,
            "is_spam": False,
            "spam_reason": "no_images",
        }
    print(f"Received {len(images)} images for analysis.")  # Debug log
    extracted_text = ""

    # Try local OCR first (best-effort). This is optional; if not installed, we proceed.
    print("Attempting local OCR extraction...")  # Debug log
    try:
        from PIL import Image  # type: ignore
        import pytesseract  # type: ignore

        parts = []
        for b in images[:4]:
            try:
                img = Image.open(io.BytesIO(b))
                parts.append(pytesseract.image_to_string(img) or "")
                print(f"OCR extracted text: {parts[-1][:100]}...")  # Debug log
            except Exception:
                continue
        extracted_text = "\n".join(parts).strip()
    except Exception:
        extracted_text = ""
    print(f"Total extracted text length: {len(extracted_text)}")  # Debug log
    # If OpenAI is available, use vision to extract text + generate + classify.
    try:
        from openai import OpenAI

        # api_key = getattr(settings, "OPENAI_API_KEY", None)
        # if not api_key:
        #     raise RuntimeError("OPENAI_API_KEY not configured")

        # model = getattr(settings, "OPENAI_VISION_MODEL", "gpt-4o-mini")
        # client = OpenAI(api_key=api_key)
        from django.conf import settings
        client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
        print("Using OpenAI vision for analysis...")  # Debug log
        content = [
            {
                "type": "text",
                "text": (
                    "You are analyzing community bulletin photos. "
                    "1) Extract any visible text from the images (posters, signs, flyers). "
                    "2) Decide if the content is spam (scam, ads with links/phone numbers, crypto/casino/loans, etc). "
                    "3) Generate a short title and description. "
                    "Return STRICT JSON with keys: "
                    "title, description, extracted_text, has_words, is_spam, spam_reason. "
                    "Rules: title <= 60 chars, description <= 240 chars. "
                    "Set has_words=false if there are no readable words at all. "
                    "Set is_spam=true only if you're confident."
                ),
            }
        ]

        for b in images[:4]:
            b64 = base64.b64encode(b).decode("utf-8")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})


        resp = client.chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[{"role": "user", "content": content}],
        )
        print(f"OpenAI response: {resp}")  # Debug log
        raw = (resp.choices[0].message.content or "").strip()
        data = json.loads(raw) if raw else {}

        title = (data.get("title") or "").strip() or "Community bulletin"
        description = (data.get("description") or "").strip()
        extracted_text_ai = (data.get("extracted_text") or "").strip()
        has_words = bool(data.get("has_words"))
        is_spam = bool(data.get("is_spam"))
        spam_reason = (data.get("spam_reason") or "").strip()

        extracted_text = extracted_text_ai or extracted_text

        return {
            "title": title[:160].rstrip(),
            "description": description[:2000].rstrip(),
            "extracted_text": extracted_text,
            "has_words": has_words,
            "is_spam": is_spam,
            "spam_reason": spam_reason,
        }

    except Exception:
        # Fall back to OCR-only (or empty) and local heuristics.
        has_words = _count_meaningful_words(extracted_text) >= 2
        is_spam, spam_reason = _basic_spam_check(extracted_text)

        return {
            "title": "Community bulletin",
            "description": "Photos shared by the community.",
            "extracted_text": extracted_text,
            "has_words": has_words,
            "is_spam": is_spam,
            "spam_reason": spam_reason,
        }


def generate_title_and_description_from_images(image_bytes_list: Iterable[bytes]) -> Tuple[str, str]:
    """Generate a short title and description from uploaded images.

    Uses OpenAI vision if configured and available; otherwise falls back to a simple default.
    """

    analysis = analyze_bulletin_post_from_images(image_bytes_list)
    return (str(analysis.get("title") or "Community bulletin"), str(analysis.get("description") or ""))

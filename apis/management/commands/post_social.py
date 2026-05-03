import os
from dataclasses import dataclass
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.core.management.base import BaseCommand, CommandError

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # Optional convenience: if python-dotenv isn't installed, env vars must be provided by the shell.
    pass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # Optional dependency; if missing, env vars must be set by the shell/runtime.
    pass


@dataclass(frozen=True)
class SocialConfig:
    graph_api_version: str

    facebook_page_id: Optional[str]
    facebook_page_access_token: Optional[str]

    instagram_user_id: Optional[str]
    instagram_access_token: Optional[str]


def _graph_url(version: str, path: str) -> str:
    version = version.strip("/")
    path = path.lstrip("/")
    return f"https://graph.facebook.com/{version}/{path}"


def _post_json(url: str, data: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    response = requests.post(url, data=data, timeout=timeout)
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}

    if not response.ok:
        message = payload
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = error.get("message")
        raise CommandError(f"Graph API request failed ({response.status_code}): {message}")

    if not isinstance(payload, dict):
        raise CommandError(f"Unexpected Graph API response: {payload}")

    return payload


def _post_multipart(
    url: str,
    *,
    data: Dict[str, Any],
    files: Dict[str, Any],
    timeout: int = 30,
) -> Dict[str, Any]:
    response = requests.post(url, data=data, files=files, timeout=timeout)
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}

    if not response.ok:
        message = payload
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = error.get("message")
        raise CommandError(f"Graph API request failed ({response.status_code}): {message}")

    if not isinstance(payload, dict):
        raise CommandError(f"Unexpected Graph API response: {payload}")

    return payload


def _get_json(url: str, params: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=timeout)
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text}

    if not response.ok:
        message = payload
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = error.get("message")
        raise CommandError(f"Graph API request failed ({response.status_code}): {message}")

    if not isinstance(payload, dict):
        raise CommandError(f"Unexpected Graph API response: {payload}")

    return payload


def _validate_instagram_image_url(image_url: str, *, timeout: int = 15) -> None:
    """Best-effort validation that a URL is publicly reachable and looks like a raster image.

    Instagram Graph API requires a publicly accessible image URL. Many "free image" sites
    return HTML, redirects, or block hotlinking; those will fail with "Only photo or video".
    """

    try:
        res = requests.get(image_url, stream=True, allow_redirects=True, timeout=timeout)
    except Exception as exc:
        raise CommandError(f"Image URL is not reachable: {image_url} ({exc})")

    if not res.ok:
        raise CommandError(f"Image URL returned HTTP {res.status_code}: {image_url}")

    content_type = (res.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        raise CommandError(
            "Instagram requires a public direct image URL. "
            f"This URL returned Content-Type '{content_type or 'unknown'}' (likely HTML/blocked): {image_url}"
        )

    # IG typically accepts raster formats (jpeg/png/webp). SVG often fails.
    if content_type in {"image/svg+xml", "image/svg"}:
        raise CommandError(
            f"Instagram does not reliably accept SVG. Use a PNG/JPG URL instead: {image_url}"
        )


def post_facebook(
    *,
    cfg: SocialConfig,
    message: str,
    link: Optional[str],
    image_url: Optional[str],
    image_path: Optional[str],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.facebook_page_id or not cfg.facebook_page_access_token:
        raise CommandError(
            "Facebook config missing. Provide FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN (env) "
            "or pass --facebook-page-id / --facebook-access-token."
        )

    if image_url and image_path:
        raise CommandError("Choose only one of --image-url or --image-path")

    if image_path:
        # Uploads a local image file to the Page, with an optional caption.
        if not os.path.isfile(image_path):
            raise CommandError(f"Image file not found: {image_path}")
        url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/photos")
        data: Dict[str, Any] = {
            "access_token": cfg.facebook_page_access_token,
            "caption": message,
        }
        with open(image_path, "rb") as file_handle:
            payload = _post_multipart(
                url,
                data=data,
                files={"source": file_handle},
                timeout=timeout,
            )
        return "facebook", payload

    if image_url:
        # Posts a photo to the Page by URL, with an optional caption.
        url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/photos")
        data = {
            "access_token": cfg.facebook_page_access_token,
            "url": image_url,
            "caption": message,
        }
        payload = _post_json(url, data, timeout=timeout)
        return "facebook", payload

    url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/feed")
    data = {
        "access_token": cfg.facebook_page_access_token,
        "message": message,
    }
    if link:
        data["link"] = link
    payload = _post_json(url, data, timeout=timeout)
    return "facebook", payload


def post_facebook_multi_images(
    *,
    cfg: SocialConfig,
    message: str,
    image_urls: List[str],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.facebook_page_id or not cfg.facebook_page_access_token:
        raise CommandError(
            "Facebook config missing. Provide FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN (env) "
            "or pass --facebook-page-id / --facebook-access-token."
        )

    if len(image_urls) < 2:
        raise CommandError("post_facebook_multi_images requires at least 2 image URLs")

    photo_ids: List[str] = []
    photos_url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/photos")
    for image_url in image_urls:
        image_url = image_url.strip()
        if not image_url:
            continue
        # Upload as unpublished so we can attach multiple to a single feed post.
        payload = _post_json(
            photos_url,
            {
                "access_token": cfg.facebook_page_access_token,
                "url": image_url,
                "published": "false",
            },
            timeout=timeout,
        )
        photo_id = payload.get("id")
        if not photo_id:
            raise CommandError(f"Facebook photo upload did not return an id: {payload}")
        photo_ids.append(str(photo_id))

    if not photo_ids:
        raise CommandError("No valid image URLs provided")

    feed_url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/feed")
    data: Dict[str, Any] = {
        "access_token": cfg.facebook_page_access_token,
        "message": message,
    }

    for idx, photo_id in enumerate(photo_ids):
        data[f"attached_media[{idx}]" ] = json.dumps({"media_fbid": photo_id})

    payload = _post_json(feed_url, data, timeout=timeout)
    return "facebook", payload


def _wait_for_ig_container(*, cfg: SocialConfig, creation_id: str, timeout: int) -> None:
    status_url = _graph_url(cfg.graph_api_version, str(creation_id))
    deadline = time.monotonic() + 180  # seconds
    last_status: Optional[str] = None
    while time.monotonic() < deadline:
        status_payload = _get_json(
            status_url,
            {
                "access_token": cfg.instagram_access_token,
                "fields": "status_code",
            },
            timeout=timeout,
        )
        last_status = status_payload.get("status_code")
        if last_status == "FINISHED":
            return
        if last_status == "ERROR":
            raise CommandError(f"Instagram media container processing failed: {status_payload}")
        time.sleep(3)

    raise CommandError(
        f"Instagram media container not ready (status_code={last_status}). Try again in a few seconds."
    )


def _publish_ig_with_retry(
    *,
    cfg: SocialConfig,
    creation_id: str,
    timeout: int,
    max_attempts: int = 6,
) -> Dict[str, Any]:
    publish_url = _graph_url(cfg.graph_api_version, f"{cfg.instagram_user_id}/media_publish")
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _post_json(
                publish_url,
                {
                    "access_token": cfg.instagram_access_token,
                    "creation_id": creation_id,
                },
                timeout=timeout,
            )
        except CommandError as exc:
            last_error = exc
            msg = str(exc)
            # Transient Meta error: container exists but publish isn't ready yet.
            if "Media ID is not available" in msg or "not available" in msg:
                sleep_s = min(3 * attempt, 18)
                time.sleep(sleep_s)
                continue
            raise

    raise CommandError(f"Instagram publish failed after {max_attempts} attempts: {last_error}")


def post_instagram(
    *,
    cfg: SocialConfig,
    caption: str,
    image_url: str,
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.instagram_user_id or not cfg.instagram_access_token:
        raise CommandError(
            "Instagram config missing. Provide IG_USER_ID and IG_ACCESS_TOKEN (env) "
            "or pass --instagram-user-id / --instagram-access-token."
        )

    _validate_instagram_image_url(image_url, timeout=min(15, timeout))

    # Instagram requires media container creation first, then publish.
    create_url = _graph_url(cfg.graph_api_version, f"{cfg.instagram_user_id}/media")
    create_payload = _post_json(
        create_url,
        {
            "access_token": cfg.instagram_access_token,
            "image_url": image_url,
            "caption": caption,
        },
        timeout=timeout,
    )

    creation_id = create_payload.get("id")
    if not creation_id:
        raise CommandError(f"Instagram media creation did not return an id: {create_payload}")

    # Media containers can take a moment to process.
    _wait_for_ig_container(cfg=cfg, creation_id=str(creation_id), timeout=timeout)

    publish_payload = _publish_ig_with_retry(
        cfg=cfg,
        creation_id=str(creation_id),
        timeout=timeout,
    )

    return "instagram", {"create": create_payload, "publish": publish_payload}


def post_instagram_carousel(
    *,
    cfg: SocialConfig,
    caption: str,
    image_urls: List[str],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.instagram_user_id or not cfg.instagram_access_token:
        raise CommandError(
            "Instagram config missing. Provide IG_USER_ID and IG_ACCESS_TOKEN (env) "
            "or pass --instagram-user-id / --instagram-access-token."
        )

    if len(image_urls) < 2:
        raise CommandError("Instagram carousel requires at least 2 image URLs")

    # 1) Create item containers (and wait for each to finish processing)
    child_ids: List[str] = []
    create_url = _graph_url(cfg.graph_api_version, f"{cfg.instagram_user_id}/media")
    for image_url in image_urls:
        image_url = image_url.strip()
        if not image_url:
            continue
        _validate_instagram_image_url(image_url, timeout=min(15, timeout))
        payload = _post_json(
            create_url,
            {
                "access_token": cfg.instagram_access_token,
                "image_url": image_url,
                "is_carousel_item": "true",
            },
            timeout=timeout,
        )
        cid = payload.get("id")
        if not cid:
            raise CommandError(f"Instagram carousel item creation did not return an id: {payload}")
        cid_str = str(cid)
        _wait_for_ig_container(cfg=cfg, creation_id=cid_str, timeout=timeout)
        child_ids.append(cid_str)

    if len(child_ids) < 2:
        raise CommandError("Instagram carousel requires at least 2 valid image URLs")

    # 2) Create carousel container
    carousel_payload = _post_json(
        create_url,
        {
            "access_token": cfg.instagram_access_token,
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
        timeout=timeout,
    )
    carousel_id = carousel_payload.get("id")
    if not carousel_id:
        raise CommandError(f"Instagram carousel creation did not return an id: {carousel_payload}")

    _wait_for_ig_container(cfg=cfg, creation_id=str(carousel_id), timeout=timeout)

    # 3) Publish (with retry)
    publish_payload = _publish_ig_with_retry(
        cfg=cfg,
        creation_id=str(carousel_id),
        timeout=timeout,
    )

    return "instagram", {"children": child_ids, "carousel": carousel_payload, "publish": publish_payload}


def post_instagram_video(
    *,
    cfg: SocialConfig,
    caption: str,
    video_url: str,
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.instagram_user_id or not cfg.instagram_access_token:
        raise CommandError(
            "Instagram config missing. Provide IG_USER_ID and IG_ACCESS_TOKEN (env) "
            "or pass --instagram-user-id / --instagram-access-token."
        )

    create_url = _graph_url(cfg.graph_api_version, f"{cfg.instagram_user_id}/media")

    # Try REELS first; some accounts prefer it. Fall back to VIDEO if needed.
    last_error: Optional[Exception] = None
    for media_type in ("REELS", "VIDEO"):
        try:
            create_payload = _post_json(
                create_url,
                {
                    "access_token": cfg.instagram_access_token,
                    "video_url": video_url,
                    "caption": caption,
                    "media_type": media_type,
                },
                timeout=timeout,
            )
            creation_id = create_payload.get("id")
            if not creation_id:
                raise CommandError(f"Instagram video creation did not return an id: {create_payload}")

            publish_url = _graph_url(cfg.graph_api_version, f"{cfg.instagram_user_id}/media_publish")
            publish_payload = _post_json(
                publish_url,
                {
                    "access_token": cfg.instagram_access_token,
                    "creation_id": creation_id,
                },
                timeout=timeout,
            )

            return "instagram", {"create": create_payload, "publish": publish_payload}
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise CommandError("Instagram video publishing failed")


def post_facebook_multi_images(
    *,
    cfg: SocialConfig,
    message: str,
    image_urls: list[str],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    if not cfg.facebook_page_id or not cfg.facebook_page_access_token:
        raise CommandError(
            "Facebook config missing. Provide FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN (env) "
            "or pass --facebook-page-id / --facebook-access-token."
        )
    if len(image_urls) < 2:
        raise CommandError("Facebook multi-image post requires at least 2 image URLs")

    photos_url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/photos")
    media_fbid_list: list[str] = []

    for image_url in image_urls:
        payload = _post_json(
            photos_url,
            {
                "access_token": cfg.facebook_page_access_token,
                "url": image_url,
                "published": "false",
            },
            timeout=timeout,
        )
        media_fbid = payload.get("id")
        if not media_fbid:
            raise CommandError(f"Facebook photo upload did not return an id: {payload}")
        media_fbid_list.append(str(media_fbid))

    feed_url = _graph_url(cfg.graph_api_version, f"{cfg.facebook_page_id}/feed")
    data: Dict[str, Any] = {
        "access_token": cfg.facebook_page_access_token,
        "message": message,
    }
    for idx, media_fbid in enumerate(media_fbid_list):
        data[f"attached_media[{idx}]" ] = json.dumps({"media_fbid": media_fbid})

    feed_payload = _post_json(feed_url, data, timeout=timeout)
    return "facebook", {"media": media_fbid_list, "post": feed_payload}


class Command(BaseCommand):
    help = "Post to Facebook Page and/or Instagram (Meta Graph API)."

    def add_arguments(self, parser):
        parser.add_argument("--message", required=True, help="Text message/caption")
        parser.add_argument("--image-url", help="Public image URL (required for Instagram)")
        parser.add_argument("--image-path", help="Local image path (Facebook only)")
        parser.add_argument("--link", help="Link to attach (Facebook feed posts only)")

        parser.add_argument(
            "--facebook-only",
            action="store_true",
            help="Only post to Facebook (ignore Instagram)",
        )
        parser.add_argument(
            "--instagram-only",
            action="store_true",
            help="Only post to Instagram (ignore Facebook)",
        )

        parser.add_argument("--graph-api-version", default=os.getenv("GRAPH_API_VERSION", "v19.0"))
        parser.add_argument("--timeout", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true", help="Validate args; do not post")
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify token/IDs via Graph API (no posting)",
        )

        parser.add_argument("--facebook-page-id", default=os.getenv("FB_PAGE_ID"))
        parser.add_argument("--facebook-access-token", default=os.getenv("FB_PAGE_ACCESS_TOKEN"))

        parser.add_argument("--instagram-user-id", default=os.getenv("IG_USER_ID"))
        parser.add_argument("--instagram-access-token", default=os.getenv("IG_ACCESS_TOKEN"))

    def handle(self, *args, **options):
        if options["facebook_only"] and options["instagram_only"]:
            raise CommandError("Choose only one of --facebook-only / --instagram-only")

        message: str = options["message"].strip()
        if not message:
            raise CommandError("--message cannot be empty")

        image_url: Optional[str] = options.get("image_url")
        if image_url:
            image_url = image_url.strip()

        image_path: Optional[str] = options.get("image_path")
        if image_path:
            image_path = image_path.strip()

        link: Optional[str] = options.get("link")
        if link:
            link = link.strip()

        cfg = SocialConfig(
            graph_api_version=options["graph_api_version"],
            facebook_page_id=options.get("facebook_page_id"),
            facebook_page_access_token=options.get("facebook_access_token"),
            instagram_user_id=options.get("instagram_user_id"),
            instagram_access_token=options.get("instagram_access_token"),
        )

        def _validate_token(name: str, token: Optional[str]) -> None:
            if not token:
                return
            if any(ch.isspace() for ch in token):
                raise CommandError(
                    f"{name} contains whitespace/newlines. In .env it must be a single line with no quotes."
                )

        _validate_token("FB_PAGE_ACCESS_TOKEN", cfg.facebook_page_access_token)
        _validate_token("IG_ACCESS_TOKEN", cfg.instagram_access_token)

        # Common pitfall: using an Instagram Basic Display token (often starts with 'IG')
        # instead of a Facebook Graph API user/page token (typically starts with 'EA').
        if cfg.instagram_access_token and cfg.instagram_access_token.startswith("IG"):
            raise CommandError(
                "IG_ACCESS_TOKEN looks like an Instagram Basic Display token. "
                "For Instagram Graph API publishing, use a Facebook Graph API access token (usually starts with 'EA') "
                "that has instagram permissions (instagram_basic, instagram_content_publish, pages_show_list, etc.)."
            )

        if options.get("verify"):
            self._verify(cfg=cfg, timeout=options["timeout"])
            return

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: no requests were made."))
            self.stdout.write(f"Graph API version: {cfg.graph_api_version}")
            self.stdout.write(f"Facebook enabled: {bool(cfg.facebook_page_id and cfg.facebook_page_access_token)}")
            self.stdout.write(f"Instagram enabled: {bool(cfg.instagram_user_id and cfg.instagram_access_token)}")
            if options["instagram_only"] or (not options["facebook_only"]):
                if not image_url:
                    self.stdout.write(self.style.WARNING("Note: Instagram requires --image-url"))
            return None

        do_facebook = not options["instagram_only"]
        do_instagram = not options["facebook_only"]

        if do_facebook:
            channel, payload = post_facebook(
                cfg=cfg,
                message=message,
                link=link,
                image_url=image_url,
                image_path=image_path,
                timeout=options["timeout"],
            )
            self.stdout.write(self.style.SUCCESS(f"Facebook OK: {json.dumps(payload, ensure_ascii=False)}"))

        if do_instagram:
            if not image_url:
                raise CommandError("Instagram posting requires --image-url")
            if image_path:
                raise CommandError("Instagram does not support --image-path; use a public --image-url")
            channel, payload = post_instagram(
                cfg=cfg,
                caption=message,
                image_url=image_url,
                timeout=options["timeout"],
            )
            self.stdout.write(self.style.SUCCESS(f"Instagram OK: {json.dumps(payload, ensure_ascii=False)}"))

        return None

    def _verify(self, *, cfg: SocialConfig, timeout: int) -> None:
        self.stdout.write(self.style.WARNING("VERIFY: making read-only Graph API requests."))
        self.stdout.write(f"Graph API version: {cfg.graph_api_version}")

        # 1) Facebook token check
        if cfg.facebook_page_access_token:
            me = _get_json(
                _graph_url(cfg.graph_api_version, "me"),
                {"access_token": cfg.facebook_page_access_token},
                timeout=timeout,
            )
            self.stdout.write(self.style.SUCCESS(f"Facebook token OK (me): {me}"))
            if cfg.facebook_page_id and str(me.get("id")) == str(cfg.facebook_page_id):
                self.stdout.write(
                    self.style.WARNING(
                        "Note: FB_PAGE_ACCESS_TOKEN appears to be a Page token (me == FB_PAGE_ID)."
                    )
                )
        else:
            self.stdout.write(self.style.WARNING("Facebook token not set (FB_PAGE_ACCESS_TOKEN)."))

        # 2) Page -> IG linkage
        # Use IG token (user token) for this check if available; otherwise fall back to FB token.
        token_for_page = cfg.instagram_access_token or cfg.facebook_page_access_token

        if cfg.facebook_page_id and token_for_page:
            page = _get_json(
                _graph_url(cfg.graph_api_version, str(cfg.facebook_page_id)),
                {
                    "access_token": token_for_page,
                    "fields": "name,instagram_business_account",
                },
                timeout=timeout,
            )
            self.stdout.write(self.style.SUCCESS(f"Page fields: {page}"))

            if "instagram_business_account" not in page:
                self.stdout.write(
                    self.style.WARNING(
                        "No instagram_business_account returned for this Page. "
                        "This usually means the Page is not linked to an Instagram Business/Creator account, "
                        "or your token lacks permissions (instagram_basic + pages_show_list/pages_read_engagement)."
                    )
                )
        else:
            self.stdout.write(self.style.WARNING("FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN not fully set; cannot check Page linkage."))

        # 3) IG user id + token check
        if cfg.instagram_user_id and cfg.instagram_access_token:
            ig = _get_json(
                _graph_url(cfg.graph_api_version, str(cfg.instagram_user_id)),
                {
                    "access_token": cfg.instagram_access_token,
                    # Keep fields conservative across Graph API versions.
                    "fields": "username,name,media_count",
                },
                timeout=timeout,
            )
            self.stdout.write(self.style.SUCCESS(f"Instagram user OK: {ig}"))
        else:
            self.stdout.write(self.style.WARNING("IG_USER_ID/IG_ACCESS_TOKEN not fully set; cannot check Instagram user."))

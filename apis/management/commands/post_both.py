import os
from typing import Any, Dict, Optional

import requests
from django.core.management.base import BaseCommand, CommandError

from .post_social import (
    SocialConfig,
    post_facebook,
    post_facebook_multi_images,
    post_instagram,
    post_instagram_carousel,
)


def _get_imgbb_api_key() -> str:
        """Return ImgBB API key from env, tolerating common .env formatting mistakes.

        Supports IMGBB_API_KEY or API_IMBB_KEY and strips inline comments like:
            IMGBB_API_KEY = abc123  # comment
        """

        raw = os.getenv("IMGBB_API_KEY") or os.getenv("API_IMBB_KEY") or ""
        raw = raw.strip().strip('"').strip("'")
        if not raw:
                return ""
        # Drop inline comments and whitespace
        raw = raw.split("#", 1)[0].strip()
        # If someone left extra tokens, keep only the first token
        raw = raw.split()[0].strip()
        return raw


def upload_to_imgbb(*, image_path: str, api_key: str, timeout: int = 60) -> str:
    if not os.path.isfile(image_path):
        raise CommandError(f"Image file not found: {image_path}")

    if not api_key:
        raise CommandError(
            "Missing IMGBB_API_KEY. Set it in your environment/.env to upload local images for Instagram."
        )

    with open(image_path, "rb") as file_handle:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key},
            files={"image": file_handle},
            timeout=timeout,
        )

    try:
        payload: Dict[str, Any] = response.json()
    except Exception:
        payload = {"raw": response.text}

    if not response.ok or not payload.get("success"):
        raise CommandError(f"ImgBB upload failed ({response.status_code}): {payload}")

    url = payload.get("data", {}).get("url")
    if not url:
        raise CommandError(f"ImgBB upload did not return a url: {payload}")

    return url


def upload_url_to_imgbb(*, image_url: str, api_key: str, timeout: int = 60) -> str:
    """Rehost a remote image URL on ImgBB.

    Useful when the original host blocks hotlinking (Instagram servers won't be able to fetch it).
    """
    if not api_key:
        raise CommandError(
            "Missing IMGBB_API_KEY. Set it in your environment/.env to rehost images for Instagram."
        )

    try:
        res = requests.get(
            image_url,
            stream=True,
            allow_redirects=True,
            timeout=min(30, timeout),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/*,*/*;q=0.8",
            },
        )
    except Exception as exc:
        raise CommandError(f"Failed to download image URL for rehost: {image_url} ({exc})")

    if not res.ok:
        raise CommandError(f"Failed to download image URL (HTTP {res.status_code}): {image_url}")

    content_type = (res.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not content_type.startswith("image/"):
        raise CommandError(
            f"URL did not return an image (Content-Type={content_type or 'unknown'}): {image_url}"
        )

    content = res.content
    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": api_key},
        files={"image": ("image", content)},
        timeout=timeout,
    )

    try:
        payload: Dict[str, Any] = response.json()
    except Exception:
        payload = {"raw": response.text}

    if not response.ok or not payload.get("success"):
        raise CommandError(f"ImgBB rehost failed ({response.status_code}): {payload}")

    url = payload.get("data", {}).get("url")
    if not url:
        raise CommandError(f"ImgBB rehost did not return a url: {payload}")

    return url


class Command(BaseCommand):
    help = "Simple: post the same message+image to Facebook Page + Instagram."

    def add_arguments(self, parser):
        parser.add_argument("message", help="Caption/text to post")
        parser.add_argument(
            "image",
            nargs="?",
            help="(optional) Public image URL OR local file path. Prefer using --image-url for multiple images.",
        )

        parser.add_argument(
            "--image-url",
            action="append",
            dest="image_urls",
            help="Public image URL. Repeat to create a multi-image post (FB album / IG carousel).",
        )

        parser.add_argument(
            "--rehost-ig",
            action="store_true",
            help="Re-upload provided image URLs to ImgBB before Instagram posting (fixes hotlink-blocked hosts).",
        )

        parser.add_argument("--graph-api-version", default=os.getenv("GRAPH_API_VERSION", "v19.0"))
        parser.add_argument("--timeout", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true", help="Validate; do not post")

        # Allow overriding env vars if needed
        parser.add_argument("--facebook-page-id", default=os.getenv("FB_PAGE_ID"))
        parser.add_argument("--facebook-access-token", default=os.getenv("FB_PAGE_ACCESS_TOKEN"))
        parser.add_argument("--instagram-user-id", default=os.getenv("IG_USER_ID"))
        parser.add_argument("--instagram-access-token", default=os.getenv("IG_ACCESS_TOKEN"))

    def handle(self, *args, **options):
        message: str = (options["message"] or "").strip()
        if not message:
            raise CommandError("message cannot be empty")

        image_urls_opt = options.get("image_urls") or []
        video_url: Optional[str] = None

        image_input_raw: Optional[str] = options.get("image")
        image_input = (image_input_raw or "").strip() if image_input_raw else None

        if not image_input and not image_urls_opt:
            raise CommandError("Provide an image (image or --image-url)")

        cfg = SocialConfig(
            graph_api_version=options["graph_api_version"],
            facebook_page_id=options.get("facebook_page_id"),
            facebook_page_access_token=options.get("facebook_access_token"),
            instagram_user_id=options.get("instagram_user_id"),
            instagram_access_token=options.get("instagram_access_token"),
        )

        # Build image mode
        image_urls: list[str] = []
        image_url_single: Optional[str] = None
        image_path_single: Optional[str] = None
        ig_image_url_single: Optional[str] = None
        rehost_ig: bool = bool(options.get("rehost_ig"))

        if image_urls_opt:
            image_urls = [u.strip() for u in image_urls_opt if u and u.strip()]
        elif image_input:
            is_url = image_input.lower().startswith("http://") or image_input.lower().startswith("https://")
            image_url_single = image_input if is_url else None
            image_path_single = None if is_url else image_input

        if image_path_single and not image_url_single:
            # Instagram requires a public URL; if user provides a file path, upload it.
            ig_image_url_single = upload_to_imgbb(
                image_path=image_path_single,
                api_key=_get_imgbb_api_key(),
                timeout=max(60, int(options["timeout"]) or 60),
            )
        else:
            ig_image_url_single = image_url_single

        # Optional: rehost remote URLs for Instagram to avoid hotlink blocks.
        if rehost_ig:
            api_key = _get_imgbb_api_key()
            if len(image_urls) >= 2:
                image_urls = [
                    upload_url_to_imgbb(image_url=u, api_key=api_key, timeout=max(60, int(options["timeout"]) or 60))
                    for u in image_urls
                ]
            elif len(image_urls) == 1:
                ig_image_url_single = upload_url_to_imgbb(
                    image_url=image_urls[0],
                    api_key=api_key,
                    timeout=max(60, int(options["timeout"]) or 60),
                )
            elif ig_image_url_single:
                ig_image_url_single = upload_url_to_imgbb(
                    image_url=ig_image_url_single,
                    api_key=api_key,
                    timeout=max(60, int(options["timeout"]) or 60),
                )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN: no requests were made."))
            self.stdout.write(f"Graph API version: {cfg.graph_api_version}")
            if image_urls:
                self.stdout.write(f"Mode: multi-image ({len(image_urls)})")
            else:
                self.stdout.write(f"Mode: single-image ({'url' if image_url_single else 'file'})")
            self.stdout.write(f"Instagram ready: {bool(image_urls or ig_image_url_single)}")
            if rehost_ig:
                self.stdout.write("Instagram rehost: enabled (ImgBB)")
            return None

        # Facebook
        if len(image_urls) >= 2:
            _, fb_payload = post_facebook_multi_images(
                cfg=cfg,
                message=message,
                image_urls=image_urls,
                timeout=options["timeout"],
            )
        else:
            _, fb_payload = post_facebook(
                cfg=cfg,
                message=message,
                link=None,
                image_url=image_urls[0] if image_urls else image_url_single,
                image_path=image_path_single,
                timeout=options["timeout"],
            )
        self.stdout.write(self.style.SUCCESS(f"Facebook OK: {fb_payload}"))

        # Instagram
        try:
            if len(image_urls) >= 2:
                _, ig_payload = post_instagram_carousel(
                    cfg=cfg,
                    caption=message,
                    image_urls=image_urls,
                    timeout=options["timeout"],
                )
            else:
                if not ig_image_url_single:
                    # Support a single --image-url by treating it as the single IG image URL.
                    if len(image_urls) == 1:
                        ig_image_url_single = image_urls[0]
                    else:
                        raise CommandError("Instagram requires a public image URL (or a local file + IMGBB_API_KEY).")
                _, ig_payload = post_instagram(
                    cfg=cfg,
                    caption=message,
                    image_url=ig_image_url_single,
                    timeout=options["timeout"],
                )
        except CommandError as exc:
            msg = str(exc)
            # Common transient/host issue: IG can't fetch the source URL (hotlink blocked / HTML page).
            # If we have ImgBB key, rehost URLs and retry once.
            api_key = _get_imgbb_api_key()
            if "Only photo or video can be accepted" in msg and api_key:
                self.stdout.write(self.style.WARNING("Instagram rejected media URL; rehosting to ImgBB and retrying once..."))

                if len(image_urls) >= 2:
                    rehosted = [
                        upload_url_to_imgbb(
                            image_url=u,
                            api_key=api_key,
                            timeout=max(60, int(options["timeout"]) or 60),
                        )
                        for u in image_urls
                    ]
                    self.stdout.write(self.style.WARNING(f"Rehosted {len(rehosted)} images to ImgBB for Instagram."))
                    _, ig_payload = post_instagram_carousel(
                        cfg=cfg,
                        caption=message,
                        image_urls=rehosted,
                        timeout=options["timeout"],
                    )
                else:
                    if not ig_image_url_single:
                        raise
                    rehosted = upload_url_to_imgbb(
                        image_url=ig_image_url_single,
                        api_key=api_key,
                        timeout=max(60, int(options["timeout"]) or 60),
                    )
                    self.stdout.write(self.style.WARNING("Rehosted 1 image to ImgBB for Instagram."))
                    _, ig_payload = post_instagram(
                        cfg=cfg,
                        caption=message,
                        image_url=rehosted,
                        timeout=options["timeout"],
                    )
            else:
                raise
        self.stdout.write(self.style.SUCCESS(f"Instagram OK: {ig_payload}"))

        return None

import os
from typing import Any, Dict, List, Optional

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime


def _extract_media_urls(post: Dict[str, Any]) -> List[str]:
    urls: List[str] = []

    attachments = (post.get("attachments") or {}).get("data") or []
    for att in attachments:
        media = att.get("media") or {}
        img = (media.get("image") or {}).get("src")
        if img:
            urls.append(img)

        # Albums / multi images
        sub = (att.get("subattachments") or {}).get("data") or []
        for subatt in sub:
            submedia = subatt.get("media") or {}
            subimg = (submedia.get("image") or {}).get("src")
            if subimg:
                urls.append(subimg)

    # De-dupe while keeping order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


class Command(BaseCommand):
    help = "Sync latest Facebook Page posts into the website database (home.FacebookPagePost)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--page-id", default=os.getenv("FB_PAGE_ID"))
        parser.add_argument("--access-token", default=os.getenv("FB_PAGE_ACCESS_TOKEN"))
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        page_id: Optional[str] = options.get("page_id")
        access_token: Optional[str] = options.get("access_token")
        limit: int = int(options.get("limit") or 25)

        if not page_id:
            raise CommandError("Missing FB_PAGE_ID (or pass --page-id)")
        if not access_token:
            raise CommandError("Missing FB_PAGE_ACCESS_TOKEN (or pass --access-token)")

        url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
        params = {
            "access_token": access_token,
            "limit": limit,
            "fields": "id,message,created_time,permalink_url,attachments{media,subattachments}",
        }

        res = requests.get(url, params=params, timeout=30)
        try:
            payload: Dict[str, Any] = res.json()
        except Exception:
            payload = {"raw": res.text}

        if not res.ok:
            raise CommandError(f"Graph API request failed ({res.status_code}): {payload}")

        data = payload.get("data") or []
        if not isinstance(data, list):
            raise CommandError(f"Unexpected Graph response: {payload}")

        try:
            from home.models import FacebookPagePost
        except Exception as exc:
            raise CommandError(f"Could not import FacebookPagePost: {exc}")

        created_count = 0
        updated_count = 0

        for post in data:
            fb_post_id = (post.get("id") or "").strip()
            if not fb_post_id:
                continue

            message = (post.get("message") or "").strip()
            permalink_url = (post.get("permalink_url") or "").strip()
            created_time_raw = post.get("created_time")
            created_time = parse_datetime(created_time_raw) if created_time_raw else None
            media_urls = _extract_media_urls(post)

            if options.get("dry_run"):
                self.stdout.write(f"DRY: {fb_post_id} ({len(media_urls)} media) {permalink_url}")
                continue

            obj, created = FacebookPagePost.objects.update_or_create(
                fb_post_id=fb_post_id,
                defaults={
                    "message": message,
                    "permalink_url": permalink_url,
                    "created_time": created_time,
                    "media_json": {"media_urls": media_urls},
                    "raw_json": post,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"FB sync complete: {created_count} created, {updated_count} updated"))

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from django.core.management import call_command
import os
import logging


logger = logging.getLogger(__name__)


@receiver(post_save, sender='home.SiargaoEventSchedule')
def wire_event_to_package(sender, instance, **kwargs):
    pkg = getattr(instance, 'package', None)
    if not pkg:
        return
    try:
        pkg.siargaoevents.add(instance)
    except Exception:
        # If migrations not applied yet or relation missing, fail silently.
        return


@receiver(post_save, sender='home.SiargaoEventRegistrant')
def mirror_siargao_registration_to_package(sender, instance, created, **kwargs):
    event_obj = getattr(instance, 'event', None)
    if not event_obj:
        return

    pkg = getattr(event_obj, 'package', None)
    if not pkg:
        return

    # Determine the resort for this package (required by resorts.EventRegistration)
    resort = None
    try:
        resort = getattr(getattr(pkg, 'packageName', None), 'ItemOfResort', None)
    except Exception:
        resort = None
    if resort is None:
        return

    try:
        from resorts.models import EventRegistration
    except Exception:
        return

    # Update-or-create by (event/package, email) (case-insensitive match)
    existing = EventRegistration.objects.filter(event=pkg, email__iexact=instance.email).first()
    if existing:
        existing.full_name = instance.full_name
        existing.email = instance.email
        existing.phone = instance.phone
        existing.pax = instance.pax
        existing.notes = instance.notes
        existing.resort = resort
        existing.save()
        return

    try:
        EventRegistration.objects.create(
            event=pkg,
            resort=resort,
            full_name=instance.full_name,
            email=instance.email,
            phone=instance.phone,
            pax=instance.pax,
            notes=instance.notes,
        )
    except Exception:
        # If unique constraint race or similar, ignore.
        return


def _build_bulletin_caption(*, title: str, description: str) -> str:
    title_clean = (title or '').strip()
    desc_clean = (description or '').strip()

    if title_clean and desc_clean:
        return f"{title_clean}\n\n{desc_clean}".strip()
    if title_clean:
        return title_clean
    if desc_clean:
        return desc_clean
    return "Community bulletin"

 
def _publish_bulletin_post_to_social(*, post_id: int) -> None:
    try:
        from home.models import CommunityBulletinPost
    except Exception:
        return

    # Claim this post so we only attempt posting once at a time.
    try:
        with transaction.atomic():
            post = CommunityBulletinPost.objects.select_for_update().get(pk=post_id)
            if post.social_posted_at:
                return
            if post.social_posting:
                return
            post.social_posting = True
            post.save(update_fields=["social_posting"])
    except Exception:
        return

    try:
        # Gather image URLs (in creation order)
        image_urls = list(
            post.images.exclude(image_url__isnull=True)
            .exclude(image_url="")
            .values_list("image_url", flat=True)
        )

        if not image_urls:
            with transaction.atomic():
                CommunityBulletinPost.objects.filter(pk=post_id).update(social_posting=False)
            return

        caption = _build_bulletin_caption(title=post.ai_title, description=post.ai_description)
        args = []
        for url in image_urls:
            args.extend(["--image-url", url])

        # If we have an ImgBB key, prefer rehosting for Instagram reliability.
        has_imgbb_key = bool((os.getenv("IMGBB_API_KEY") or os.getenv("API_IMBB_KEY") or "").strip())
        if has_imgbb_key:
            args.append("--rehost-ig")

        call_command("post_both", caption, *args)

        with transaction.atomic():
            CommunityBulletinPost.objects.filter(pk=post_id).update(
                social_posting=False,
                social_posted_at=timezone.now(),
                social_last_error="",
            )
    except Exception as exc:
        # Don't get stuck in posting=True
        try:
            with transaction.atomic():
                CommunityBulletinPost.objects.filter(pk=post_id).update(social_posting=False)
        except Exception:
            pass
        try:
            CommunityBulletinPost.objects.filter(pk=post_id).update(social_last_error=str(exc)[:2000])
        except Exception:
            pass
        logger.exception("Community bulletin social post failed (post_id=%s)", post_id)
        return


@receiver(post_save, sender='home.CommunityBulletinImage')
def auto_post_bulletin_to_social(sender, instance, created, **kwargs):
    if not created:
        return
    post = getattr(instance, 'post', None)
    if not post:
        return

    # Run after commit so the image URL is visible to the posting command.
    transaction.on_commit(lambda: _publish_bulletin_post_to_social(post_id=post.id))

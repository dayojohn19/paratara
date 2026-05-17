from django.db.models.signals import m2m_changed, post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import resortItem, resortPackages, Packages
from home.models import SiargaoEventSchedule
from django.conf import settings
from openai import OpenAI
import logging
import json
from datetime import datetime
import cloudinary
import cloudinary.uploader

from .date_patterns import expand_every_weekday_in_month

logger = logging.getLogger(__name__)
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.GROK_API_KEY, base_url='https://api.x.ai/v1')
    return _openai_client


def extract_date_with_openai(title, description, location):
    """
    Use OpenAI to extract date information from event title and description.
    Handles multiple dates, date ranges, and recurring patterns.
    For recurring events, returns the specific dates to create individual events.
    Returns dict with dateN, monthN, yearN, exactDate, recurring, is_multiple_dates, dates_list
    """
    try:
        # Fast-path: handle simple recurring patterns deterministically.
        combined_text = f"{title}\n{description}\n{location}"
        deterministic = expand_every_weekday_in_month(combined_text)
        if deterministic:
            print(f"📅 Deterministic date expansion: {deterministic}")
            return deterministic

        current_year = datetime.now().year
        current_month = datetime.now().month
        
        prompt = f"""Extract the event date from this information:
    Title: {title}
    Description: {description}
    Location: {location}

    Today's date is {datetime.now().strftime('%B %d, %Y')}.

    Analyze the text and determine all specific dates for this event. If recurring, list EACH specific date.

    Return ONLY a JSON object with these fields:
    {{
    "is_recurring": <true if event repeats on a schedule, false otherwise>,
    "is_multiple_dates": <true if there are multiple specific dates, false otherwise>,
    "recurring_pattern": "<describe the recurring pattern>",
    "specific_dates": [
        {{
        "dateN": <day number>,
        "monthN": <month number 1-12>,
        "yearN": <year>,
        "date_string": "<readable date like 'Dec 7, 2025'>"
        }}
    ]
    }}

    IMPORTANT: For recurring events, calculate and list ALL specific dates. Examples:

    - "Every Sunday in December" → List all 4-5 Sundays in December {current_year}
    - "Every Wednesday" → List next 4 Wednesdays from today
    - "First Monday of December" → List the specific date of first Monday
    - "December 25, 26, 27" → List all three dates
    - "Every weekend in January" → List all Saturdays and Sundays in January

    Example output for "Every Sunday in December":
    {{
    "is_recurring": true,
    "is_multiple_dates": true,
    "recurring_pattern": "Every Sunday in December",
    "specific_dates": [
        {{"dateN": 7, "monthN": 12, "yearN": 2025, "date_string": "Dec 7, 2025"}},
        {{"dateN": 14, "monthN": 12, "yearN": 2025, "date_string": "Dec 14, 2025"}},
        {{"dateN": 21, "monthN": 12, "yearN": 2025, "date_string": "Dec 21, 2025"}},
        {{"dateN": 28, "monthN": 12, "yearN": 2025, "date_string": "Dec 28, 2025"}}
    ]
    }}"""

        response = _get_openai_client().chat.completions.create(
            model=settings.GROK_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a date extraction assistant. Calculate all specific dates for recurring events. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        
        date_info = json.loads(result)
        print(f"📅 OpenAI extracted date: {date_info}")

        # If the recurring pattern looks like "Every <weekday> in <month> <year>",
        # compute dates using Python's calendar (don't trust LLM day math).
        pattern = date_info.get("recurring_pattern") or ""
        deterministic_from_pattern = expand_every_weekday_in_month(pattern)
        if deterministic_from_pattern:
            date_info["is_recurring"] = True
            date_info["is_multiple_dates"] = deterministic_from_pattern.get("is_multiple_dates", True)
            date_info["specific_dates"] = deterministic_from_pattern.get("specific_dates", [])
            # Keep a normalized recurring_pattern string.
            date_info["recurring_pattern"] = deterministic_from_pattern.get("recurring_pattern", pattern)
            print(f"📅 Overriding OpenAI dates via calendar math: {date_info}")
        
        # Ensure specific_dates exists and is not empty
        if not date_info.get("specific_dates"):
            now = datetime.now()
            date_info["specific_dates"] = [{
                "dateN": now.day,
                "monthN": now.month,
                "yearN": now.year,
                "date_string": now.strftime("%b %d, %Y")
            }]
        
        return date_info
        
    except Exception as e:
        print(f"⚠️ OpenAI date extraction failed: {e}")
        import traceback
        traceback.print_exc()
        # Return default values
        now = datetime.now()
        return {
            "is_recurring": False,
            "is_multiple_dates": False,
            "recurring_pattern": "",
            "specific_dates": [{
                "dateN": now.day,
                "monthN": now.month,
                "yearN": now.year,
                "date_string": now.strftime("%b %d, %Y")
            }]
        }


@receiver(m2m_changed, sender=resortItem.resortTour.through)
def create_event_on_resort_tour_add(sender, instance, action, pk_set, **kwargs):
    """
    Automatically create SiargaoEventSchedule when packages are added to resortTour.
    Creates an event for EACH subpackage using the subpackage title.
    Also adds events to the place's eventSchedules.
    Uses OpenAI to extract date information.
    """
    print(f"🔔 Signal triggered! Action: {action}, Instance: {instance}, pk_set: {pk_set}")
    
    if action == "post_add":
        # instance is the resortItem
        # pk_set contains the IDs of resortPackages being added
        
        if not pk_set:
            print("⚠️ No packages in pk_set")
            return
            
        for package_id in pk_set:
            try:
                package = resortPackages.objects.get(id=package_id)
                print(f"📦 Processing package: {package.PackageTitle}")
                
                # Get the place from the resort
                place = instance.place
                if not place:
                    print(f"⚠️ Resort {instance.name} has no place assigned")
                    continue
                
                print(f"📍 Place found: {place.placename}")
                
                # Get subpackages - create an event for EACH subpackage
                subpackages = package.subPackages.all()
                
                if not subpackages.exists():
                    print(f"⏭️ Skipping package '{package.PackageTitle}' because it has no subpackages (no event needed).")
                    continue

                print(f"📋 Found {subpackages.count()} subpackages. Creating an event for each.")
                subpackages_to_process = [
                    {
                        "title": sub.title,
                        "description": sub.description,
                        "information": sub.information,
                        "price": sub.price,
                        "images": [img.urlField for img in sub.images.all()]
                    }
                    for sub in subpackages
                ]
                
                for sub_data in subpackages_to_process:
                    try:
                        cost = str(sub_data["price"]) if sub_data["price"] else "Free"

                        # Build full description
                        full_description = f"{sub_data['title']}. {sub_data['description']} {sub_data['information']} {instance.description}".strip()

                        # Extract date using OpenAI
                        print(f"🤖 Calling OpenAI to extract date for '{sub_data['title']}'...")
                        date_info = extract_date_with_openai(
                            title=sub_data['title'],
                            description=full_description,
                            location=f"{instance.address or place.placename}"
                        )

                        # Get image URL (first subpackage image, or resort header)
                        image_url = sub_data["images"][0] if sub_data["images"] else instance.headerImage or ""

                        # Prepare other details
                        other_details = ""
                        if date_info.get("recurring_pattern"):
                            other_details = f"Recurring: {date_info['recurring_pattern']}"

                        specific_dates = date_info.get("specific_dates", [])
                        if not specific_dates:
                            specific_dates = [{
                                "dateN": datetime.now().day,
                                "monthN": datetime.now().month,
                                "yearN": datetime.now().year,
                                "date_string": datetime.now().strftime("%b %d, %Y")
                            }]

                        created_count = 0
                        for d in specific_dates:
                            dn = d.get("dateN")
                            mn = d.get("monthN")
                            yn = d.get("yearN")
                            ds = d.get("date_string", "")

                            # Deduplicate: avoid creating same event multiple times for same place/title/date
                            exists = SiargaoEventSchedule.objects.filter(
                                place=place,
                                scheduleTitle=sub_data['title'],
                                dateN=dn,
                                monthN=mn,
                                yearN=yn
                            ).exists()
                            if exists:
                                print(f"↪️ Skipping duplicate event for {sub_data['title']} on {mn}/{dn}/{yn}")
                                continue

                            event = SiargaoEventSchedule.objects.create(
                                package=Packages.objects.filter(id=sub_data.get('id')).first(),
                                place=place,
                                scheduleTitle=sub_data['title'],
                                # Show resort name as event location in m2m-created events
                                schedulePlace=f"https://www.google.com/maps/dir/?api=1&destination={instance.latitude},{instance.longitude}",
                                posterName=instance.RealName or instance.name,
                                posterURL=f"/resorts/{instance.slug or instance.name}/",
                                scheduleImageURL=image_url,
                                backgroundURL=image_url,
                                thumbnailURL=image_url,
                                scheduleCost=cost,
                                additionalDetails=full_description[:500],
                                otherDetails=other_details,
                                host_name=instance.RealName or instance.name,
                                host_link=f"/resorts/{instance.slug or instance.name}/",
                                scheduleTypeAndMode="Resort Tour Package",
                                scheduleWebsite=f"https://www.paratara.com/resorts/{instance.slug or instance.name}/",
                                dateN=dn,
                                monthN=mn,
                                yearN=yn,
                                exactDate=ds,
                            )

                            # Add to place's eventSchedules
                            place.eventSchedules.add(event)

                            # Wire link back to the originating resort package item
                            try:
                                sub_obj = Packages.objects.filter(id=sub_data.get('id')).first()
                                if sub_obj:
                                    sub_obj.siargaoevents.add(event)
                            except Exception:
                                pass
                            created_count += 1
                            print(f"✅ Created event '{event.scheduleTitle}' (ID: {event.id}) for {place.placename}")
                            print(f"   📅 Date: {event.exactDate} ({event.monthN}/{event.dateN}/{event.yearN})")
                        logger.info(f"Created {created_count} events for {sub_data['title']} at {place.placename}")

                    except Exception as e:
                        print(f"❌ Error creating event for subpackage '{sub_data['title']}': {e}")
                        import traceback
                        traceback.print_exc()
                
            except resortPackages.DoesNotExist:
                print(f"❌ Package {package_id} does not exist")
                continue
            except Exception as e:
                print(f"❌ Error creating event for package {package_id}: {e}")
                import traceback
                traceback.print_exc()
                logger.error(f"Error creating event for package {package_id}: {e}")


def _create_events_for_subpackage(sub: Packages):
    """Create place events for a single subpackage, one per specific date."""
    try:
        package = sub.packageName
        if not package:
            print("⚠️ Subpackage has no parent package")
            return
        resort = package.ItemOfResort
        if not resort:
            print("⚠️ Package has no associated resort")
            return
        place = resort.place
        if not place:
            print(f"⚠️ Resort {resort.name} has no place assigned")
            return

        # Only create events for Special Promotions (packages under resortTour)
        if package not in resort.resortTour.all():
            print(f"⏭️ Skipping event creation for '{sub.title}' because its category is not Special Promotion (tour)")
            return

        full_description = f"{sub.title}. {sub.description} {sub.information} {resort.description}".strip()
        cost = str(sub.price) if sub.price else "Free"
        # pick first image or resort header
        imgs = [img.urlField for img in sub.images]
        image_url = imgs[0] if imgs else (resort.headerImage or "")

        print(f"🤖 Calling OpenAI to extract date for new promo '{sub.title}'...")
        date_info = extract_date_with_openai(
            title=sub.title,
            description=full_description,
            location=f"{resort.address or place.placename}"
        )

        other_details = ""
        if date_info.get("recurring_pattern"):
            other_details = f"Recurring: {date_info['recurring_pattern']}"

        specific_dates = date_info.get("specific_dates", [])
        if not specific_dates:
            specific_dates = [{
                "dateN": datetime.now().day,
                "monthN": datetime.now().month,
                "yearN": datetime.now().year,
                "date_string": datetime.now().strftime("%b %d, %Y")
            }]

        created = 0
        for d in specific_dates:
            dn = d.get("dateN")
            mn = d.get("monthN")
            yn = d.get("yearN")
            ds = d.get("date_string", "")

            # Deduplicate same place/title/date
            exists = SiargaoEventSchedule.objects.filter(
                place=place,
                scheduleTitle=sub.title,
                dateN=dn,
                monthN=mn,
                yearN=yn
            ).exists()
            if exists:
                print(f"↪️ Skipping duplicate event for {sub.title} on {mn}/{dn}/{yn}")
                continue

            # Use the place name as location to keep events tied to the resort's place
            event = SiargaoEventSchedule.objects.create(
                package=sub,
                place=place,
                scheduleTitle=sub.title,
                # Show resort name as the event location
                schedulePlace=f"📍 Location: https://www.google.com/maps/dir/?api=1&destination={resort.latitude},{resort.longitude}",
                posterName=resort.RealName or resort.name,
                posterURL=f"/resorts/{resort.slug or resort.name}/",
                scheduleImageURL=image_url,
                backgroundURL=image_url,
                thumbnailURL=image_url,
                scheduleCost=cost,
                additionalDetails=full_description[:500],
                otherDetails=other_details,
                host_name=resort.RealName or resort.name,
                host_link=f"/resorts/{resort.slug or resort.name}/",
                scheduleTypeAndMode="Resort Promotion",
                scheduleWebsite=f"https://paratara.com/resorts/{resort.slug or resort.name}/",
                dateN=dn,
                monthN=mn,
                yearN=yn,
                exactDate=ds,
            )

            place.eventSchedules.add(event)

            # Wire link back to the originating resort package item
            try:
                sub.siargaoevents.add(event)
            except Exception:
                pass
            created += 1
            print(f"✅ Created promo event '{event.scheduleTitle}' (ID: {event.id}) for {place.placename}")
            print(f"   📅 Date: {event.exactDate} ({event.monthN}/{event.dateN}/{event.yearN})")
        logger.info(f"Created {created} promo events for {sub.title} at {place.placename}")

    except Exception as e:
        print(f"❌ Error creating events for subpackage '{sub}': {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=Packages)
def create_events_on_promo_created(sender, instance: Packages, created, **kwargs):
    """
    Automatically create place events when a resort promotion (subpackage) is created.
    This ensures events exist even before adding the package to resortTour.
    
    NOTE: This is skipped if _skip_event_creation is True (set by createPackages view
    to handle image upload before event creation).
    """
    # Skip if view is handling event creation manually (after image upload)
    if getattr(instance, '_skip_event_creation', False):
        print(f"⏭️ Skipping auto event creation for {instance.title} (will be handled manually)")
        return
    
    if created:
        print(f"🔔 Promo created: {instance.title}. Auto-creating events...")
        _create_events_for_subpackage(instance)


# Ensure newly created resorts are linked to their place's resort list
@receiver(post_save, sender=resortItem)
def link_resort_to_place(sender, instance: resortItem, created, **kwargs):
    try:
        if instance.place:
            # Only add on creation to avoid unnecessary writes on every update
            if created:
                instance.place.resortItem.add(instance)
                print(f"🏷️ Linked resort '{instance.name or instance.RealName}' to place '{instance.place.placename}'")
        
        # Generate QR code image and upload to Cloudinary if not set
        if created and not instance.resortQRLink:
            import qrcode
            from io import BytesIO
            
            # Build the resort URL
            slug = instance.slug or instance.name
            resort_path = f"/resorts/{slug}/"
            
            # Use settings domain or construct from request
            domain = getattr(settings, 'SITE_DOMAIN', 'http://localhost:8000')
            qr_url = f"{domain}{resort_path}"
            
            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to BytesIO buffer
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Upload to Cloudinary
            cloudinary.config(
                cloud_name="dam2loimt",
                api_key="662376458813576",
                api_secret="Y7vfoLOfo7lheRMDuN-YLQNwKec",
                secure=True,
            )
            
            public_id = f"resort_qr_{instance.id}_{slug}"
            upload_result = cloudinary.uploader.upload(
                buffer,
                public_id=public_id,
                folder="resort_qr_codes"
            )
            
            qr_image_url = upload_result.get('secure_url', '')
            
            # Update the resort with QR image URL
            resortItem.objects.filter(pk=instance.pk).update(resortQRLink=qr_image_url)
            print(f"🔗 Generated and uploaded QR code for resort '{instance.name}': {qr_image_url}")
            
    except Exception as e:
        print(f"⚠️ Failed linking resort to place or generating QR: {e}")
        import traceback
        traceback.print_exc()
    

# When a resort is deleted, remove all its promotion events from the place
@receiver(post_delete, sender=resortItem)
def delete_events_for_resort(sender, instance: resortItem, **kwargs):
    try:
        place = getattr(instance, 'place', None)
        slug_or_name = getattr(instance, 'slug', None) or getattr(instance, 'name', '')
        host_link = f"/resorts/{slug_or_name}/" if slug_or_name else ''

        qs = SiargaoEventSchedule.objects.filter(scheduleTypeAndMode="Resort Promotion")
        if host_link:
            qs = qs.filter(host_link=host_link)
        if place:
            qs = qs.filter(place=place)

        deleted_count, _ = qs.delete()
        logger.info(f"🗑️ Deleted {deleted_count} events for resort {instance} ({slug_or_name})")
    except Exception as e:
        logger.error(f"Error deleting events for resort {instance}: {e}")


# When a promotion (subpackage) is deleted, remove its events from the place
@receiver(post_delete, sender=Packages)
def delete_events_for_package(sender, instance: Packages, **kwargs):
    try:
        package = getattr(instance, 'packageName', None)
        resort = getattr(package, 'ItemOfResort', None) if package else None
        place = getattr(resort, 'place', None)
        slug_or_name = getattr(resort, 'slug', None) or getattr(resort, 'name', '') if resort else ''
        host_link = f"/resorts/{slug_or_name}/" if slug_or_name else ''

        qs = SiargaoEventSchedule.objects.filter(
            scheduleTypeAndMode="Resort Promotion",
            scheduleTitle=instance.title
        )
        if host_link:
            qs = qs.filter(host_link=host_link)
        if place:
            qs = qs.filter(place=place)

        deleted_count, _ = qs.delete()
        logger.info(f"🗑️ Deleted {deleted_count} events for package {instance.title} ({deleted_count} removed)")
    except Exception as e:
        logger.error(f"Error deleting events for package {instance}: {e}")


# When a promotion (subpackage) is about to be deleted, remove its images from Cloudinary
@receiver(pre_delete, sender=Packages)
def delete_images_for_package(sender, instance: Packages, **kwargs):
    try:
        # Ensure Cloudinary is configured (use same creds as uploader)
        cloudinary.config(
            cloud_name="dam2loimt",
            api_key="662376458813576",
            api_secret="Y7vfoLOfo7lheRMDuN-YLQNwKec",
            secure=True,
        )

        def _public_id_from_url(url: str):
            try:
                if '/upload/' not in url:
                    return None
                tail = url.split('/upload/', 1)[1]
                parts = tail.split('/')
                # drop version segment like v123456789 if present
                if parts and parts[0].startswith('v') and parts[0][1:].isdigit():
                    parts = parts[1:]
                if not parts:
                    return None
                filename = '/'.join(parts)
                # strip extension
                public_id = filename.rsplit('.', 1)[0]
                return public_id
            except Exception:
                return None

        urls = [img.urlField for img in instance.ImageURL.all()]
        for url in urls:
            public_id = _public_id_from_url(url)
            if not public_id:
                continue
            try:
                cloudinary.uploader.destroy(public_id)
                logger.info(f"🗑️ Deleted Cloudinary asset {public_id} for package {instance.title}")
            except Exception as cloud_err:
                logger.warning(f"⚠️ Failed to delete Cloudinary asset {public_id}: {cloud_err}")

        # Clean up sideImagesURLs rows tied to this package
        instance.ImageURL.all().delete()
    except Exception as e:
        logger.error(f"Error deleting images for package {instance}: {e}")

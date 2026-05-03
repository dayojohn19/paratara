from django.core.management.base import BaseCommand
from home.models import CommunityBulletinPost, Places_v2
from django.utils.text import slugify
import json
import os
# Usage
# python3 manage.py import_fb_posts --place="Siargao"

class Command(BaseCommand):
    help = 'Import Facebook posts from facebook_posts.json as CommunityBulletinPost items.'

    def add_arguments(self, parser):
        parser.add_argument('--place', type=str, help='Placename to assign to imported posts')

    def handle(self, *args, **options):
        output_dir = 'output'
        placename = options.get('place')
        if placename:
            # Try to find a file with the placename in the output folder
            files = [f for f in os.listdir(output_dir) if f.startswith('facebook_posts_') and placename.lower() in f.lower() and f.endswith('.json')]
            if files:
                json_path = os.path.join(output_dir, files[0])
            else:
                self.stdout.write(self.style.ERROR(f'No JSON file found for placename "{placename}" in {output_dir}'))
                return
        else:
            # Fallback to any facebook_posts_*.json file in output folder
            files = [f for f in os.listdir(output_dir) if f.startswith('facebook_posts_') and f.endswith('.json')]
            if files:
                json_path = os.path.join(output_dir, files[0])
            else:
                self.stdout.write(self.style.ERROR(f'No JSON file found in {output_dir}'))
                return
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return
        with open(json_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)

        placename = options.get('place')
        if placename:
            slug = slugify(placename)
            place = Places_v2.objects.filter(slug=slug).first()
            if not place:
                self.stdout.write(self.style.ERROR(f'No Places_v2 found with slug "{slug}" (from placename "{placename}").'))
                return
        else:
            place = Places_v2.objects.first()
            if not place:
                self.stdout.write(self.style.ERROR('No Places_v2 found.'))
                return

        created_count = 0
        from home.models import CommunityBulletinImage
        from home.signals import _publish_bulletin_post_to_social
        for post in posts:
            ai_title = post.get('message', '')[:160]
            ai_description = f"{post.get('message', '')}\n{post.get('permalink_url', '')}"
            obj, created = CommunityBulletinPost.objects.get_or_create(
                place=place,
                ai_title=ai_title,
                ai_description=ai_description,
            )
            # Create CommunityBulletinImage if full_picture exists and not already linked
            full_picture = post.get('full_picture')
            if full_picture and not obj.images.filter(image_url=full_picture).exists():
                CommunityBulletinImage.objects.create(post=obj, image_url=full_picture)
            if created:
                created_count += 1
                # Publish to social after creation (if image exists)
                if obj.images.exists():
                    _publish_bulletin_post_to_social(post_id=obj.id)
        self.stdout.write(self.style.SUCCESS(f'Imported {created_count} new CommunityBulletinPost items.'))

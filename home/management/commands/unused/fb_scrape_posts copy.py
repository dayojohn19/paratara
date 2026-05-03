from django.core.management.base import BaseCommand
import requests
import json
import os

# python3 manage.py fb_scrape_posts --page_id="APhilippineAbsentPOV" --place="Siargao"

class Command(BaseCommand):
    help = 'Scrape latest Facebook page posts and save to a file.'

    def add_arguments(self, parser):
        parser.add_argument('--page_id', type=str, default='APhilippineAbsentPOV', help='Facebook Page ID to scrape')
        parser.add_argument('--place', type=str, default='', help='Place name to include in output file')

    def handle(self, *args, **options):
        ACCESS_TOKEN = 'EAANyQ8lj90kBQdVD0LiwCGUqZCaaxFB0ZClkoKmcJN6sa8rZCVPOeJymSETFmHHrhCX0bpSGYt6GzHT0I3iXlVnsc6ZAgaxMZClRV5V5rZCzgIZCXhdRg95Oj3R2LzgNbtQ0C9nDmhMZBWOEHSIH6AAPbvP07ZAUJz4yO4sRk6IklyZBBzTrKnNdDQZAZCk9mwGB06Y5QZArPtRJZBzUDZBkgAj7QqmwT0RPQraf9rjXHoDZBzPkon4LakKAASWhInVGM5LtWawyhRyFJjlZBTZAvnZAZBjOOxScMQZDZD'
        PAGE_ID = options.get('page_id', 'APhilippineAbsentPOV')
        PLACE = options.get('place', '').strip()
        POST_LIMIT = 4  # Number of posts to fetch
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        if PLACE:
            OUTPUT_FILE = os.path.join(output_dir, f'facebook_posts_{PAGE_ID}_{PLACE}.json')
        else:
            OUTPUT_FILE = os.path.join(output_dir, f'facebook_posts_{PAGE_ID}.json')

        # Load existing posts if file exists
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                existing_posts = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_posts = []

        existing_ids = {post.get('id') for post in existing_posts}

        url = f'https://graph.facebook.com/v18.0/{PAGE_ID}/posts'
        params = {
            'access_token': ACCESS_TOKEN,
            'limit': POST_LIMIT,
            'fields': 'id,message,created_time,permalink_url,full_picture'
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('data', [])
            new_posts = [post for post in posts if post.get('id') not in existing_ids]
            all_posts = existing_posts + new_posts
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_posts, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f'Added {len(new_posts)} new posts. Total posts: {len(all_posts)} in {OUTPUT_FILE}'))
        else:
            self.stdout.write(self.style.ERROR(f'Error fetching posts: {response.status_code}'))
            self.stdout.write(response.text)
 
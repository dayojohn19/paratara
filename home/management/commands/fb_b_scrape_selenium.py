import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from django.core.management.base import BaseCommand
from home.models import FacebookPagePost
# USAGE:
# python manage.py fb_scrape_selenium --page_id="CGSSIA" --place="Siargao"
def scrape_facebook_page(page_id, place, post_limit=4, output_dir='output'):
    url = f'https://www.facebook.com/{page_id}/posts'
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)  # Wait for page to load
 
    posts_data = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    while len(posts_data) < post_limit:
        posts = driver.find_elements(By.XPATH, '//div[@role="article"]')
        for post in posts:
            try:
                message = post.text
                # Try to extract permalink
                links = post.find_elements(By.TAG_NAME, 'a')
                permalink = ''
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/posts/' in href:
                        permalink = href
                        break
                # Try to extract images
                img_urls = []
                imgs = post.find_elements(By.TAG_NAME, 'img')
                for img in imgs:
                    src = img.get_attribute('src')
                    if src and 'scontent' in src:
                        img_urls.append(src)
                posts_data.append({
                    'message': message[:500],
                    'permalink_url': permalink,
                    'full_picture': img_urls
                })
                if len(posts_data) >= post_limit:
                    break
            except Exception:
                continue
        # Scroll down to load more posts if needed
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    driver.quit()
    posts_data = posts_data[:post_limit]
    
    # Create FacebookPagePost objects
    for post in posts_data:
        permalink = post.get('permalink_url', '')
        if permalink:
            # Extract fb_post_id from permalink, e.g., https://www.facebook.com/CGSSIA/posts/1234567890
            try:
                parts = permalink.split('/posts/')
                if len(parts) == 2:
                    page_part = parts[0].split('/')[-1]
                    post_id = parts[1].split('/')[0].split('?')[0]  # remove query params
                    fb_post_id = f"{page_part}_{post_id}"
                else:
                    fb_post_id = permalink
            except:
                fb_post_id = permalink
        else:
            fb_post_id = f"{page_id}_{hash(post['message'])}"  # fallback unique id
        
        FacebookPagePost.objects.update_or_create(
            fb_post_id=fb_post_id,
            defaults={
                'message': post['message'],
                'permalink_url': permalink,
                'media_json': {'media_urls': post['full_picture']},
                'raw_json': post,
            }
        )
    
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'facebook_posts_{page_id}_{place}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)
    print(f'Saved {len(posts_data)} posts to {output_file} and database')

class Command(BaseCommand):
    help = 'Scrape a few public posts from a Facebook page using Selenium.'

    def add_arguments(self, parser):
        parser.add_argument('--page_id', type=str, required=True, help='Facebook Page ID to scrape')
        parser.add_argument('--place', type=str, required=True, help='Place name to include in output file')
        parser.add_argument('--post_limit', type=int, default=4, help='Number of posts to fetch')

    def handle(self, *args, **options):
        page_id = options['page_id']
        place = options['place']
        post_limit = options['post_limit']
        try:
            scrape_facebook_page(page_id, place, post_limit=post_limit)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error scraping Facebook page: {e}'))

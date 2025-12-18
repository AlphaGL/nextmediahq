# news/management/commands/scrape_sportingsun.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from news.models import News, Category
from bs4 import BeautifulSoup
import requests
import re
import time
from urllib.parse import urljoin

class Command(BaseCommand):
    help = 'Scrape sports news from Sporting Sun'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='Page number to start scraping from (default: 1)'
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            default=3,
            help='Maximum number of pages to scrape (default: 3)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default='sports',
            help='Category slug to assign scraped news (default: sports)'
        )

    def handle(self, *args, **options):
        start_page = options['start_page']
        max_pages = options['max_pages']
        category_slug = options['category']
        
        # Calculate end page
        end_page = start_page + max_pages - 1
        
        # Get or create a system user for scraped content
        scraper_user, created = User.objects.get_or_create(
            username='sportingsun_scraper',
            defaults={
                'email': 'scraper@sportingsun.ng',
                'first_name': 'Sporting Sun',
                'last_name': 'Scraper'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created scraper user: {scraper_user.username}"))
        
        # Get or create Sports category
        category, created = Category.objects.get_or_create(
            slug=category_slug,
            defaults={'name': category_slug.replace('-', ' ').title()}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created category: {category.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Starting Sporting Sun scraper - Category: {category.name}"))
        self.stdout.write(self.style.SUCCESS(f"📄 Scraping pages {start_page} to {end_page}"))
        
        base_url = "https://sportingsun.ng"
        api_url = "https://sportingsun.ng/wp-json/wp/v2/posts"
        
        total_scraped = 0
        total_skipped = 0
        
        for page in range(start_page, end_page + 1):
            self.stdout.write(f"\n📄 Fetching page {page}...")
            
            try:
                # Fetch posts from WordPress API
                params = {
                    'page': page,
                    'per_page': 10,
                    '_embed': 1  # Include featured media and author info
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(api_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                posts = response.json()
                
                if not posts:
                    self.stdout.write(self.style.WARNING("⚠️ No more posts found"))
                    break
                
                self.stdout.write(f"   📰 Found {len(posts)} posts on page {page}")
                
                for post in posts:
                    try:
                        # Extract post data
                        title = BeautifulSoup(post['title']['rendered'], 'html.parser').get_text().strip()
                        link = post['link']
                        
                        # Check if already exists
                        if News.objects.filter(title=title).exists():
                            self.stdout.write(self.style.WARNING(f"⏭️ Skipped (exists): {title[:50]}..."))
                            total_skipped += 1
                            continue
                        
                        # Get content
                        content_html = post['content']['rendered']
                        content = BeautifulSoup(content_html, 'html.parser').get_text()
                        
                        # Clean up content - remove excessive whitespace
                        content = re.sub(r'\s+', ' ', content).strip()
                        
                        # Remove "sunsports reports" and similar patterns
                        content = re.sub(r'sunsports\s+reports[.,]?\s*', '', content, flags=re.IGNORECASE)
                        
                        # Get excerpt
                        excerpt_html = post['excerpt']['rendered']
                        excerpt = BeautifulSoup(excerpt_html, 'html.parser').get_text().strip()
                        
                        # Get featured image
                        image_url = ''
                        if '_embedded' in post and 'wp:featuredmedia' in post['_embedded']:
                            try:
                                media = post['_embedded']['wp:featuredmedia'][0]
                                # Try to get the largest available image
                                if 'media_details' in media and 'sizes' in media['media_details']:
                                    sizes = media['media_details']['sizes']
                                    # Prefer full > large > medium-large > medium
                                    for size_name in ['full', 'large', 'medium_large', 'medium']:
                                        if size_name in sizes:
                                            image_url = sizes[size_name]['source_url']
                                            break
                                if not image_url:
                                    image_url = media.get('source_url', '')
                            except (KeyError, IndexError):
                                pass
                        
                        # Get author
                        author = ''
                        if '_embedded' in post and 'author' in post['_embedded']:
                            try:
                                author = post['_embedded']['author'][0]['name']
                            except (KeyError, IndexError):
                                author = 'Sporting Sun'
                        else:
                            author = 'Sporting Sun'
                        
                        # Get published date
                        published_date = timezone.now()
                        try:
                            from dateutil import parser
                            published_date = parser.parse(post['date_gmt']).replace(tzinfo=timezone.utc)
                        except:
                            pass
                        
                        # Create slug from title
                        slug = re.sub(r'[^\w\s-]', '', title.lower())
                        slug = re.sub(r'[-\s]+', '-', slug)[:50]
                        
                        # Make slug unique if needed
                        original_slug = slug
                        counter = 1
                        while News.objects.filter(slug=slug).exists():
                            slug = f"{original_slug}-{counter}"
                            counter += 1
                        
                        # Determine if should be featured (e.g., posts from categories 4, 7, 8)
                        is_featured = False
                        post_categories = post.get('categories', [])
                        featured_cat_ids = [4, 7, 8]  # Football, EPL, Transfer News based on the API
                        if any(cat_id in featured_cat_ids for cat_id in post_categories):
                            is_featured = True
                        
                        # Create news entry
                        news = News.objects.create(
                            title=title,
                            slug=slug,
                            content=content,
                            excerpt=excerpt[:500] if len(excerpt) > 500 else excerpt,
                            category=category,
                            author=author,
                            published_by=scraper_user,
                            published_date=published_date,
                            is_published=True,
                            is_featured=is_featured,
                            featured_image_url=image_url if image_url else None
                        )
                        
                        # Log image URL
                        if image_url:
                            self.stdout.write(f"   🖼️ Image URL: {image_url[:60]}...")
                        
                        total_scraped += 1
                        feat_indicator = "⭐" if is_featured else ""
                        self.stdout.write(self.style.SUCCESS(f"✅ {feat_indicator} Scraped: {title[:60]}..."))
                        
                        # Respect rate limiting
                        time.sleep(1)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Error processing post: {e}"))
                        import traceback
                        self.stdout.write(self.style.ERROR(traceback.format_exc()))
                        continue
                
                # Delay between pages
                time.sleep(2)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    self.stdout.write(self.style.WARNING(f"⚠️ No more pages available (page {page})"))
                    break
                else:
                    self.stdout.write(self.style.ERROR(f"❌ HTTP Error on page {page}: {e}"))
                    continue
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"❌ Request Error on page {page}: {e}"))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Unexpected error on page {page}: {e}"))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                continue
        
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Scraping complete!"))
        self.stdout.write(self.style.SUCCESS(f"   📊 Total scraped: {total_scraped}"))
        self.stdout.write(self.style.SUCCESS(f"   ⏭️ Total skipped: {total_skipped}"))
        self.stdout.write(self.style.SUCCESS(f"   ⭐ Featured: {News.objects.filter(category=category, is_featured=True).count()}"))
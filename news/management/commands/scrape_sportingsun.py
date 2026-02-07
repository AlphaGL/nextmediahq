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
    help = 'Scrape sports news from Sporting Sun with automatic category detection'

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
            '--default-category',
            type=str,
            default='sports',
            help='Default category if none detected (default: sports)'
        )

    def get_or_create_category(self, category_name):
        """Get or create category, checking if it exists first"""
        # Normalize category name
        category_name = category_name.strip().title()
        category_slug = re.sub(r'[^\w\s-]', '', category_name.lower())
        category_slug = re.sub(r'[-\s]+', '-', category_slug)
        
        # Check if category already exists (by slug or name)
        category = Category.objects.filter(slug=category_slug).first()
        
        if category:
            return category
        
        # Check by name (case-insensitive)
        category = Category.objects.filter(name__iexact=category_name).first()
        
        if category:
            return category
        
        # Create new category
        category = Category.objects.create(
            name=category_name,
            slug=category_slug,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f"      ✨ Created new category: {category.name}"))
        return category

    def map_wordpress_category(self, category_id, category_name):
        """Map WordPress category ID/name to our category structure"""
        # Sporting Sun category mapping based on their WordPress structure
        category_mapping = {
            # Football-related
            4: 'Football',
            7: 'EPL',  # English Premier League
            8: 'Transfer News',
            26: 'La Liga',
            27: 'Serie A',
            28: 'Bundesliga',
            29: 'Champions League',
            30: 'Europa League',
            31: 'World Cup',
            
            # Other sports
            5: 'Basketball',
            6: 'Boxing',
            9: 'Tennis',
            10: 'Athletics',
            11: 'Cricket',
            12: 'Rugby',
            13: 'Formula 1',
            14: 'MMA',
            15: 'Golf',
            
            # General
            1: 'Sports',  # General sports
            2: 'News',
            3: 'Features',
        }
        
        # Try mapping by ID first
        if category_id in category_mapping:
            return category_mapping[category_id]
        
        # Try to extract from category name
        if category_name:
            name_lower = category_name.lower()
            
            # Football/Soccer keywords
            if any(keyword in name_lower for keyword in ['football', 'soccer', 'premier league', 'epl']):
                if 'premier' in name_lower or 'epl' in name_lower:
                    return 'EPL'
                elif 'transfer' in name_lower:
                    return 'Transfer News'
                elif 'champions' in name_lower:
                    return 'Champions League'
                else:
                    return 'Football'
            
            # Basketball
            if 'basketball' in name_lower or 'nba' in name_lower:
                return 'Basketball'
            
            # Boxing/MMA
            if 'boxing' in name_lower:
                return 'Boxing'
            if 'mma' in name_lower or 'ufc' in name_lower:
                return 'MMA'
            
            # Tennis
            if 'tennis' in name_lower:
                return 'Tennis'
            
            # Athletics
            if 'athletics' in name_lower or 'track' in name_lower:
                return 'Athletics'
            
            # Use the category name as-is if it doesn't match
            return category_name.title()
        
        return 'Sports'  # Default fallback

    def handle(self, *args, **options):
        start_page = options['start_page']
        max_pages = options['max_pages']
        default_category_name = options['default_category']
        
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
        
        # Get or create default category
        default_category = self.get_or_create_category(default_category_name)
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Starting Sporting Sun scraper with auto-category detection"))
        self.stdout.write(self.style.SUCCESS(f"📄 Scraping pages {start_page} to {end_page}"))
        self.stdout.write(self.style.SUCCESS(f"🏷️  Default category: {default_category.name}"))
        
        base_url = "https://sportingsun.ng"
        api_url = "https://sportingsun.ng/wp-json/wp/v2/posts"
        
        total_scraped = 0
        total_skipped = 0
        categories_created = set()
        category_stats = {}
        
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
                        
                        self.stdout.write(f"\n   📰 Processing: {title[:60]}...")
                        
                        # Get categories for this post
                        post_categories = post.get('categories', [])
                        category = None
                        category_name = None
                        
                        # If post has categories, try to map them
                        if post_categories and '_embedded' in post and 'wp:term' in post['_embedded']:
                            try:
                                terms = post['_embedded']['wp:term']
                                if terms and len(terms) > 0:
                                    # Get the first category
                                    first_category = terms[0][0] if isinstance(terms[0], list) and terms[0] else None
                                    
                                    if first_category:
                                        wp_category_id = first_category.get('id')
                                        wp_category_name = first_category.get('name', '')
                                        
                                        self.stdout.write(f"      🏷️  WP Category: {wp_category_name} (ID: {wp_category_id})")
                                        
                                        # Map to our category
                                        category_name = self.map_wordpress_category(wp_category_id, wp_category_name)
                                        self.stdout.write(f"      🏷️  Mapped to: {category_name}")
                            except (KeyError, IndexError, TypeError) as e:
                                self.stdout.write(f"      ⚠️ Category extraction error: {e}")
                        
                        # Get or create the category
                        if category_name:
                            category = self.get_or_create_category(category_name)
                            if category.name not in categories_created:
                                categories_created.add(category.name)
                        else:
                            category = default_category
                            self.stdout.write(f"      🏷️  Using default category: {category.name}")
                        
                        # Track category usage
                        category_stats[category.name] = category_stats.get(category.name, 0) + 1
                        
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
                        
                        # Determine if should be featured
                        # Feature posts from important categories
                        featured_categories = ['Football', 'EPL', 'Transfer News', 'Champions League']
                        is_featured = category.name in featured_categories
                        
                        # Create news entry - ENSURE is_published is True
                        news = News.objects.create(
                            title=title,
                            slug=slug,
                            content=content,
                            excerpt=excerpt[:500] if len(excerpt) > 500 else excerpt,
                            category=category,
                            author=author,
                            published_by=scraper_user,
                            published_date=published_date,
                            is_published=True,  # CRITICAL: Set to True
                            is_featured=is_featured,
                            featured_image_url=image_url if image_url else None
                        )
                        
                        # Log image URL
                        if image_url:
                            self.stdout.write(f"      🖼️ Image URL: {image_url[:60]}...")
                        
                        total_scraped += 1
                        feat_indicator = "⭐" if is_featured else ""
                        self.stdout.write(self.style.SUCCESS(
                            f"      ✅ {feat_indicator} Scraped! Category: {category.name}"
                        ))
                        
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
        
        if categories_created:
            self.stdout.write(self.style.SUCCESS(f"   ✨ New categories created: {', '.join(sorted(categories_created))}"))
        
        if category_stats:
            self.stdout.write(self.style.SUCCESS(f"\n📈 Category Distribution:"))
            for cat_name, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(self.style.SUCCESS(f"      {cat_name}: {count} articles"))
        
        featured_count = News.objects.filter(
            published_by=scraper_user,
            is_featured=True
        ).count()
        self.stdout.write(self.style.SUCCESS(f"   ⭐ Featured articles: {featured_count}"))
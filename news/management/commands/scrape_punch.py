# news/management/commands/scrape_punch.py
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
    help = 'Scrape news from Punch Nigeria'

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
            default='national',
            help='Category slug to assign scraped news (default: global-news)'
        )

    def handle(self, *args, **options):
        start_page = options['start_page']
        max_pages = options['max_pages']
        category_slug = options['category']
        
        # Calculate end page
        end_page = start_page + max_pages - 1
        
        # Get or create a system user for scraped content
        scraper_user, created = User.objects.get_or_create(
            username='punch_scraper',
            defaults={
                'email': 'scraper@punchng.com',
                'first_name': 'Punch',
                'last_name': 'Scraper'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created scraper user: {scraper_user.username}"))
        
        # Get or create category
        category, created = Category.objects.get_or_create(
            slug=category_slug,
            defaults={'name': category_slug.replace('-', ' ').title()}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f"✅ Created category: {category.name}"))
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Starting Punch scraper - Category: {category.name}"))
        self.stdout.write(self.style.SUCCESS(f"📄 Scraping pages {start_page} to {end_page}"))
        
        base_url = "https://punchng.com"
        
        total_scraped = 0
        total_skipped = 0
        
        # Better headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        for page in range(start_page, end_page + 1):
            self.stdout.write(f"\n📄 Fetching page {page}...")
            
            try:
                # Construct URL
                if page == 1:
                    url = base_url
                else:
                    url = f"{base_url}/page/{page}/"
                
                self.stdout.write(f"   🔗 URL: {url}")
                
                # Fetch page
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                self.stdout.write(f"   ✅ Page fetched (Status: {response.status_code})")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try multiple selectors to find articles
                articles = []
                
                # Method 1: Find all article tags
                articles = soup.find_all('article')
                self.stdout.write(f"   📰 Found {len(articles)} article tags")
                
                # Method 2: If no articles found, try divs with post class
                if not articles:
                    articles = soup.find_all('div', class_=lambda x: x and 'post' in str(x).lower())
                    self.stdout.write(f"   📰 Found {len(articles)} post divs")
                
                # Method 3: Try finding by ID pattern
                if not articles:
                    articles = soup.find_all(id=lambda x: x and 'post-' in str(x))
                    self.stdout.write(f"   📰 Found {len(articles)} posts by ID")
                
                if not articles:
                    self.stdout.write(self.style.WARNING("   ⚠️ No articles found on this page"))
                    # Print some of the page structure for debugging
                    self.stdout.write("   🔍 Page structure sample:")
                    main_content = soup.find('main') or soup.find('div', class_='content')
                    if main_content:
                        self.stdout.write(f"   {str(main_content)[:500]}...")
                    break
                
                for idx, article in enumerate(articles, 1):
                    try:
                        self.stdout.write(f"\n   📰 Processing article {idx}/{len(articles)}...")
                        
                        # Try to find title and link - multiple methods
                        title_elem = None
                        link_elem = None
                        
                        # Method 1: h2 or h3 with entry-title class
                        title_elem = article.find(['h2', 'h3'], class_=lambda x: x and 'title' in str(x).lower())
                        
                        # Method 2: Just any h2 or h3 with a link
                        if not title_elem:
                            title_elem = article.find(['h2', 'h3'])
                        
                        # Method 3: Any heading tag
                        if not title_elem:
                            title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                        
                        if not title_elem:
                            self.stdout.write(f"      ⚠️ No title found in article")
                            continue
                        
                        # Get link
                        link_elem = title_elem.find('a')
                        if not link_elem:
                            link_elem = article.find('a')
                        
                        if not link_elem or not link_elem.get('href'):
                            self.stdout.write(f"      ⚠️ No link found")
                            continue
                        
                        title = title_elem.get_text().strip()
                        article_url = link_elem['href']
                        
                        # Ensure absolute URL
                        if not article_url.startswith('http'):
                            article_url = urljoin(base_url, article_url)
                        
                        self.stdout.write(f"      📌 Title: {title[:60]}...")
                        self.stdout.write(f"      🔗 URL: {article_url[:80]}...")
                        
                        # Check if already exists
                        if News.objects.filter(title=title).exists():
                            self.stdout.write(self.style.WARNING(f"      ⏭️ Skipped (exists)"))
                            total_skipped += 1
                            continue
                        
                        # Fetch full article
                        self.stdout.write(f"      🔄 Fetching full article...")
                        time.sleep(2)  # Longer delay to avoid rate limiting
                        
                        article_response = requests.get(article_url, headers=headers, timeout=30)
                        article_response.raise_for_status()
                        article_soup = BeautifulSoup(article_response.text, 'html.parser')
                        
                        # Get content - try multiple selectors
                        content_div = (
                            article_soup.find('div', class_='entry-content') or
                            article_soup.find('div', class_='post-content') or
                            article_soup.find('div', class_='content') or
                            article_soup.find('article')
                        )
                        
                        if not content_div:
                            self.stdout.write(self.style.WARNING(f"      ⚠️ No content found"))
                            continue
                        
                        # Extract text from paragraphs
                        paragraphs = content_div.find_all('p')
                        content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                        
                        # Clean up content
                        content = re.sub(r'\s+', ' ', content).strip()
                        
                        if not content or len(content) < 100:
                            self.stdout.write(self.style.WARNING(f"      ⚠️ Content too short ({len(content)} chars)"))
                            continue
                        
                        # Get excerpt
                        excerpt = content[:500] if len(content) > 500 else content
                        
                        # Get featured image
                        image_url = ''
                        img_elem = (
                            article_soup.find('img', class_='wp-post-image') or
                            article_soup.find('img', class_='featured-image') or
                            article_soup.find('meta', property='og:image')
                        )
                        
                        if img_elem:
                            if img_elem.name == 'meta':
                                image_url = img_elem.get('content', '')
                            else:
                                image_url = img_elem.get('src', '') or img_elem.get('data-src', '')
                        
                        # Ensure absolute URL for image
                        if image_url and not image_url.startswith('http'):
                            image_url = urljoin(base_url, image_url)
                        
                        # Get author
                        author = 'Punch Nigeria'
                        author_elem = (
                            article_soup.find('span', class_='author') or
                            article_soup.find('a', rel='author') or
                            article_soup.find('span', class_='by-author')
                        )
                        if author_elem:
                            author = author_elem.get_text().strip()
                            # Clean author name
                            author = re.sub(r'^by\s+', '', author, flags=re.IGNORECASE).strip()
                        
                        # Get published date
                        published_date = timezone.now()
                        date_elem = (
                            article_soup.find('time', class_='entry-date') or
                            article_soup.find('time') or
                            article_soup.find('meta', property='article:published_time')
                        )
                        
                        if date_elem:
                            try:
                                from dateutil import parser
                                if date_elem.name == 'meta':
                                    date_str = date_elem.get('content')
                                else:
                                    date_str = date_elem.get('datetime') or date_elem.get_text()
                                
                                if date_str:
                                    published_date = parser.parse(date_str)
                            except Exception as e:
                                self.stdout.write(f"      ⚠️ Date parse error: {e}")
                        
                        # Create slug
                        slug = re.sub(r'[^\w\s-]', '', title.lower())
                        slug = re.sub(r'[-\s]+', '-', slug)[:50]
                        
                        # Make slug unique
                        original_slug = slug
                        counter = 1
                        while News.objects.filter(slug=slug).exists():
                            slug = f"{original_slug}-{counter}"
                            counter += 1
                        
                        # Create news entry
                        news = News.objects.create(
                            title=title,
                            slug=slug,
                            content=content,
                            excerpt=excerpt,
                            category=category,
                            author=author,
                            published_by=scraper_user,
                            published_date=published_date,
                            is_published=True,
                            is_featured=False,
                            featured_image_url=image_url if image_url else None
                        )
                        
                        if image_url:
                            self.stdout.write(f"      🖼️ Image: {image_url[:60]}...")
                        
                        total_scraped += 1
                        self.stdout.write(self.style.SUCCESS(f"      ✅ Successfully scraped!"))
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"      ❌ Error processing article: {e}"))
                        import traceback
                        self.stdout.write(self.style.ERROR(f"      {traceback.format_exc()}"))
                        continue
                
                # Delay between pages
                self.stdout.write(f"\n   ⏳ Waiting 3 seconds before next page...")
                time.sleep(3)
                
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"❌ HTTP Error on page {page}: {e}"))
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error on page {page}: {e}"))
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                continue
        
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Scraping complete!"))
        self.stdout.write(self.style.SUCCESS(f"   📊 Total scraped: {total_scraped}"))
        self.stdout.write(self.style.SUCCESS(f"   ⏭️ Total skipped: {total_skipped}"))
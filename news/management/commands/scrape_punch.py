# news/management/commands/scrape_punch.py
"""
Scrapes punchng.com using their sitemap / RSS feed + article pages.

Strategy (most reliable against layout changes):
  1. Fetch RSS feed  https://punchng.com/feed/  — always works, no HTML parsing needed
  2. For each item: fetch the article page to get full content + category
  3. Save to DB, skip duplicates by title

Falls back to HTML scraping of /page/N/ if RSS is empty.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from news.models import News, Category
from bs4 import BeautifulSoup
import requests
import re
import time
from urllib.parse import urljoin
from dateutil import parser as dateparser


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

BASE_URL = 'https://punchng.com'
RSS_URL  = 'https://punchng.com/feed/'


class Command(BaseCommand):
    help = 'Scrape news from Punch Nigeria (RSS + article pages)'

    def add_arguments(self, parser):
        parser.add_argument('--max-pages', type=int, default=5,
                            help='Max listing pages to crawl if RSS fails (default: 5)')
        parser.add_argument('--start-page', type=int, default=1)
        parser.add_argument('--default-category', type=str, default='national')

    # ── helpers ───────────────────────────────────────────────

    def _session(self):
        s = requests.Session()
        s.headers.update(HEADERS)
        return s

    def _get_or_create_category(self, name):
        name  = (name or 'National').strip().title()
        slug  = re.sub(r'[^\w\s-]', '', name.lower())
        slug  = re.sub(r'[-\s]+', '-', slug)
        cat   = (Category.objects.filter(slug=slug).first() or
                 Category.objects.filter(name__iexact=name).first())
        if cat:
            return cat
        return Category.objects.create(name=name, slug=slug, is_active=True)

    def _make_slug(self, title):
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:60]
        base, n = slug, 1
        while News.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'; n += 1
        return slug

    def _cat_from_url(self, url):
        known = ['politics','business','sports','entertainment','metro',
                 'health','tech','lifestyle','education','opinion',
                 'world','crime','investigations','national']
        for part in url.split('/'):
            if part.lower() in known:
                return part.title()
        return None

    def _cat_from_soup(self, soup):
        for sel in [
            ('a',  {'rel': 'category tag'}),
            ('meta', {'property': 'article:section'}),
        ]:
            el = soup.find(sel[0], sel[1])
            if el:
                return (el.get('content') or el.get_text()).strip()
        bc = soup.find('div', class_=re.compile(r'breadcrumb', re.I))
        if bc:
            links = bc.find_all('a')
            if len(links) > 1:
                return links[1].get_text().strip()
        return None

    # ── RSS path ──────────────────────────────────────────────

    def _items_from_rss(self, session, max_items=50):
        """Return list of {title, url, published} from RSS."""
        try:
            r = session.get(RSS_URL, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'xml')
            items = []
            for item in soup.find_all('item')[:max_items]:
                title = (item.find('title') or {}).get_text(strip=True)
                url   = (item.find('link')  or {}).get_text(strip=True)
                pub   = (item.find('pubDate') or {}).get_text(strip=True)
                if title and url:
                    items.append({'title': title, 'url': url, 'pub': pub})
            self.stdout.write(f'   📡 RSS: {len(items)} items')
            return items
        except Exception as e:
            self.stdout.write(f'   ⚠️  RSS failed: {e}')
            return []

    # ── HTML listing fallback ─────────────────────────────────

    def _urls_from_listing(self, session, page):
        url = BASE_URL if page == 1 else f'{BASE_URL}/page/{page}/'
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 404:
                return None          # signal: no more pages
            r.raise_for_status()
        except Exception as e:
            self.stdout.write(f'   ❌ Listing fetch error: {e}')
            return []

        soup  = BeautifulSoup(r.text, 'html.parser')
        links = set()

        # Punch now uses <h2 class="entry-title"> or <h3 class="post-title">
        for tag in soup.find_all(['h2','h3'], class_=re.compile(r'(entry|post)-title', re.I)):
            a = tag.find('a', href=True)
            if a:
                links.add(a['href'])

        # Fallback: all <a> inside <article>
        if not links:
            for art in soup.find_all('article'):
                a = art.find('a', href=True)
                if a and 'punchng.com' in a['href']:
                    links.add(a['href'])

        # Fallback: any punchng.com link that looks like an article
        if not links:
            for a in soup.find_all('a', href=re.compile(r'punchng\.com/[^/]+/$')):
                links.add(a['href'])

        self.stdout.write(f'   🔗 Listing page {page}: {len(links)} links')
        return list(links)

    # ── Article parser ────────────────────────────────────────

    def _parse_article(self, session, url, fallback_title='', fallback_pub=None):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            self.stdout.write(f'      ❌ Fetch error: {e}')
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        # Title
        og   = soup.find('meta', property='og:title')
        title = og['content'].strip() if og and og.get('content') else ''
        if not title:
            h1 = soup.find('h1')
            title = h1.get_text(strip=True) if h1 else fallback_title
        title = re.sub(r'\s*[|\-–]\s*Punch.*$', '', title, flags=re.I).strip()
        if not title:
            return None

        # Category
        cat_name = self._cat_from_url(url) or self._cat_from_soup(soup)

        # Content
        content_div = (
            soup.find('div', class_='entry-content') or
            soup.find('div', class_='post-content')  or
            soup.find('article')
        )
        if not content_div:
            return None
        paras   = [p.get_text(strip=True) for p in content_div.find_all('p') if p.get_text(strip=True)]
        content = '\n\n'.join(paras)
        content = re.sub(r'\s+', ' ', content).strip()
        if len(content) < 80:
            return None

        # Image
        image_url = ''
        og_img = soup.find('meta', property='og:image')
        if og_img:
            image_url = og_img.get('content', '')
        if not image_url:
            img = soup.find('img', class_=re.compile(r'(featured|wp-post)', re.I))
            if img:
                image_url = img.get('src') or img.get('data-src', '')

        # Author
        author = 'Punch Nigeria'
        for sel in [('span','author'), ('a', {'rel':'author'}), ('span','by-author')]:
            el = soup.find(sel[0], sel[1] if isinstance(sel[1], dict) else {'class': sel[1]})
            if el:
                author = re.sub(r'^by\s+', '', el.get_text(strip=True), flags=re.I).strip() or author
                break

        # Date
        pub_date = fallback_pub or timezone.now()
        for sel in [('time', {'class':'entry-date'}), ('time',{}), ('meta',{'property':'article:published_time'})]:
            el = soup.find(sel[0], sel[1])
            if el:
                raw = el.get('content') or el.get('datetime') or el.get_text()
                try:
                    pub_date = dateparser.parse(raw)
                except Exception:
                    pass
                break

        return {
            'title':     title,
            'cat_name':  cat_name,
            'content':   content,
            'excerpt':   content[:500],
            'image_url': image_url,
            'author':    author,
            'pub_date':  pub_date,
        }

    # ── main ─────────────────────────────────────────────────

    def handle(self, *args, **options):
        max_pages    = options['max_pages']
        start_page   = options['start_page']
        default_cat  = options['default_category']

        scraper_user, _ = User.objects.get_or_create(
            username='punch_scraper',
            defaults={'email': 'scraper@punchng.com',
                      'first_name': 'Punch', 'last_name': 'Scraper'}
        )
        default_category = self._get_or_create_category(default_cat)
        session          = self._session()

        self.stdout.write(self.style.SUCCESS(
            f'🚀 Punch scraper | pages {start_page}–{start_page + max_pages - 1}'
        ))

        total_scraped = total_skipped = 0
        featured_cats = {'Politics','National','Breaking','Crime','Business','Metro'}

        # ── Try RSS first ─────────────────────────────────────
        rss_items = self._items_from_rss(session, max_items=max_pages * 15)
        urls_to_process = []   # list of (url, fallback_title, fallback_pub)

        if rss_items:
            for item in rss_items:
                pub = None
                try:
                    pub = dateparser.parse(item['pub'])
                except Exception:
                    pass
                urls_to_process.append((item['url'], item['title'], pub))
        else:
            # Fallback: crawl listing pages
            for page in range(start_page, start_page + max_pages):
                links = self._urls_from_listing(session, page)
                if links is None:
                    self.stdout.write('   ✅ No more listing pages.')
                    break
                for lnk in links:
                    urls_to_process.append((lnk, '', None))
                time.sleep(2)

        self.stdout.write(f'\n📋 Articles to process: {len(urls_to_process)}')

        for url, fb_title, fb_pub in urls_to_process:
            self.stdout.write(f'\n   🔗 {url[:80]}')

            if News.objects.filter(title=fb_title).exists() and fb_title:
                self.stdout.write('      ⏭️  Already exists — skipping')
                total_skipped += 1
                continue

            time.sleep(1)
            data = self._parse_article(session, url, fb_title, fb_pub)
            if not data:
                self.stdout.write('      ⚠️  Could not parse — skipping')
                continue

            if News.objects.filter(title=data['title']).exists():
                self.stdout.write('      ⏭️  Already exists — skipping')
                total_skipped += 1
                continue

            category   = self._get_or_create_category(data['cat_name']) if data['cat_name'] else default_category
            is_featured = category.name in featured_cats or bool(data['image_url'])

            News.objects.create(
                title             = data['title'][:200],
                slug              = self._make_slug(data['title']),
                content           = data['content'],
                excerpt           = data['excerpt'],
                category          = category,
                author            = data['author'],
                published_by      = scraper_user,
                published_date    = data['pub_date'],
                is_published      = True,
                is_featured       = is_featured,
                featured_image_url= data['image_url'] or None,
            )
            total_scraped += 1
            self.stdout.write(self.style.SUCCESS(
                f"      ✅ Saved | {category.name} | {'⭐' if is_featured else ''} {data['title'][:60]}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 Done — scraped: {total_scraped} | skipped: {total_skipped}'
        ))
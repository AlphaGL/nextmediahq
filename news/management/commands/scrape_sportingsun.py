"""
Scrapes sportingsun.ng (Sporting Sun) via RSS feed + article pages.

Strategy:
  1. Fetch RSS feed  https://sportingsun.ng/feed/  (main feed, ~10 items)
  2. Also fetch category RSS feeds  https://sportingsun.ng/category/<slug>/feed/
  3. For each item: fetch the article page for full content + category
  4. Save to DB, skip duplicates by title

Falls back to rotating through multiple RSS feeds if one is empty.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from news.models import News, Category
from bs4 import BeautifulSoup
import requests
import re
import sys
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
    'Referer': 'https://www.google.com/',
}

BASE_URL = 'https://sportingsun.ng'

# Multiple RSS feeds — WordPress category feeds + main feed
RSS_FEEDS = [
    ('Football',      'https://sportingsun.ng/category/football/feed/'),
    ('EPL',           'https://sportingsun.ng/category/epl/feed/'),
    ('Transfer News', 'https://sportingsun.ng/category/transfer-news/feed/'),
    ('Basketball',    'https://sportingsun.ng/category/basketball/feed/'),
    ('Boxing',        'https://sportingsun.ng/category/boxing/feed/'),
    ('Tennis',        'https://sportingsun.ng/category/tennis/feed/'),
    ('General',       'https://sportingsun.ng/feed/'),
]

FEATURED_CATS = {'Football', 'EPL', 'Transfer News', 'Champions League', 'Sports', 'Boxing'}

SPORTS_KEYWORDS = [
    'football', 'soccer', 'epl', 'premier league', 'transfer', 'champions league',
    'basketball', 'nba', 'boxing', 'tennis', 'athletics', 'sport', 'fifa',
    'super eagles', 'afcon', 'world cup', 'bundesliga', 'la liga', 'serie a',
]


class Command(BaseCommand):
    help = 'Scrape sports news from Sporting Sun (RSS + article pages)'

    def add_arguments(self, parser):
        parser.add_argument('--max-pages', type=int, default=5,
                            help='Max items per RSS feed (multiplied by 10, default: 5 → 50 items)')
        parser.add_argument('--start-page', type=int, default=1)
        parser.add_argument('--default-category', type=str, default='sports')

    # ── helpers ───────────────────────────────────────────────

    def _session(self):
        s = requests.Session()
        s.headers.update(HEADERS)
        return s

    def _get_or_create_category(self, name):
        name = (name or 'Sports').strip()
        # .title() would turn acronyms like EPL into "Epl"
        if name.islower():
            name = name.title()
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        cat  = (Category.objects.filter(slug=slug).first() or
                Category.objects.filter(name__iexact=name).first())
        if cat:
            return cat
        cat = Category.objects.create(name=name, slug=slug, is_active=True)
        self.stdout.write(self.style.SUCCESS(f'      ✨ New category: {cat.name}'))
        return cat

    def _make_slug(self, title):
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)[:60]
        base, n = slug, 1
        while News.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'; n += 1
        return slug

    def _detect_sports_category(self, title, url, meta_cat):
        """Map title/url/meta to a clean sports category name."""
        combined = f'{title} {url} {meta_cat}'.lower()

        if any(k in combined for k in ['premier league', 'epl', 'english premier']):
            return 'EPL'
        if any(k in combined for k in ['transfer', 'signing', 'signed']):
            return 'Transfer News'
        if 'champions league' in combined:
            return 'Champions League'
        if any(k in combined for k in ['football', 'soccer', 'super eagles', 'afcon',
                                        'world cup', 'bundesliga', 'la liga', 'serie a',
                                        'fifa', 'premier league']):
            return 'Football'
        if any(k in combined for k in ['basketball', 'nba']):
            return 'Basketball'
        if 'boxing' in combined:
            return 'Boxing'
        if 'tennis' in combined:
            return 'Tennis'
        if any(k in combined for k in ['athletics', 'track', 'field']):
            return 'Athletics'
        if meta_cat and meta_cat.lower() not in ('uncategorized', ''):
            return meta_cat.title()
        return 'Sports'

    # ── RSS reader ────────────────────────────────────────────

    def _items_from_rss(self, session, feed_url, max_items=50):
        """Return list of {title, url, pub, cat} from an RSS feed."""
        try:
            r = session.get(feed_url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            self.stdout.write(f'      ⚠️  RSS fetch failed ({feed_url}): {e}')
            return []

        try:
            soup = BeautifulSoup(r.text, 'lxml-xml')
        except Exception:
            soup = BeautifulSoup(r.text, 'xml')

        def _text(node):
            return node.get_text(strip=True) if node else ''

        items = []
        for item in soup.find_all('item')[:max_items]:
            title = _text(item.find('title'))
            url   = _text(item.find('link'))
            pub   = _text(item.find('pubDate'))
            cat   = _text(item.find('category'))
            if title and url and ('sportingsun.ng' in url or 'thesun.ng' in url):
                items.append({'title': title, 'url': url, 'pub': pub, 'cat': cat})

        self.stdout.write(f'      📡 {len(items)} items from {feed_url}')
        return items

    # ── article parser ────────────────────────────────────────

    def _parse_article(self, session, url, fallback_cat='Sports'):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
        except Exception as e:
            self.stdout.write(f'      ❌ Fetch error: {e}')
            return None

        soup = BeautifulSoup(r.text, 'html.parser')

        # Title
        og    = soup.find('meta', property='og:title')
        title = og['content'].strip() if og and og.get('content') else ''
        if not title:
            h1    = soup.find('h1')
            title = h1.get_text(strip=True) if h1 else ''
        title = re.sub(r'\s*[|\-–]\s*(Sun|Sporting Sun|TheSun).*$', '', title, flags=re.I).strip()
        if not title or title.startswith('http'):
            return None

        # Category from meta
        meta_cat = fallback_cat
        sec = soup.find('meta', property='article:section')
        if sec:
            meta_cat = sec.get('content', fallback_cat).strip()

        cat_name = self._detect_sports_category(title, url, meta_cat)

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
        content = re.sub(r'sunsports\s+reports[.,]?\s*', '', content, flags=re.I)
        if len(content) < 80:
            return None

        # Image
        image_url = ''
        og_img = soup.find('meta', property='og:image')
        if og_img:
            image_url = og_img.get('content', '')
        if not image_url and content_div:
            img = content_div.find('img')
            if img:
                image_url = img.get('src') or img.get('data-src', '')

        # Author
        author = 'Sporting Sun'
        for sel in [('a', {'rel': 'author'}), ('span', {'class': 'author'}),
                    ('span', {'class': 'by-author'})]:
            el = soup.find(sel[0], sel[1])
            if el:
                text = re.sub(r'^by\s+', '', el.get_text(strip=True), flags=re.I).strip()
                if text:
                    author = text
                    break

        # Date (None if not found — caller falls back to RSS pubDate)
        pub_date = None
        for sel in [('time', {'class': 'entry-date'}), ('time', {}),
                    ('meta', {'property': 'article:published_time'})]:
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
        # Windows consoles default to cp1252, which crashes on the emoji below
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

        max_pages   = options['max_pages']
        default_cat = options['default_category']

        # max_pages * 10 = max items per feed (5 pages × 10 = 50)
        max_items = max_pages * 10

        scraper_user, _ = User.objects.get_or_create(
            username='sportingsun_scraper',
            defaults={'email': 'scraper@sportingsun.ng',
                      'first_name': 'Sporting Sun', 'last_name': 'Scraper'}
        )
        default_category = self._get_or_create_category(default_cat)
        session          = self._session()

        self.stdout.write(self.style.SUCCESS(
            f'🚀 Sporting Sun scraper | RSS mode | up to {max_items} items per feed'
        ))

        total_scraped = total_skipped = 0
        seen_urls     = set()

        for feed_label, feed_url in RSS_FEEDS:
            self.stdout.write(f'\n\n{"═"*55}')
            self.stdout.write(f'📡  Feed: {feed_label}  ({feed_url})')
            self.stdout.write(f'{"═"*55}')

            rss_items = self._items_from_rss(session, feed_url, max_items)
            if not rss_items:
                self.stdout.write(f'   ⚠️  No items — skipping feed.')
                continue

            for item in rss_items:
                url = item['url'].strip()
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                self.stdout.write(f'\n   🔗 {url[:80]}')

                if News.objects.filter(title=item['title']).exists():
                    self.stdout.write('      ⏭️  Already exists — skipping')
                    total_skipped += 1
                    continue

                time.sleep(1)

                # Parse pub date from RSS
                rss_pub = None
                try:
                    rss_pub = dateparser.parse(item['pub'])
                except Exception:
                    pass

                data = self._parse_article(session, url, fallback_cat=item.get('cat', 'Sports'))
                if not data:
                    self.stdout.write('      ⚠️  Could not parse — skipping')
                    continue

                # Use RSS pub date if article page had none
                data['pub_date'] = data['pub_date'] or rss_pub or timezone.now()

                if News.objects.filter(title=data['title']).exists():
                    self.stdout.write('      ⏭️  Already exists — skipping')
                    total_skipped += 1
                    continue

                category    = self._get_or_create_category(data['cat_name'])
                is_featured = category.name in FEATURED_CATS

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
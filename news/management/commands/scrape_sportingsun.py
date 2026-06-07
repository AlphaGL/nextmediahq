# news/management/commands/scrape_sportingsun.py
"""
Scrapes thesun.ng (Sporting Sun) via HTML scraping.

Their WP REST API blocks GitHub Actions IPs with 403.
Strategy:
  1. Fetch category listing pages (HTML) for sports sections
  2. Extract article links from each page
  3. Fetch + parse each article for content, image, author, date
  4. Save to DB, skip duplicates

Listing URLs tried (in order):
  https://thesun.ng/sports/
  https://thesun.ng/sports/page/N/
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
    'Referer': 'https://www.google.com/',
}

BASE_URL = 'https://thesun.ng'

# Category pages to crawl — each is a separate sports section
CATEGORY_PAGES = [
    ('Sports',            '/sports/'),
    ('Football',          '/sports/football/'),
    ('EPL',               '/sports/football/english-premier-league/'),
    ('Transfer News',     '/sports/football/transfer-news/'),
    ('Basketball',        '/sports/basketball/'),
    ('Boxing',            '/sports/boxing/'),
]

FEATURED_CATS = {'Football', 'EPL', 'Transfer News', 'Champions League', 'Sports'}


class Command(BaseCommand):
    help = 'Scrape sports news from Sporting Sun (HTML scraping)'

    def add_arguments(self, parser):
        parser.add_argument('--max-pages', type=int, default=5,
                            help='Max listing pages per category (default: 5)')
        parser.add_argument('--start-page', type=int, default=1)
        parser.add_argument('--default-category', type=str, default='sports')

    # ── helpers ───────────────────────────────────────────────

    def _session(self):
        s = requests.Session()
        s.headers.update(HEADERS)
        return s

    def _get_or_create_category(self, name):
        name = (name or 'Sports').strip().title()
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

    # ── listing page ─────────────────────────────────────────

    def _article_links_from_listing(self, session, cat_path, page):
        url = BASE_URL + cat_path if page == 1 else f'{BASE_URL}{cat_path}page/{page}/'
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 404:
                return None     # no more pages
            r.raise_for_status()
        except Exception as e:
            self.stdout.write(f'      ❌ Listing error ({url}): {e}')
            return []

        soup  = BeautifulSoup(r.text, 'html.parser')
        links = set()

        # Strategy 1: <h2>/<h3> with title-like class containing a link
        for tag in soup.find_all(['h2', 'h3'], class_=re.compile(r'(entry|post)-title', re.I)):
            a = tag.find('a', href=True)
            if a:
                links.add(urljoin(BASE_URL, a['href']))

        # Strategy 2: links inside <article> tags
        if not links:
            for art in soup.find_all('article'):
                a = art.find('a', href=True)
                if a and 'thesun.ng' in urljoin(BASE_URL, a['href']):
                    links.add(urljoin(BASE_URL, a['href']))

        # Strategy 3: any thesun.ng link that looks like an article slug
        if not links:
            for a in soup.find_all('a', href=True):
                href = urljoin(BASE_URL, a['href'])
                # article slugs: thesun.ng/<slug>/ or thesun.ng/<cat>/<slug>/
                if re.match(r'https://thesun\.ng/[^/]+/[^/]+/$', href):
                    links.add(href)

        self.stdout.write(f'      📋 Page {page}: {len(links)} links')
        return list(links)

    # ── article parser ────────────────────────────────────────

    def _parse_article(self, session, url):
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
        if not title:
            return None

        # Category from meta
        cat_name = 'Sports'
        sec = soup.find('meta', property='article:section')
        if sec:
            cat_name = sec.get('content', 'Sports').strip()
        else:
            # try breadcrumb
            bc = soup.find(class_=re.compile(r'breadcrumb', re.I))
            if bc:
                links = bc.find_all('a')
                if len(links) > 1:
                    cat_name = links[-1].get_text(strip=True) or cat_name

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
        # Remove "sunsports reports" filler
        content = re.sub(r'sunsports\s+reports[.,]?\s*', '', content, flags=re.I)
        if len(content) < 80:
            return None

        # Image
        image_url = ''
        og_img = soup.find('meta', property='og:image')
        if og_img:
            image_url = og_img.get('content', '')
        if not image_url:
            img = content_div.find('img')
            if img:
                image_url = img.get('src') or img.get('data-src', '')

        # Author
        author = 'Sporting Sun'
        for sel in [('a', {'rel': 'author'}), ('span', {'class': 'author'}),
                    ('span', {'class': 'by-author'})]:
            el = soup.find(sel[0], sel[1])
            if el:
                author = re.sub(r'^by\s+', '', el.get_text(strip=True), flags=re.I).strip() or author
                break

        # Date
        pub_date = timezone.now()
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
        max_pages   = options['max_pages']
        start_page  = options['start_page']
        default_cat = options['default_category']

        scraper_user, _ = User.objects.get_or_create(
            username='sportingsun_scraper',
            defaults={'email': 'scraper@sportingsun.ng',
                      'first_name': 'Sporting Sun', 'last_name': 'Scraper'}
        )
        default_category = self._get_or_create_category(default_cat)
        session          = self._session()

        self.stdout.write(self.style.SUCCESS(
            f'🚀 Sporting Sun scraper | pages {start_page}–{start_page + max_pages - 1} per category'
        ))

        total_scraped = total_skipped = 0
        seen_urls     = set()

        for cat_label, cat_path in CATEGORY_PAGES:
            self.stdout.write(f'\n\n{"═"*55}')
            self.stdout.write(f'📂  Category: {cat_label}  ({BASE_URL + cat_path})')
            self.stdout.write(f'{"═"*55}')

            for page in range(start_page, start_page + max_pages):
                links = self._article_links_from_listing(session, cat_path, page)
                if links is None:
                    self.stdout.write(f'   ✅ No more pages for {cat_label}.')
                    break
                if not links:
                    break

                for url in links:
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    self.stdout.write(f'\n   🔗 {url[:80]}')
                    time.sleep(1)

                    data = self._parse_article(session, url)
                    if not data:
                        self.stdout.write('      ⚠️  Could not parse — skipping')
                        continue

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

                time.sleep(2)

        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 Done — scraped: {total_scraped} | skipped: {total_skipped}'
        ))
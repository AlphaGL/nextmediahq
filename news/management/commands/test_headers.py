import requests

variants = [
    ('No Accept header', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }),
    ('Browser Accept', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }),
    ('Feedburner UA', {
        'User-Agent': 'FeedBurner/1.0 (http://www.FeedBurner.com)'
    }),
    ('curl UA', {
        'User-Agent': 'curl/7.68.0',
        'Accept': '*/*'
    }),
    ('Full browser headers', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }),
]

urls = [
    'https://sportingsun.ng/feed/',
    'https://sportingsun.ng/wp-json/wp/v2/posts?per_page=2',
]

for url in urls:
    print(f"\n{'='*60}")
    print(f"Testing URL: {url}")
    print('='*60)
    for name, h in variants:
        try:
            r = requests.get(url, headers=h, timeout=15)
            ct = r.headers.get('Content-Type', '?')
            body = r.text[:200].replace('\n', ' ')
            print(f"  [{name}]")
            print(f"    Status : {r.status_code}")
            print(f"    C-Type : {ct}")
            print(f"    Body   : {body}")
            print()
        except Exception as e:
            print(f"  [{name}] ERROR: {e}\n")
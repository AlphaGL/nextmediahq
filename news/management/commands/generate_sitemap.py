# news/management/commands/generate_sitemap.py
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse
from news.models import News, School, Category
import os

class Command(BaseCommand):
    help = 'Generate sitemap for NextMedia'

    def handle(self, *args, **options):
        sitemap_content = ['<?xml version="1.0" encoding="UTF-8"?>']
        sitemap_content.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        
        base_url = 'https://yourdomain.com'  # Change this to your actual domain
        
        # Add homepage
        sitemap_content.append(f'''
        <url>
            <loc>{base_url}/</loc>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>''')
        
        # Add school pages
        for school in School.objects.filter(is_active=True):
            sitemap_content.append(f'''
        <url>
            <loc>{base_url}{reverse('news:school_news', kwargs={'slug': school.slug})}</loc>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>''')
        
        # Add category pages
        for category in Category.objects.filter(is_active=True):
            sitemap_content.append(f'''
        <url>
            <loc>{base_url}{reverse('news:category_news', kwargs={'slug': category.slug})}</loc>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>''')
        
        # Add news articles
        for news in News.objects.filter(is_published=True):
            sitemap_content.append(f'''
        <url>
            <loc>{base_url}{news.get_absolute_url()}</loc>
            <lastmod>{news.updated_at.strftime('%Y-%m-%d')}</lastmod>
            <changefreq>monthly</changefreq>
            <priority>0.6</priority>
        </url>''')
        
        sitemap_content.append('</urlset>')
        
        # Write sitemap to file
        sitemap_path = os.path.join(settings.BASE_DIR, 'sitemap.xml')
        with open(sitemap_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sitemap_content))
        
        self.stdout.write(
            self.style.SUCCESS(f'Sitemap generated at {sitemap_path}')
        )
# news/management/commands/cleanup_old_news.py
from django.core.management.base import BaseCommand
from news.models import News
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Cleanup old unpublished news articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete unpublished news older than this many days'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_news = News.objects.filter(
            is_published=False,
            created_at__lt=cutoff_date
        )
        
        count = old_news.count()
        
        if dry_run:
            self.stdout.write(f'Would delete {count} old unpublished news articles')
            for news in old_news:
                self.stdout.write(f'  - {news.title} (created: {news.created_at})')
        else:
            deleted_count, _ = old_news.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} old unpublished news articles')
            )
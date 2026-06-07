# news/tasks.py
"""
Celery tasks that wrap the two scraper management commands.
Both tasks run every 3 hours via Celery Beat (configured in settings.py).
"""

from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task(
    name='news.tasks.run_punch_scraper',
    bind=True,
    max_retries=2,
    default_retry_delay=120,   # retry after 2 minutes on failure
    time_limit=1800,           # hard kill after 30 min
    soft_time_limit=1500,      # SoftTimeLimitExceeded after 25 min
)
def run_punch_scraper(self):
    """
    Runs: python manage.py scrape_punch --max-pages 3
    Scheduled every 3 hours by Celery Beat.
    """
    logger.info('⏰ [Celery] Starting Punch scraper task…')
    try:
        call_command('scrape_punch', max_pages=3)
        logger.info('✅ [Celery] Punch scraper finished successfully.')
    except Exception as exc:
        logger.error(f'❌ [Celery] Punch scraper failed: {exc}', exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    name='news.tasks.run_sportingsun_scraper',
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    time_limit=1800,
    soft_time_limit=1500,
)
def run_sportingsun_scraper(self):
    """
    Runs: python manage.py scrape_sportingsun --max-pages 3
    Scheduled every 3 hours by Celery Beat.
    """
    logger.info('⏰ [Celery] Starting Sporting Sun scraper task…')
    try:
        call_command('scrape_sportingsun', max_pages=3)
        logger.info('✅ [Celery] Sporting Sun scraper finished successfully.')
    except Exception as exc:
        logger.error(f'❌ [Celery] Sporting Sun scraper failed: {exc}', exc_info=True)
        raise self.retry(exc=exc)
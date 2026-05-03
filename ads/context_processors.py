# ads/context_processors.py
from datetime import datetime
from .models import Advertisement


def active_ads(request):
    """
    Inject live ads into every template context so that include tags
    in base.html can render the header/body/footer banners automatically.
    """
    now = datetime.now()
    live = Advertisement.objects.filter(
        status='approved',
        expires_at__gt=now,
    ).select_related('slot')

    return {
        'header_ads': live.filter(slot__position='header'),
        'body_ads':   live.filter(slot__position='body'),
        'footer_ads': live.filter(slot__position='footer'),
    }
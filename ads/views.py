# ads/views.py
import logging
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Advertisement, AdImpression, AdClick

logger = logging.getLogger(__name__)


# ── Analytics tracking (called via JS from ad templates) ──────────────────────

@csrf_exempt
def track_impression(request, ad_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    try:
        ad = Advertisement.objects.get(
            id=ad_id,
            status='approved',
            expires_at__gt=datetime.now(),
        )
        ip = request.META.get('REMOTE_ADDR')
        AdImpression.objects.create(advertisement=ad, ip_address=ip)
        ad.impressions += 1
        ad.save(update_fields=['impressions'])
    except Advertisement.DoesNotExist:
        pass
    return JsonResponse({'ok': True})


@csrf_exempt
def track_click(request, ad_id):
    if request.method != 'POST':
        return JsonResponse({'url': '#'}, status=405)
    try:
        ad = Advertisement.objects.get(
            id=ad_id,
            status='approved',
            expires_at__gt=datetime.now(),
        )
        ip = request.META.get('REMOTE_ADDR')
        AdClick.objects.create(advertisement=ad, ip_address=ip)
        ad.clicks += 1
        ad.save(update_fields=['clicks'])
        return JsonResponse({'url': ad.destination_url})
    except Advertisement.DoesNotExist:
        pass
    return JsonResponse({'url': '#'})
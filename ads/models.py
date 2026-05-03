# ads/models.py
from django.db import models
from datetime import datetime, timedelta
import uuid


class AdSlot(models.Model):
    POSITION_CHOICES = [
        ('header', 'Header Banner'),
        ('body', 'Body Banner'),
        ('footer', 'Footer Banner'),
    ]

    position = models.CharField(max_length=20, choices=POSITION_CHOICES, unique=True)
    max_advertisers = models.IntegerField(default=5)
    duration_days = models.IntegerField(default=30, help_text='How long one ad booking lasts (days)')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.get_position_display()

    def active_ad_count(self):
        return Advertisement.objects.filter(
            slot=self,
            status='approved',
            expires_at__gt=datetime.now(),
        ).count()

    def is_full(self):
        return self.active_ad_count() >= self.max_advertisers

    def slots_remaining(self):
        return max(0, self.max_advertisers - self.active_ad_count())

    class Meta:
        ordering = ['position']


class Advertisement(models.Model):
    STATUS_CHOICES = [
        ('approved', 'Approved — Live'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
    ]

    AD_FORMAT_CHOICES = [
        ('image', 'Image Banner'),
        ('text', 'Text Ad'),
        ('image_text', 'Image + Text'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slot = models.ForeignKey(AdSlot, on_delete=models.CASCADE, related_name='advertisements')

    # Ad content
    advertiser_name = models.CharField(max_length=200, help_text='Business / brand name shown on the ad')
    title = models.CharField(max_length=100, help_text='Ad headline (max 100 chars)')
    description = models.TextField(max_length=300, blank=True, help_text='Short description (max 300 chars)')

    image = models.ImageField(
        upload_to='ads/banners/',
        blank=True,
        null=True,
        help_text='Upload your banner image (JPG/PNG, max 2MB)',
    )
    image_url = models.URLField(blank=True, null=True, help_text='Auto-filled from uploaded image')
    cloudinary_public_id = models.CharField(max_length=255, blank=True, null=True)

    cta_text = models.CharField(max_length=50, default='Learn More', help_text='Call-to-action button text')
    destination_url = models.URLField(help_text='Where to send visitors when they click the ad')
    ad_format = models.CharField(max_length=20, choices=AD_FORMAT_CHOICES, default='image_text')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    admin_notes = models.TextField(blank=True, help_text='Internal notes (not shown publicly)')

    # Timing — naive datetimes to match USE_TZ = False in settings
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Analytics
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} [{self.slot.get_position_display()}] — {self.get_status_display()}"

    def get_image_url(self):
        """Return the best available image URL (uploaded file > stored URL)."""
        if self.image:
            return self.image.url
        return self.image_url or ''

    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round((self.clicks / self.impressions) * 100, 2)

    def is_live(self):
        return (
            self.status == 'approved'
            and self.expires_at is not None
            and datetime.now() < self.expires_at
        )

    def days_remaining(self):
        if self.expires_at and self.is_live():
            delta = self.expires_at - datetime.now()
            return max(0, delta.days)
        return 0

    def performance_rating(self):
        ctr = self.ctr()
        if ctr >= 5:
            return 'excellent'
        elif ctr >= 2:
            return 'good'
        elif ctr >= 0.5:
            return 'average'
        return 'poor'

    def save(self, *args, **kwargs):
        """
        Auto-set approved_at and expires_at whenever status is 'approved'
        and those fields are missing or stale.
        """
        now = datetime.now()

        if self.status == 'approved':
            if not self.approved_at:
                self.approved_at = now
            if not self.expires_at or self.expires_at <= now:
                self.expires_at = self.approved_at + timedelta(days=self.slot.duration_days)

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']


class AdImpression(models.Model):
    advertisement = models.ForeignKey(
        Advertisement, on_delete=models.CASCADE, related_name='impression_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class AdClick(models.Model):
    advertisement = models.ForeignKey(
        Advertisement, on_delete=models.CASCADE, related_name='click_logs'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
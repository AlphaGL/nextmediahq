# ads/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import AdSlot, Advertisement, AdImpression, AdClick


# ─────────────────────────────────────────────
# AdSlot
# ─────────────────────────────────────────────
@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ('position', 'max_advertisers', 'active_ad_count', 'slots_remaining', 'duration_days', 'is_active')
    list_filter = ('is_active', 'position')
    readonly_fields = ('active_ad_count_display', 'slots_remaining_display', 'is_full_display')

    fieldsets = (
        ('Slot Details', {
            'fields': ('position', 'description', 'is_active'),
        }),
        ('Limits & Duration', {
            'fields': ('max_advertisers', 'duration_days'),
        }),
        ('Live Stats (read-only)', {
            'fields': ('active_ad_count_display', 'slots_remaining_display', 'is_full_display'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Active Ads')
    def active_ad_count(self, obj):
        return obj.active_ad_count()

    @admin.display(description='Slots Remaining')
    def slots_remaining(self, obj):
        return obj.slots_remaining()

    @admin.display(description='Active Ads')
    def active_ad_count_display(self, obj):
        return obj.active_ad_count()

    @admin.display(description='Slots Remaining')
    def slots_remaining_display(self, obj):
        return obj.slots_remaining()

    @admin.display(description='Full?', boolean=True)
    def is_full_display(self, obj):
        return obj.is_full()


# ─────────────────────────────────────────────
# Advertisement
# ─────────────────────────────────────────────
@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'advertiser_name', 'slot', 'ad_format', 'status',
        'impressions', 'clicks', 'ctr_display', 'is_live_display', 'expires_at',
    )
    list_filter = ('status', 'ad_format', 'slot__position')
    search_fields = ('title', 'advertiser_name', 'destination_url')
    readonly_fields = (
        'id', 'impressions', 'clicks', 'ctr_display',
        'is_live_display', 'days_remaining_display', 'performance_rating_display',
        'created_at', 'approved_at', 'expires_at',
    )
    actions = ['pause_ads', 'resume_ads']

    fieldsets = (
        ('Ad Identity', {
            'fields': ('id', 'slot', 'ad_format', 'status'),
        }),
        ('Advertiser', {
            'fields': ('advertiser_name',),
        }),
        ('Ad Content', {
            'fields': ('title', 'description', 'image', 'image_url', 'cloudinary_public_id', 'cta_text', 'destination_url'),
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
        }),
        ('Analytics (read-only)', {
            'fields': ('impressions', 'clicks', 'ctr_display', 'performance_rating_display'),
            'classes': ('collapse',),
        }),
        ('Timing (read-only)', {
            'fields': ('created_at', 'approved_at', 'expires_at', 'days_remaining_display', 'is_live_display'),
            'classes': ('collapse',),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # expires_at and approved_at are auto-set by model.save()
        return self.readonly_fields

    @admin.display(description='CTR (%)')
    def ctr_display(self, obj):
        return f"{obj.ctr()}%"

    @admin.display(description='Live?', boolean=True)
    def is_live_display(self, obj):
        return obj.is_live()

    @admin.display(description='Days Left')
    def days_remaining_display(self, obj):
        return obj.days_remaining()

    @admin.display(description='Performance')
    def performance_rating_display(self, obj):
        return obj.performance_rating()

    @admin.action(description='⏸ Pause selected ads')
    def pause_ads(self, request, queryset):
        updated = queryset.filter(status='approved').update(status='paused')
        self.message_user(request, f"{updated} ad(s) paused.")

    @admin.action(description='▶ Resume selected ads (set back to Approved)')
    def resume_ads(self, request, queryset):
        updated = 0
        for ad in queryset.filter(status='paused'):
            ad.status = 'approved'
            ad.save()  # model.save() auto-fixes expires_at if needed
            updated += 1
        self.message_user(request, f"{updated} ad(s) resumed and are now live.")

    def save_model(self, request, obj, form, change):
        """
        When an admin saves a new ad with status='approved',
        the model's save() method auto-sets approved_at and expires_at.
        """
        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────────
# AdImpression & AdClick (read-only logs)
# ─────────────────────────────────────────────
@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    list_display = ('advertisement', 'ip_address', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('advertisement__title', 'ip_address')
    readonly_fields = ('advertisement', 'ip_address', 'timestamp')

    def has_add_permission(self, request):
        return False


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ('advertisement', 'ip_address', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('advertisement__title', 'ip_address')
    readonly_fields = ('advertisement', 'ip_address', 'timestamp')

    def has_add_permission(self, request):
        return False
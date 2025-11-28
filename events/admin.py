# events/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from .models import (
    EventCategory, Event, VotingContestant, Vote, EventRSVP
)


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active', 'event_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    def event_count(self, obj):
        count = obj.event_set.count()
        return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', count)
    event_count.short_description = 'Events'


class VotingContestantInline(admin.TabularInline):
    model = VotingContestant
    extra = 1
    fields = ['contestant_number', 'name', 'total_votes', 'total_amount_received', 'is_active']
    readonly_fields = ['total_votes', 'total_amount_received']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'school', 'category', 'status', 'start_date', 
        'banner_preview', 'is_featured', 'is_trending', 
        'total_votes_count', 'voting_revenue', 'views_count'
    ]
    list_filter = ['status', 'is_featured', 'is_trending', 'category', 'school', 'start_date']
    search_fields = ['title', 'description', 'venue']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_featured', 'is_trending', 'status']
    readonly_fields = ['banner_preview', 'views_count', 'created_at', 'updated_at', 'total_votes_count', 'voting_revenue']
    date_hierarchy = 'start_date'
    inlines = [VotingContestantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'short_description')
        }),
        ('Media', {
            'fields': ('banner_image', 'banner_preview', 'gallery_images')
        }),
        ('Classification', {
            'fields': ('category', 'school')
        }),
        ('Date & Time', {
            'fields': ('start_date', 'end_date')
        }),
        ('Location', {
            'fields': ('venue', 'address', 'map_link')
        }),
        ('Voting Features', {
            'fields': ('allow_voting', 'voting_price_per_vote', 'voting_ends_at')
        }),
        ('Status', {
            'fields': ('status', 'is_featured', 'is_trending')
        }),
        ('Statistics', {
            'fields': ('views_count', 'total_votes_count', 'voting_revenue'),
            'classes': ['collapse']
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    def banner_preview(self, obj):
        if obj.banner_image:
            return format_html(
                '<img src="{}" width="150" height="90" style="border-radius: 5px; object-fit: cover;" />',
                obj.banner_image.url
            )
        return mark_safe('<span style="color: #999;">No Banner</span>')
    banner_preview.short_description = 'Banner Preview'
    
    def total_votes_count(self, obj):
        count = obj.total_votes
        if count > 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: #dc3545;">0</span>')
    total_votes_count.short_description = 'Total Votes'
    
    def voting_revenue(self, obj):
        total = obj.total_voting_revenue
        if total > 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">₦{}</span>', f'{float(total):,.2f}')
        return format_html('<span style="color: #999;">₦0.00</span>')
    voting_revenue.short_description = 'Voting Revenue'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VotingContestant)
class VotingContestantAdmin(admin.ModelAdmin):
    list_display = [
        'contestant_number', 'name', 'event', 'photo_preview', 
        'total_votes', 'total_amount_received', 'is_active'
    ]
    list_filter = ['is_active', 'event', 'created_at']
    search_fields = ['name', 'event__title']
    list_editable = ['is_active']
    readonly_fields = ['photo_preview', 'total_votes', 'total_amount_received']
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 25px; object-fit: cover;" />',
                obj.photo.url
            )
        return mark_safe('<span style="color: #999;">No Photo</span>')
    photo_preview.short_description = 'Photo'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'voter_name', 'contestant', 'event', 
        'votes_count', 'amount_paid', 'payment_status', 'created_at'
    ]
    list_filter = ['payment_status', 'event', 'created_at']
    search_fields = ['reference', 'voter_name', 'voter_email', 'paystack_reference']
    readonly_fields = ['reference', 'votes_count', 'created_at', 'paid_at']
    list_per_page = 50
    
    fieldsets = (
        ('Vote Information', {
            'fields': ('reference', 'event', 'contestant', 'votes_count', 'amount_paid')
        }),
        ('Voter Details', {
            'fields': ('voter_name', 'voter_email', 'voter_phone', 'user')
        }),
        ('Payment', {
            'fields': ('payment_status', 'paystack_reference', 'paid_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


@admin.register(EventRSVP)
class EventRSVPAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'event', 'created_at']
    list_filter = ['event', 'created_at']
    search_fields = ['name', 'email', 'phone', 'event__title']
    readonly_fields = ['created_at']


# Admin site customization
admin.site.site_header = "NextMedia Events Administration"
admin.site.index_title = "Events Management"
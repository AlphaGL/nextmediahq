# news/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import School, Category, News, PastQuestion

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'logo_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'established']
    search_fields = ['name', 'abbreviation', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    readonly_fields = ['logo_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'abbreviation', 'slug', 'description')
        }),
        ('Visual & Links', {
            'fields': ('logo', 'logo_preview', 'website')
        }),
        ('Details', {
            'fields': ('established', 'is_active')
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 25px; object-fit: cover;" />',
                obj.logo.url
            )
        return mark_safe('<span style="color: #999;">No Logo</span>')
    logo_preview.short_description = 'Logo Preview'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'news_count']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    def news_count(self, obj):
        count = obj.news_set.count()
        if count > 0:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: #dc3545;">0</span>')
    news_count.short_description = 'News Count'

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'school', 'category', 'author_display', 'image_preview', 'is_featured', 'is_published', 'published_date']
    list_filter = ['school', 'category', 'is_featured', 'is_published', 'published_date', 'published_by']
    search_fields = ['title', 'content', 'excerpt', 'author']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_featured', 'is_published']
    date_hierarchy = 'published_date'
    readonly_fields = ['image_preview', 'created_at', 'updated_at']
    raw_id_fields = ['published_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'excerpt')
        }),
        ('Content', {
            'fields': ('content', 'featured_image', 'featured_image_url', 'image_preview')
        }),
        ('Classification', {
            'fields': ('school', 'category')
        }),
        ('Author Information', {
            'fields': ('author', 'published_by')
        }),
        ('Publication Settings', {
            'fields': ('is_featured', 'is_published', 'published_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    def image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="100" height="60" style="border-radius: 5px; object-fit: cover;" />',
                obj.featured_image.url
            )
        elif obj.featured_image_url:
            return format_html(
                '<img src="{}" width="100" height="60" style="border-radius: 5px; object-fit: cover;" />',
                obj.featured_image_url
            )
        return mark_safe('<span style="color: #999;">No Image</span>')
    image_preview.short_description = 'Featured Image'

    def author_display(self, obj):
        if obj.author:
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', obj.author)
        else:
            user = obj.published_by
            display_name = user.get_full_name() or user.username
            return format_html('<span style="color: #6c757d;">@{}</span>', display_name)
    author_display.short_description = 'Author'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.published_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(PastQuestion)
class PastQuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'school', 'subject', 'year_range', 'cover_preview', 'created_at']
    list_filter = ['school', 'subject', 'start_year', 'end_year', 'created_at']
    search_fields = ['title', 'subject', 'school__name', 'description']
    readonly_fields = ['cover_preview', 'created_at']
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'school', 'subject')
        }),
        ('Academic Details', {
            'fields': ('start_year', 'end_year', 'description')
        }),
        ('Media & Links', {
            'fields': ('cover_image', 'cover_preview', 'link')
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        }),
    )
    
    def year_range(self, obj):
        if obj.start_year == obj.end_year:
            return format_html('<span style="font-weight: bold;">{}</span>', obj.start_year)
        else:
            return format_html(
                '<span style="font-weight: bold;">{} - {}</span>', 
                obj.start_year, obj.end_year
            )
    year_range.short_description = 'Year(s)'
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="80" height="60" style="border-radius: 5px; object-fit: cover;" />',
                obj.cover_image.url
            )
        return mark_safe('<span style="color: #999;">No Cover Image</span>')
    cover_preview.short_description = 'Cover Preview'

# Admin site customization
admin.site.site_header = "NextMedia Administration"
admin.site.site_title = "NextMedia Admin"
admin.site.index_title = "Welcome to NextMedia Administration"
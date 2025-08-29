# news/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import School, Category, News, PastQuestion

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'abbreviation']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 25px;" />'.format(obj.logo.url))
        return "No Logo"
    logo_preview.short_description = 'Logo'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'school', 'category', 'is_featured', 'is_published', 'published_date']
    list_filter = ['school', 'category', 'is_featured', 'is_published', 'published_date']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['is_featured', 'is_published']
    date_hierarchy = 'published_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'excerpt')
        }),
        ('Content', {
            'fields': ('content', 'featured_image')
        }),
        ('Classification', {
            'fields': ('school', 'category')
        }),
        ('Publication', {
            'fields': ('is_featured', 'is_published', 'published_date')
        }),
    )
    
    def image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" width="100" height="60" style="border-radius: 5px;" />'.format(obj.featured_image.url))
        return "No Image"
    image_preview.short_description = 'Preview'

@admin.register(PastQuestion)
class PastQuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'school', 'subject', 'year']
    list_filter = ['school', 'year', 'subject']
    search_fields = ['title', 'subject', 'school__name']
    
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields
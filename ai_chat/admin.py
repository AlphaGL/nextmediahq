# ai_chat/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ChatSession, ChatMessage, ConversationContext

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id_short', 'created_at', 'last_activity', 'message_count', 'is_active', 'duration']
    list_filter = ['is_active', 'created_at', 'last_activity']
    search_fields = ['session_id']
    readonly_fields = ['session_id', 'created_at', 'last_activity']
    date_hierarchy = 'created_at'
    
    def session_id_short(self, obj):
        return format_html(
            '<span style="font-family: monospace; color: #2196F3;">{}</span>',
            str(obj.session_id)[:8]
        )
    session_id_short.short_description = 'Session ID'
    
    def message_count(self, obj):
        count = obj.messages.count()
        color = '#4CAF50' if count > 0 else '#999'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, count
        )
    message_count.short_description = 'Messages'
    
    def duration(self, obj):
        delta = obj.last_activity - obj.created_at
        minutes = delta.total_seconds() / 60
        if minutes < 1:
            return format_html('<span style="color: #999;">< 1 min</span>')
        elif minutes < 60:
            return format_html('<span style="color: #2196F3;">{:.0f} min</span>', minutes)
        else:
            hours = minutes / 60
            return format_html('<span style="color: #FF9800;">{:.1f} hrs</span>', hours)
    duration.short_description = 'Duration'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_short', 'message_type_badge', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content', 'session__session_id']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def session_short(self, obj):
        return format_html(
            '<span style="font-family: monospace; font-size: 0.85em;">{}</span>',
            str(obj.session.session_id)[:8]
        )
    session_short.short_description = 'Session'
    
    def message_type_badge(self, obj):
        colors = {
            'user': '#2196F3',
            'ai': '#4CAF50',
            'system': '#FF9800'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold;">{}</span>',
            colors.get(obj.message_type, '#999'),
            obj.message_type.upper()
        )
    message_type_badge.short_description = 'Type'
    
    def content_preview(self, obj):
        preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return format_html('<span style="color: #555;">{}</span>', preview)
    content_preview.short_description = 'Content'

@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_short', 'context_keys', 'updated_at']
    readonly_fields = ['updated_at']
    
    def session_short(self, obj):
        return format_html(
            '<span style="font-family: monospace; font-size: 0.85em;">{}</span>',
            str(obj.session.session_id)[:8]
        )
    session_short.short_description = 'Session'
    
    def context_keys(self, obj):
        keys = list(obj.context_data.keys()) if obj.context_data else []
        if not keys:
            return format_html('<span style="color: #999;">No data</span>')
        return format_html(
            '<span style="color: #2196F3;">{}</span>',
            ', '.join(keys[:5])
        )
    context_keys.short_description = 'Context Keys'

# Customize admin site
admin.site.site_header = "Next AI Chat Administration"
admin.site.site_title = "Next AI Admin"
admin.site.index_title = "Manage AI Chat Sessions"
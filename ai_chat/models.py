# ai_chat/models.py
from django.db import models
from django.utils import timezone
import uuid

class ChatSession(models.Model):
    """Store chat sessions for tracking conversations"""
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['-last_activity']),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class ChatMessage(models.Model):
    """Store individual chat messages"""
    MESSAGE_TYPES = (
        ('user', 'User'),
        ('ai', 'AI'),
        ('system', 'System'),
    )
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.message_type} - {self.content[:50]}..."

class ConversationContext(models.Model):
    """Store conversation context for better AI responses"""
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='context')
    context_data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Context for {self.session.session_id}"
# ai_chat/urls.py
from django.urls import path
from . import views

app_name = 'ai_chat'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    path('history/<uuid:session_id>/', views.get_chat_history, name='get_history'),
    path('clear/', views.clear_chat, name='clear_chat'),
    path('cleanup/', views.cleanup_old_sessions, name='cleanup'),
]
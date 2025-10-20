# ai_chat/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ChatSession, ChatMessage, ConversationContext
from .ai_service import EnhancedAIService
import json
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Initialize enhanced AI service
ai_service = EnhancedAIService()
logger.info("Enhanced AI service initialized")

def chat_view(request):
    """Main chat interface view"""
    return render(request, 'ai_chat/chat.html')

@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Handle incoming chat messages and return AI responses"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(session_id=session_id, is_active=True)
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create()
        else:
            session = ChatSession.objects.create()
        
        # Save user message
        ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=user_message
        )
        
        # Get conversation history (last 5 messages for context)
        previous_messages = list(
            ChatMessage.objects.filter(session=session)
            .order_by('-timestamp')[:5]
        )
        previous_messages.reverse()
        
        conversation_history = [
            {'role': msg.message_type, 'content': msg.content}
            for msg in previous_messages[:-1]  # Exclude current message
        ]
        
        logger.info(f"Session {session.session_id}: Processing message with {len(conversation_history)} history items")
        
        # Generate enhanced AI response
        ai_result = ai_service.generate_response(user_message, conversation_history)
        
        if ai_result['success']:
            ai_response = ai_result['message']
            logger.info(f"Response generated using context: {ai_result.get('context_used', [])}")
        else:
            ai_response = ai_result['message']
            logger.error(f"AI service error: {ai_result.get('error', 'Unknown error')}")
        
        # Save AI response
        ChatMessage.objects.create(
            session=session,
            message_type='ai',
            content=ai_response
        )
        
        # Update session activity
        session.last_activity = timezone.now()
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': ai_response,
            'session_id': str(session.session_id),
            'timestamp': timezone.now().isoformat(),
            'context_used': ai_result.get('context_used', [])
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON Error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_chat_history(request, session_id):
    """Retrieve chat history for a session"""
    try:
        session = ChatSession.objects.get(session_id=session_id, is_active=True)
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
        
        history = [{
            'type': msg.message_type,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]
        
        return JsonResponse({'success': True, 'history': history})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def clear_chat(request):
    """Clear chat history for a session"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)
        
        session = ChatSession.objects.get(session_id=session_id, is_active=True)
        ChatMessage.objects.filter(session=session).delete()
        new_session = ChatSession.objects.create()
        
        return JsonResponse({
            'success': True,
            'new_session_id': str(new_session.session_id),
            'message': 'Chat cleared successfully'
        })
    except ChatSession.DoesNotExist:
        new_session = ChatSession.objects.create()
        return JsonResponse({
            'success': True,
            'new_session_id': str(new_session.session_id),
            'message': 'New session created'
        })
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def cleanup_old_sessions(request):
    """Admin view to cleanup old inactive sessions"""
    cutoff_date = timezone.now() - timedelta(days=7)
    old_sessions = ChatSession.objects.filter(last_activity__lt=cutoff_date)
    count = old_sessions.count()
    old_sessions.delete()
    
    return JsonResponse({'success': True, 'deleted_sessions': count})
# events/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import json
import hmac
import hashlib
import requests

from .models import (
    Event, EventCategory, VotingContestant, Vote, EventRSVP
)
from news.models import School

# Import ticket models to check for ticket availability
try:
    from tickets.models import Event as TicketEvent
    TICKETS_APP_ENABLED = True
except ImportError:
    TICKETS_APP_ENABLED = False


def events_home(request):
    """Events homepage with featured, trending, and categorized events"""
    # Get featured events
    featured_events = Event.objects.filter(
        is_featured=True,
        status='upcoming'
    ).select_related('school', 'category')[:6]
    
    # Get trending events
    trending_events = Event.objects.filter(
        is_trending=True,
        status='upcoming'
    ).select_related('school', 'category')[:8]
    
    # Get upcoming events by category
    categories_with_events = []
    categories = EventCategory.objects.filter(is_active=True)
    
    for category in categories:
        category_events = Event.objects.filter(
            category=category,
            status='upcoming'
        ).select_related('school')[:8]
        
        if category_events.exists():
            categories_with_events.append({
                'category': category,
                'events': list(category_events)
            })
    
    # Get all schools with events
    schools = School.objects.filter(
        is_active=True,
        event__status='upcoming'
    ).distinct()[:12]
    
    context = {
        'featured_events': featured_events,
        'trending_events': trending_events,
        'categories_with_events': categories_with_events,
        'schools': schools,
    }
    return render(request, 'events/index.html', context)


def event_detail(request, slug):
    """Detailed event page with voting and ticket availability check"""
    event = get_object_or_404(Event, slug=slug)
    
    # Increment view count
    event.views_count += 1
    event.save(update_fields=['views_count'])
    
    # Get voting contestants if available
    contestants = None
    voting_active = False
    if event.allow_voting:
        contestants = event.contestants.filter(is_active=True).order_by('-total_votes')
        if event.voting_ends_at:
            voting_active = timezone.now() < event.voting_ends_at
        else:
            voting_active = event.status == 'upcoming' or event.is_live
    
    # Check if there's a matching ticket event
    ticket_event = None
    has_tickets = False
    
    if TICKETS_APP_ENABLED:
        try:
            # Try to find a matching ticket event by slug or similar title and date
            ticket_event = TicketEvent.objects.filter(
                Q(slug=event.slug) |
                Q(title__icontains=event.title[:30]) |
                Q(event_date__date=event.start_date.date(), venue__icontains=event.venue[:20]),
                is_active=True,
                status='upcoming'
            ).first()
            
            if ticket_event:
                has_tickets = not ticket_event.is_sold_out
        except Exception as e:
            print(f"Error checking tickets: {e}")
    
    # Get related events
    related_events = Event.objects.filter(
        category=event.category,
        status='upcoming'
    ).exclude(id=event.id).select_related('school', 'category')[:4]
    
    context = {
        'event': event,
        'contestants': contestants,
        'voting_active': voting_active,
        'related_events': related_events,
        'ticket_event': ticket_event,
        'has_tickets': has_tickets,
        'tickets_enabled': TICKETS_APP_ENABLED,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'events/event_detail.html', context)


def events_by_category(request, slug):
    """List events by category"""
    category = get_object_or_404(EventCategory, slug=slug, is_active=True)
    events_list = Event.objects.filter(
        category=category,
        status='upcoming'
    ).select_related('school')
    
    paginator = Paginator(events_list, 12)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'events': events,
    }
    return render(request, 'events/category_events.html', context)


def events_by_school(request, slug):
    """List events by school"""
    school = get_object_or_404(School, slug=slug, is_active=True)
    events_list = Event.objects.filter(
        school=school,
        status='upcoming'
    ).select_related('category')
    
    paginator = Paginator(events_list, 12)
    page_number = request.GET.get('page')
    events = paginator.get_page(page_number)
    
    context = {
        'school': school,
        'events': events,
    }
    return render(request, 'events/school_events.html', context)


def search_events(request):
    """Search events"""
    query = request.GET.get('q', '').strip()
    results = []
    
    if query:
        results = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__icontains=query) |
            Q(school__name__icontains=query) |
            Q(category__name__icontains=query),
            status='upcoming'
        ).select_related('school', 'category').distinct()[:50]
    
    context = {
        'query': query,
        'results': results,
        'total_results': len(results),
    }
    return render(request, 'events/search.html', context)


@require_POST
def initiate_vote_payment(request):
    """Initialize Paystack payment for voting"""
    try:
        data = json.loads(request.body)
        contestant_id = data.get('contestant_id')
        amount = data.get('amount')
        voter_name = data.get('voter_name')
        voter_email = data.get('voter_email')
        voter_phone = data.get('voter_phone', '')
        
        # Validate inputs
        if not all([contestant_id, amount, voter_name, voter_email]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Convert amount to Decimal to avoid float/Decimal issues
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid amount'}, status=400)
        
        contestant = get_object_or_404(VotingContestant, id=contestant_id)
        event = contestant.event
        
        # Check if voting is active
        if event.voting_ends_at and timezone.now() > event.voting_ends_at:
            return JsonResponse({'error': 'Voting has ended'}, status=400)
        
        # Validate minimum amount - convert to Decimal for comparison
        min_amount = Decimal(str(event.voting_price_per_vote))
        if amount < min_amount:
            return JsonResponse({
                'error': f'Minimum amount is ₦{min_amount}'
            }, status=400)
        
        # Create vote record
        vote = Vote.objects.create(
            event=event,
            contestant=contestant,
            voter_name=voter_name,
            voter_email=voter_email,
            voter_phone=voter_phone,
            amount_paid=amount,
            user=request.user if request.user.is_authenticated else None
        )
        
        # Initialize Paystack payment
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "email": voter_email,
            "amount": int(amount * 100),  # Convert to kobo
            "reference": vote.reference,
            "callback_url": request.build_absolute_uri('/events/payment/callback/'),
            "metadata": {
                "type": "vote",
                "vote_id": vote.id,
                "voter_name": voter_name,
                "event_title": event.title,
                "contestant_name": contestant.name,
                "votes_count": vote.votes_count
            }
        }
        
        response = requests.post(paystack_url, json=payload, headers=headers)
        response_data = response.json()
        
        if response_data.get('status'):
            vote.paystack_reference = response_data['data']['reference']
            vote.save()
            
            return JsonResponse({
                'status': 'success',
                'authorization_url': response_data['data']['authorization_url'],
                'reference': vote.reference,
                'votes_count': vote.votes_count
            })
        else:
            return JsonResponse({'error': 'Payment initialization failed'}, status=400)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def payment_callback(request):
    """Handle Paystack payment callback"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, 'Invalid payment reference')
        return redirect('events:home')
    
    # Verify payment with Paystack
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }
    
    try:
        response = requests.get(verify_url, headers=headers)
        response_data = response.json()
        
        if response_data.get('status') and response_data['data']['status'] == 'success':
            metadata = response_data['data']['metadata']
            payment_type = metadata.get('type')
            
            if payment_type == 'vote':
                vote_id = metadata.get('vote_id')
                vote = Vote.objects.get(id=vote_id)

                # Idempotency guard — only credit once (webhook may also fire)
                if vote.payment_status != 'completed':
                    vote.payment_status = 'completed'
                    vote.paid_at = timezone.now()
                    vote.save()

                    # Update contestant votes
                    contestant = vote.contestant
                    contestant.total_votes += vote.votes_count
                    contestant.total_amount_received += vote.amount_paid
                    contestant.save()

                messages.success(request, f'{vote.votes_count} vote(s) cast successfully!')
                return redirect('events:event_detail', slug=vote.event.slug)
        else:
            messages.error(request, 'Payment verification failed')
            return redirect('events:home')
            
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
        return redirect('events:home')


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """Handle Paystack webhook notifications"""
    # Verify webhook signature
    signature = request.headers.get('x-paystack-signature')
    payload = request.body
    
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    
    if signature != computed_signature:
        return HttpResponse(status=400)
    
    try:
        data = json.loads(payload)
        event = data.get('event')
        
        if event == 'charge.success':
            reference = data['data']['reference']
            metadata = data['data']['metadata']
            payment_type = metadata.get('type')
            
            if payment_type == 'vote':
                vote = Vote.objects.get(paystack_reference=reference)
                if vote.payment_status != 'completed':
                    vote.payment_status = 'completed'
                    vote.paid_at = timezone.now()
                    vote.save()
                    
                    # Use F() for atomic update — avoids race condition with callback
                    VotingContestant.objects.filter(pk=vote.contestant_id).update(
                        total_votes=F('total_votes') + vote.votes_count,
                        total_amount_received=F('total_amount_received') + vote.amount_paid
                    )
        
        return HttpResponse(status=200)
        
    except Exception as e:
        return HttpResponse(status=400)


@require_POST
def rsvp_event(request):
    """RSVP to an event"""
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone', '')
        
        if not all([event_id, name, email]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        event = get_object_or_404(Event, id=event_id)
        
        # Check if already RSVP'd
        if EventRSVP.objects.filter(event=event, email=email).exists():
            return JsonResponse({'error': 'You have already RSVP\'d to this event'}, status=400)
        
        # Create RSVP
        rsvp = EventRSVP.objects.create(
            event=event,
            name=name,
            email=email,
            phone=phone,
            user=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'RSVP successful! We\'ll send you event updates.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
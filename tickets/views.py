# tickets/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Event, TicketPurchase, Ticket
import requests
import json
import hashlib
import hmac
from decimal import Decimal


def events_home(request):
    """Display all available events"""
    now = timezone.now()
    
    # Get upcoming events
    upcoming_events = Event.objects.filter(
        is_active=True,
        status='upcoming',
        event_date__gte=now
    ).order_by('event_date')
    
    # Get featured events
    featured_events = Event.objects.filter(
        is_active=True,
        is_featured=True,
        event_date__gte=now
    ).order_by('event_date')[:3]
    
    context = {
        'upcoming_events': upcoming_events,
        'featured_events': featured_events,
    }
    return render(request, 'tickets/events_home.html', context)


def event_detail(request, slug):
    """Display event details and ticket purchase form"""
    event = get_object_or_404(Event, slug=slug, is_active=True)
    
    # Check if event is sold out
    if event.is_sold_out:
        sold_out = True
    else:
        sold_out = False
    
    context = {
        'event': event,
        'sold_out': sold_out,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'tickets/event_detail.html', context)


@require_http_methods(["POST"])
def initiate_payment(request):
    """Initialize payment with Paystack"""
    try:
        # Get form data
        event_slug = request.POST.get('event_slug')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        quantity = int(request.POST.get('quantity', 1))
        
        # Get event
        event = get_object_or_404(Event, slug=event_slug, is_active=True)
        
        # Check if tickets are available
        if event.tickets_remaining < quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {event.tickets_remaining} tickets remaining'
            })
        
        # Calculate total amount
        price_per_ticket = event.current_price
        total_amount = price_per_ticket * quantity
        
        # Create ticket purchase record
        with transaction.atomic():
            # Generate unique payment reference
            import uuid
            payment_ref = f"NM-{uuid.uuid4().hex[:12].upper()}"
            
            purchase = TicketPurchase.objects.create(
                event=event,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                quantity=quantity,
                price_per_ticket=price_per_ticket,
                total_amount=total_amount,
                payment_reference=payment_ref,
                payment_status='pending'
            )
        
        # Initialize Paystack payment
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "amount": int(total_amount * 100),  # Convert to kobo
            "reference": payment_ref,
            "callback_url": f"{request.scheme}://{request.get_host()}/tickets/payment/callback/",
            "metadata": {
                "purchase_id": str(purchase.purchase_id),
                "event_id": event.id,
                "event_title": event.title,
                "quantity": quantity,
                "buyer_name": f"{first_name} {last_name}",
                "phone": phone
            }
        }
        
        response = requests.post(paystack_url, headers=headers, json=payload)
        response_data = response.json()
        
        if response_data.get('status'):
            return JsonResponse({
                'success': True,
                'authorization_url': response_data['data']['authorization_url'],
                'reference': payment_ref
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Payment initialization failed. Please try again.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


def payment_callback(request):
    """Handle payment callback from Paystack"""
    reference = request.GET.get('reference')
    
    if not reference:
        return render(request, 'tickets/payment_failed.html', {
            'message': 'Invalid payment reference'
        })
    
    # Verify payment with Paystack
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }
    
    try:
        response = requests.get(verify_url, headers=headers)
        response_data = response.json()
        
        if response_data.get('status') and response_data['data']['status'] == 'success':
            # Payment successful - process the purchase
            with transaction.atomic():
                purchase = TicketPurchase.objects.get(payment_reference=reference)
                
                if purchase.payment_status != 'completed':
                    # Update purchase status
                    purchase.payment_status = 'completed'
                    purchase.paystack_reference = response_data['data']['reference']
                    purchase.save()
                    
                    # Update event tickets sold
                    event = purchase.event
                    event.tickets_sold += purchase.quantity
                    event.save()
                    
                    # Create individual tickets
                    tickets = []
                    for i in range(purchase.quantity):
                        ticket = Ticket.objects.create(
                            purchase=purchase,
                            event=event,
                            status='active'
                        )
                        tickets.append(ticket)
                    
                    # Send confirmation email
                    send_ticket_email(purchase, tickets)
                
                return redirect('tickets:purchase_success', purchase_id=purchase.purchase_id)
        else:
            # Payment failed
            purchase = TicketPurchase.objects.get(payment_reference=reference)
            purchase.payment_status = 'failed'
            purchase.save()
            
            return render(request, 'tickets/payment_failed.html', {
                'message': 'Payment verification failed'
            })
            
    except TicketPurchase.DoesNotExist:
        return render(request, 'tickets/payment_failed.html', {
            'message': 'Purchase record not found'
        })
    except Exception as e:
        return render(request, 'tickets/payment_failed.html', {
            'message': f'Error processing payment: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """Handle Paystack webhooks for payment notifications"""
    try:
        # Verify webhook signature
        paystack_signature = request.headers.get('X-Paystack-Signature')
        
        if not paystack_signature:
            return JsonResponse({'status': 'error', 'message': 'No signature'}, status=400)
        
        # Compute hash
        hash_value = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()
        
        if hash_value != paystack_signature:
            return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)
        
        # Process webhook
        payload = json.loads(request.body)
        event_type = payload.get('event')
        
        if event_type == 'charge.success':
            data = payload.get('data', {})
            reference = data.get('reference')
            
            with transaction.atomic():
                purchase = TicketPurchase.objects.get(payment_reference=reference)
                
                if purchase.payment_status != 'completed':
                    purchase.payment_status = 'completed'
                    purchase.paystack_reference = reference
                    purchase.save()
                    
                    # Update tickets sold
                    event = purchase.event
                    event.tickets_sold += purchase.quantity
                    event.save()
                    
                    # Create tickets
                    tickets = []
                    for i in range(purchase.quantity):
                        ticket = Ticket.objects.create(
                            purchase=purchase,
                            event=event,
                            status='active'
                        )
                        tickets.append(ticket)
                    
                    # Send email
                    send_ticket_email(purchase, tickets)
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def purchase_success(request, purchase_id):
    """Display purchase success page with ticket download option"""
    purchase = get_object_or_404(TicketPurchase, purchase_id=purchase_id)
    tickets = purchase.tickets.all()
    
    context = {
        'purchase': purchase,
        'tickets': tickets,
    }
    return render(request, 'tickets/purchase_success.html', context)


def download_ticket(request, ticket_code):
    """Generate and download ticket image"""
    from .utils import generate_ticket_image
    
    ticket = get_object_or_404(Ticket, ticket_code=ticket_code)
    
    # Generate ticket image
    image_buffer = generate_ticket_image(ticket)
    
    # Return as downloadable image
    response = HttpResponse(image_buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket_code}.png"'
    return response


def verify_ticket(request):
    """Verify ticket by code with duplicate usage detection"""
    if request.method == 'POST':
        ticket_code = request.POST.get('ticket_code', '').strip().upper()
        
        try:
            ticket = Ticket.objects.select_related('event', 'purchase').get(ticket_code=ticket_code)
            
            context = {
                'ticket': ticket,
                'valid': True,
            }
            
            if ticket.is_used:
                # DUPLICATE ATTEMPT - Ticket already used by someone
                context['message'] = '⚠️ DUPLICATE ATTEMPT: Ticket Already Used!'
                context['warning'] = True
                context['duplicate_attempt'] = True
                context['used_info'] = {
                    'used_at': ticket.used_at,
                    'scanned_by': ticket.scanned_by or 'Event Staff',
                    'buyer_name': ticket.buyer_name,
                    'buyer_email': ticket.buyer_email,
                    'buyer_phone': ticket.purchase.phone,
                }
            elif ticket.status == 'cancelled':
                context['message'] = '❌ This ticket has been cancelled'
                context['valid'] = False
            else:
                context['message'] = '✅ VALID TICKET - Ready to Admit'
            
            return render(request, 'tickets/verify_ticket.html', context)
            
        except Ticket.DoesNotExist:
            context = {
                'valid': False,
                'message': '❌ INVALID: Ticket code not found in system',
                'ticket_code': ticket_code
            }
            return render(request, 'tickets/verify_ticket.html', context)
    
    return render(request, 'tickets/verify_ticket.html')


@require_http_methods(["POST"])
def mark_ticket_used(request, ticket_code):
    """Mark a ticket as used (for event organizers) with duplicate prevention"""
    try:
        ticket = get_object_or_404(Ticket, ticket_code=ticket_code)
        
        if ticket.is_used:
            # Return detailed info about who already used it
            return JsonResponse({
                'success': False,
                'message': f'Ticket already used on {ticket.used_at.strftime("%B %d, %Y at %I:%M %p")}',
                'already_used': True,
                'used_by': ticket.scanned_by or 'Event Staff',
                'used_at': ticket.used_at.strftime('%Y-%m-%d %H:%M:%S'),
                'original_buyer': ticket.buyer_name
            })
        
        scanned_by = request.POST.get('scanned_by', 'Event Staff')
        ticket.mark_as_used(scanned_by=scanned_by)
        
        return JsonResponse({
            'success': True,
            'message': 'Ticket marked as used successfully',
            'used_at': ticket.used_at.strftime('%Y-%m-%d %H:%M:%S'),
            'admitted': ticket.buyer_name
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


def my_tickets(request):
    """View tickets by email (no login required)"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        purchases = TicketPurchase.objects.filter(
            email__iexact=email,
            payment_status='completed'
        ).select_related('event').prefetch_related('tickets').order_by('-created_at')
        
        context = {
            'purchases': purchases,
            'email': email,
        }
        return render(request, 'tickets/my_tickets.html', context)
    
    return render(request, 'tickets/my_tickets.html')


def send_ticket_email(purchase, tickets):
    """Send ticket confirmation email"""
    try:
        subject = f'Your Tickets for {purchase.event.title} - NextMedia'
        
        # Create ticket codes list
        ticket_codes = [ticket.ticket_code for ticket in tickets]
        
        message = f"""
Hello {purchase.first_name},

Thank you for purchasing tickets for {purchase.event.title}!

Your Order Details:
- Event: {purchase.event.title}
- Date: {purchase.event.event_date.strftime('%B %d, %Y at %I:%M %p')}
- Venue: {purchase.event.venue}
- Number of Tickets: {purchase.quantity}
- Total Paid: ₦{purchase.total_amount:,.2f}

Your Ticket Codes:
{chr(10).join([f'- {code}' for code in ticket_codes])}

You can download your tickets at:
https://nextmediahq.net/tickets/my-tickets/

Simply enter your email address ({purchase.email}) to view and download all your tickets.

IMPORTANT: Please keep your ticket codes safe. You will need them for entry on the event day.

Event Details:
{purchase.event.venue}
{purchase.event.address}
{purchase.event.city}, {purchase.event.state}

Doors Open: {purchase.event.doors_open.strftime('%I:%M %p')}
Event Starts: {purchase.event.event_start.strftime('%I:%M %p')}

See you there!

Best regards,
NextMedia Events Team
"""
        
        send_mail(
            subject,
            message,
            'noreply@nextmediahq.net',
            [purchase.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending email: {e}")
# events/templatetags/event_filters.py
from django import template
from django.utils import timezone
from decimal import Decimal

register = template.Library()


@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Safely divide value by arg (returns float)"""
    try:
        if arg == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def calculate_votes(amount, price_per_vote):
    """
    Calculate number of votes based on amount paid and price per vote
    Usage: {{ amount|calculate_votes:event.voting_price_per_vote }}
    """
    try:
        amount = Decimal(str(amount))
        price = Decimal(str(price_per_vote))
        if price <= 0:
            return 0
        return int(amount // price)  # Floor division - only full votes count
    except (ValueError, TypeError, InvalidOperation):
        return 0


@register.filter
def is_voting_active(event):
    """
    Check if voting is currently active for this event
    """
    if not event.allow_voting:
        return False
    
    now = timezone.now()
    
    # If voting_ends_at is set, use it
    if event.voting_ends_at:
        return now < event.voting_ends_at
    
    # Otherwise, voting is active if event is upcoming or ongoing
    return event.is_upcoming or event.is_live


@register.filter
def format_currency(amount):
    """Format amount as Nigerian Naira with commas"""
    try:
        amount = float(amount)
        return f"₦{amount:,.2f}"
    except (ValueError, TypeError):
        return "₦0.00"


@register.filter
def truncate_text(text, length=100):
    """Truncate text to specified length with ellipsis"""
    if not text:
        return ""
    text = str(text)
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + "..."
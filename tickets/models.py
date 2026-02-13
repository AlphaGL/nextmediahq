# tickets/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from cloudinary.models import CloudinaryField
import uuid
import random
import string
from decimal import Decimal

def generate_ticket_code():
    """Generate a unique 12-character ticket code"""
    prefix = "NM"  # NextMedia prefix
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"{prefix}{random_part}"


class Event(models.Model):
    """Event model for parties and other events"""
    EVENT_TYPES = [
        ('party', 'Party'),
        ('concert', 'Concert'),
        ('festival', 'Festival'),
        ('conference', 'Conference'),
        ('workshop', 'Workshop'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='party')
    
    # Event Details
    venue = models.CharField(max_length=500)
    address = models.TextField()
    city = models.CharField(max_length=250)
    state = models.CharField(max_length=250, default='Rivers State')
    
    # Date and Time
    event_date = models.DateTimeField()
    doors_open = models.TimeField(help_text="What time do doors open?")
    event_start = models.TimeField(help_text="What time does the event start?")
    event_end = models.TimeField(blank=True, null=True)
    
    # Ticket Pricing
    ticket_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    early_bird_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Optional early bird discount price"
    )
    early_bird_deadline = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="When does early bird pricing end?"
    )
    
    # Capacity
    total_tickets = models.PositiveIntegerField(
        help_text="Total number of tickets available"
    )
    tickets_sold = models.PositiveIntegerField(default=0)
    
    # Images
    banner_image = CloudinaryField(
        'event/banner', blank=True, null=True,
        help_text="Main event banner (recommended: 1200x600px)"
    )
    thumbnail = CloudinaryField(
        'events/thumbnails/',
        blank=True,
        null=True,
        help_text="Thumbnail image (recommended: 400x400px)"
    )
    
    # Additional Info
    organizer_name = models.CharField(max_length=250)
    organizer_phone = models.CharField(max_length=250)
    organizer_email = models.EmailField(max_length=250)
    
    # Features
    features = models.TextField(
        blank=True,
        help_text="Event features, one per line (e.g., 'Live DJ', 'Free drinks', 'VIP lounge')"
    )
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['event_date']
        indexes = [
            models.Index(fields=['event_date']),
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)[:240]
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug[:230]}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    
    @property
    def tickets_remaining(self):
        """Calculate remaining tickets"""
        if self.total_tickets is None:
            return 0
        return self.total_tickets - self.tickets_sold
    
    @property
    def is_sold_out(self):
        """Check if event is sold out"""
        if self.total_tickets is None:
            return False
        return self.tickets_remaining <= 0
    
    @property
    def current_price(self):
        if self.is_early_bird_active:
            return self.early_bird_price
        return self.ticket_price
    
    @property
    def is_early_bird_active(self):
        """Check if early bird pricing is active"""
        if self.early_bird_price and self.early_bird_deadline:
            return timezone.now() < self.early_bird_deadline
        return False
    
    def get_features_list(self):
        """Get features as a list"""
        if self.features:
            return [f.strip() for f in self.features.split('\n') if f.strip()]
        return []


class TicketPurchase(models.Model):
    """Model for ticket purchases - buyers don't need to be registered users"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Purchase ID
    purchase_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Event
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='purchases')
    
    # Buyer Information
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Ticket Details
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price_per_ticket = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment Info
    payment_status = models.CharField(max_length=250, choices=PAYMENT_STATUS, default='pending')
    payment_reference = models.CharField(max_length=250, unique=True)
    paystack_reference = models.CharField(max_length=250, blank=True, null=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.CharField(max_length=250, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_reference']),
            models.Index(fields=['email']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event.title}"
    
    @property
    def buyer_full_name(self):
        return f"{self.first_name} {self.last_name}"


class Ticket(models.Model):
    """Individual ticket model with unique code"""
    TICKET_STATUS = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Ticket Code - Unique identifier
    ticket_code = models.CharField(
        max_length=12, 
        unique=True, 
        default=generate_ticket_code,
        editable=False
    )
    
    # Relations
    purchase = models.ForeignKey(TicketPurchase, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tickets')
    
    # Ticket Status
    status = models.CharField(max_length=250, choices=TICKET_STATUS, default='active')
    
    # Usage Tracking
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(blank=True, null=True)
    scanned_by = models.CharField(max_length=250, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_code']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.ticket_code} - {self.event.title}"
    
    def mark_as_used(self, scanned_by=None):
        """Mark ticket as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.status = 'used'
        if scanned_by:
            self.scanned_by = scanned_by
        self.save()
    
    @property
    def buyer_name(self):
        return self.purchase.buyer_full_name
    
    @property
    def buyer_email(self):
        return self.purchase.email
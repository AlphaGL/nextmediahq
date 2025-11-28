# events/models.py
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.utils.text import slugify
from news.models import School
from decimal import Decimal
import uuid


class EventCategory(models.Model):
    """Categories for events (e.g., Concert, Conference, Workshop, Party)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Event Categories"
        ordering = ['name']


class Event(models.Model):
    """Main Event Model"""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Basic Information
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    short_description = models.TextField(max_length=500, blank=True)
    
    # Media
    banner_image = CloudinaryField('events/banners/', blank=True, null=True)
    gallery_images = models.JSONField(default=list, blank=True, help_text="List of Cloudinary URLs")
    
    # Classification
    category = models.ForeignKey(EventCategory, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    # Date & Time
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Location
    venue = models.CharField(max_length=300)
    address = models.TextField()
    map_link = models.URLField(blank=True, help_text="Google Maps link")
    
    # Status & Features
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    allow_voting = models.BooleanField(default=False)
    
    # Voting Configuration
    voting_price_per_vote = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=500.00,
        help_text="Minimum amount per vote in Naira"
    )
    voting_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Meta
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.short_description and self.description:
            self.short_description = self.description[:200] + "..."
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('events:event_detail', kwargs={'slug': self.slug})

    @property
    def total_votes(self):
        """Total votes cast for this event"""
        return self.votes.filter(payment_status='completed').count()

    @property
    def total_voting_revenue(self):
        """Total revenue from voting"""
        completed_votes = self.votes.filter(payment_status='completed')
        return sum(vote.amount_paid for vote in completed_votes)

    @property
    def is_live(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date

    @property
    def is_upcoming(self):
        return timezone.now() < self.start_date

    @property
    def days_until_event(self):
        if self.is_upcoming:
            delta = self.start_date - timezone.now()
            return delta.days
        return 0

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-start_date']


class VotingContestant(models.Model):
    """Contestants in an event's voting competition"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='contestants')
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    photo = CloudinaryField('events/contestants/', blank=True, null=True)
    contestant_number = models.PositiveIntegerField()
    
    # Vote tracking
    total_votes = models.PositiveIntegerField(default=0)
    total_amount_received = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"#{self.contestant_number} - {self.name}"

    class Meta:
        ordering = ['contestant_number']
        unique_together = ['event', 'contestant_number']


class Vote(models.Model):
    """Individual votes cast for contestants"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Unique identifier
    reference = models.CharField(max_length=100, unique=True, editable=False)
    
    # Vote details
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='votes')
    contestant = models.ForeignKey(VotingContestant, on_delete=models.CASCADE, related_name='votes')
    
    # Voter information
    voter_name = models.CharField(max_length=200)
    voter_email = models.EmailField()
    voter_phone = models.CharField(max_length=20, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Vote calculation
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    votes_count = models.PositiveIntegerField(default=1)
    
    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    paystack_reference = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"VOTE-{uuid.uuid4().hex[:12].upper()}"
        
        # Calculate votes based on amount paid - handle Decimal properly
        if self.amount_paid and self.event.voting_price_per_vote:
            # Convert both to Decimal to avoid float/Decimal mixing
            amount = Decimal(str(self.amount_paid))
            price_per_vote = Decimal(str(self.event.voting_price_per_vote))
            
            # Perform division with Decimals
            if price_per_vote > 0:
                self.votes_count = int(amount / price_per_vote)
            else:
                self.votes_count = 0
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.votes_count} vote(s) for {self.contestant.name}"

    class Meta:
        ordering = ['-created_at']


class EventRSVP(models.Model):
    """Track event RSVPs/interest"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.event.title}"

    class Meta:
        unique_together = ['event', 'email']
        ordering = ['-created_at']
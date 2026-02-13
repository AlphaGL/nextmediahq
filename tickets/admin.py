# tickets/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Event, TicketPurchase, Ticket


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'event_type', 'event_date', 'venue', 'current_price_display',
        'tickets_status', 'status', 'is_featured', 'created_at'
    ]
    list_filter = ['event_type', 'status', 'is_featured', 'event_date', 'city']
    search_fields = ['title', 'venue', 'organizer_name', 'city']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['tickets_sold', 'created_at', 'updated_at', 'tickets_remaining']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'event_type', 'status', 'is_featured', 'is_active')
        }),
        ('Location', {
            'fields': ('venue', 'address', 'city', 'state')
        }),
        ('Date & Time', {
            'fields': ('event_date', 'doors_open', 'event_start', 'event_end')
        }),
        ('Pricing', {
            'fields': (
                'ticket_price', 
                'early_bird_price', 
                'early_bird_deadline',
            )
        }),
        ('Capacity', {
            'fields': ('total_tickets', 'tickets_sold', 'tickets_remaining')
        }),
        ('Images', {
            'fields': ('banner_image', 'thumbnail')
        }),
        ('Organizer Info', {
            'fields': ('organizer_name', 'organizer_phone', 'organizer_email')
        }),
        ('Features', {
            'fields': ('features',),
            'description': 'Enter event features, one per line'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def current_price_display(self, obj):
        if obj.is_early_bird_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">₦{}</span> '
                '<small style="text-decoration: line-through;">₦{}</small>',
                f'{obj.current_price:,.2f}', f'{obj.ticket_price:,.2f}'
            )
        return format_html('₦{}', f'{obj.current_price:,.2f}')
    current_price_display.short_description = 'Current Price'
    
    def tickets_status(self, obj):
        remaining = obj.tickets_remaining
        total = obj.total_tickets
        percentage = (remaining / total * 100) if total > 0 else 0
        
        if remaining == 0:
            color = 'red'
            status = 'SOLD OUT'
        elif percentage < 20:
            color = 'orange'
            status = f'{remaining} left'
        else:
            color = 'green'
            status = f'{remaining}/{total}'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    tickets_status.short_description = 'Tickets'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related()


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    readonly_fields = ['ticket_code', 'status', 'is_used', 'used_at', 'scanned_by']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TicketPurchase)
class TicketPurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'purchase_id_short', 'buyer_full_name', 'email', 'event',
        'quantity', 'total_amount_display', 'payment_status_display',
        'is_verified', 'created_at'
    ]
    list_filter = ['payment_status', 'is_verified', 'event', 'created_at']
    search_fields = [
        'first_name', 'last_name', 'email', 'phone', 
        'payment_reference', 'purchase_id'
    ]
    readonly_fields = [
        'purchase_id', 'payment_reference', 'paystack_reference',
        'created_at', 'updated_at', 'verified_at'
    ]
    inlines = [TicketInline]
    
    fieldsets = (
        ('Purchase Information', {
            'fields': ('purchase_id', 'event', 'quantity', 'price_per_ticket', 'total_amount')
        }),
        ('Buyer Details', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Payment Information', {
            'fields': (
                'payment_status', 'payment_reference', 
                'paystack_reference'
            )
        }),
        ('Verification', {
            'fields': ('is_verified', 'verified_at', 'verified_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def purchase_id_short(self, obj):
        return str(obj.purchase_id)[:8] + '...'
    purchase_id_short.short_description = 'Purchase ID'
    
    def total_amount_display(self, obj):
        return format_html('₦{}', f'{obj.total_amount:,.2f}')
    total_amount_display.short_description = 'Total Amount'
    
    def payment_status_display(self, obj):
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'gray'
        }
        color = colors.get(obj.payment_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'Payment Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event').prefetch_related('tickets')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_code', 'event', 'buyer_name', 'status_display',
        'is_used', 'used_at', 'created_at'
    ]
    list_filter = ['status', 'is_used', 'event', 'created_at']
    search_fields = ['ticket_code', 'purchase__first_name', 'purchase__last_name', 'purchase__email']
    readonly_fields = [
        'ticket_code', 'purchase', 'event', 'is_used', 
        'used_at', 'scanned_by', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_code', 'event', 'purchase', 'status')
        }),
        ('Usage Tracking', {
            'fields': ('is_used', 'used_at', 'scanned_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        colors = {
            'active': 'green',
            'used': 'gray',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'purchase')
    
    def has_add_permission(self, request):
        return False
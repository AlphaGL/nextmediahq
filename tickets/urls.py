# tickets/urls.py
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # Main pages
    path('', views.events_home, name='events_home'),
    path('event/<slug:slug>/', views.event_detail, name='event_detail'),
    
    # Payment
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('api/webhook/', views.paystack_webhook, name='paystack_webhook'),
    
    # Purchase success
    path('purchase/<uuid:purchase_id>/success/', views.purchase_success, name='purchase_success'),
    
    # Tickets
    path('ticket/<str:ticket_code>/download/', views.download_ticket, name='download_ticket'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    
    # Verification
    path('verify/', views.verify_ticket, name='verify_ticket'),
    path('verify/<str:ticket_code>/mark-used/', views.mark_ticket_used, name='mark_ticket_used'),
]
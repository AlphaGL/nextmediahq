# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.events_home, name='home'),
    path('event/<slug:slug>/', views.event_detail, name='event_detail'),
    path('category/<slug:slug>/', views.events_by_category, name='category_events'),
    path('school/<slug:slug>/', views.events_by_school, name='school_events'),
    path('search/', views.search_events, name='search'),
    
    # Payment endpoints (for voting only)
    path('api/cast-vote/', views.initiate_vote_payment, name='cast_vote'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('api/webhook/', views.paystack_webhook, name='paystack_webhook'),
    
    # RSVP
    path('api/rsvp/', views.rsvp_event, name='rsvp'),
]
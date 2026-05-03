# ads/urls.py
from django.urls import path
from . import views

app_name = 'ads'

urlpatterns = [
    # Analytics tracking (called via JS from ad include templates)
    path('track/impression/<uuid:ad_id>/', views.track_impression, name='track_impression'),
    path('track/click/<uuid:ad_id>/', views.track_click, name='track_click'),
]
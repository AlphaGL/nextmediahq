# news/urls.py
from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('ping/', views.ping_view, name='ping'),
    path('', views.home, name='home'),
    path('schools/', views.school_list, name='school_list'),
    path('school/<slug:slug>/', views.school_news, name='school_news'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('category/<slug:slug>/', views.category_news, name='category_news'),
    path('past-questions/', views.past_questions, name='past_questions'),
    path('download/<int:pk>/', views.download_question, name='download_question'),
    path('search/', views.search, name='search'),
    path('manifest.json', views.manifest, name='manifest'),
    path('sw.js', views.service_worker, name='service_worker'),
    path("about/", views.AboutUsViews.as_view(), name='about'),
    path("privacy/", views.PrivacyViews.as_view(), name='privacy'),
    path("terms/", views.TermsViews.as_view(), name='terms'),
    path("disclaimer/", views.DisclaimerViews.as_view(), name='disclaimer'),
    path("contact/", views.ContactViews.as_view(), name='contact'),
]
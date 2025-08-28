# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import News, School, Category, PastQuestion

def home(request):
    # Get featured news
    featured_news = News.objects.filter(is_published=True, is_featured=True).select_related('school', 'category')[:6]
    
    # Get latest news by category
    school_news = News.objects.filter(
        is_published=True, 
        category__slug='school-news'
    ).select_related('school', 'category')[:6]
    
    global_news = News.objects.filter(
        is_published=True, 
        category__slug='global-news'
    ).select_related('school', 'category')[:6]
    
    sports_news = News.objects.filter(
        is_published=True, 
        category__slug='sports'
    ).select_related('school', 'category')[:6]
    
    context = {
        'featured_news': featured_news,
        'school_news': school_news,
        'global_news': global_news,
        'sports_news': sports_news,
        'schools': School.objects.filter(is_active=True)[:6],
    }
    return render(request, 'news/index.html', context)

def school_list(request):
    schools = School.objects.filter(is_active=True)
    context = {'schools': schools}
    return render(request, 'news/school_list.html', context)

def school_news(request, slug):
    school = get_object_or_404(School, slug=slug, is_active=True)
    news_list = News.objects.filter(
        school=school, 
        is_published=True
    ).select_related('category')
    
    paginator = Paginator(news_list, 12)
    page_number = request.GET.get('page')
    news = paginator.get_page(page_number)
    
    context = {
        'school': school,
        'news': news,
    }
    return render(request, 'news/school_news.html', context)

def news_detail(request, slug):
    news = get_object_or_404(News, slug=slug, is_published=True)
    related_news = News.objects.filter(
        category=news.category,
        is_published=True
    ).exclude(id=news.id)[:4]
    
    context = {
        'news': news,
        'related_news': related_news,
    }
    return render(request, 'news/news_detail.html', context)

def category_news(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    news_list = News.objects.filter(
        category=category, 
        is_published=True
    ).select_related('school')
    
    paginator = Paginator(news_list, 12)
    page_number = request.GET.get('page')
    news = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'news': news,
    }
    return render(request, 'news/category_news.html', context)

def past_questions(request):
    questions_list = PastQuestion.objects.all().select_related('school')
    schools = School.objects.filter(is_active=True)
    
    # Filter by school if provided
    school_slug = request.GET.get('school')
    if school_slug:
        questions_list = questions_list.filter(school__slug=school_slug)
    
    # Filter by subject if provided
    subject = request.GET.get('subject')
    if subject:
        questions_list = questions_list.filter(subject__icontains=subject)
    
    paginator = Paginator(questions_list, 20)
    page_number = request.GET.get('page')
    questions = paginator.get_page(page_number)
    
    context = {
        'questions': questions,
        'schools': schools,
    }
    return render(request, 'news/past_questions.html', context)

@require_POST
def download_question(request, pk):
    question = get_object_or_404(PastQuestion, pk=pk)
    question.download_count += 1
    question.save()
    
    response = HttpResponse(question.file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{question.title}.pdf"'
    return response

def search(request):
    query = request.GET.get('q')
    results = []
    
    if query:
        results = News.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query),
            is_published=True
        ).select_related('school', 'category')[:20]
    
    context = {
        'query': query,
        'results': results,
    }
    return render(request, 'news/search.html', context)

def manifest(request):
    manifest_data = {
        "name": "NextMedia",
        "short_name": "NextMedia",
        "description": "Latest news from schools and around the world",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a2e",
        "theme_color": "#ff6b35",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/static/img/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/img/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest_data)
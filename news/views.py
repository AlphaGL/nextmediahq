# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.conf import settings
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from .models import News, School, Category, PastQuestion

def custom_404_view(request, exception=None):
    """Custom 404 error page with recent news"""
    try:
        # Get 3 recent news articles to show on 404 page
        recent_news = News.objects.filter(
            is_published=True
        ).select_related('school', 'category').order_by('-published_date')[:3]
        
        context = {
            'recent_news': recent_news,
            'hide_cta': True,  # Hide the CTA section on error page
        }
        
        return render(request, 'news/404.html', context, status=404)
    except Exception:
        # Fallback in case of database issues
        return render(request, 'news/404.html', {'recent_news': [], 'hide_cta': True}, status=404)

def custom_500_view(request):
    """Custom 500 error page"""
    context = {
        'hide_cta': True,
    }
    return render(request, 'news/500.html', context, status=500)

def custom_403_view(request, exception=None):
    """Custom 403 error page"""
    context = {
        'hide_cta': True,
    }
    return render(request, 'news/403.html', context, status=403)

def custom_400_view(request, exception=None):
    """Custom 400 error page"""
    context = {
        'hide_cta': True,
    }
    return render(request, 'news/400.html', context, status=400)

def ping_view(request):
    return JsonResponse({"status": "OK"})

@require_GET
@cache_control(max_age=86400)  # Cache for 24 hours
def service_worker(request):
    """Serve the service worker with proper content type and headers"""
    try:
        with open(settings.BASE_DIR / 'static/js/sw.js', 'r') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'  # Allow service worker to control entire site
        return response
    except FileNotFoundError:
        return HttpResponse('console.log("Service worker not found");', content_type='application/javascript')

def home(request):
    from django.db.models import Prefetch
    
    # Get the 6 most recently uploaded news (for ticker animation)
    latest_news = News.objects.filter(is_published=True).select_related('school', 'category').order_by('-created_at')[:3]
    
    # Get featured news
    featured_news = News.objects.filter(is_published=True, is_featured=True).select_related('school', 'category')[:12]
    
    # Get all active categories and their news dynamically
    categories_with_news = []
    categories = Category.objects.filter(is_active=True).order_by('name')
    
    for category in categories:
        # Get latest news for this category
        category_news = News.objects.filter(
            is_published=True,
            category=category
        ).select_related('school', 'category').order_by('-created_at')[:6]
        
        # Only include categories that have news
        if category_news.exists():
            categories_with_news.append({
                'category': category,
                'news': list(category_news)
            })
    
    context = {
        'latest_news': latest_news,
        'featured_news': featured_news,
        'categories_with_news': categories_with_news,
        'schools': School.objects.filter(is_active=True)[:6],
    }
    return render(request, 'news/index.html', context)

def school_list(request):
    schools = School.objects.filter(is_active=True)
    context = {'schools': schools}
    return render(request, 'news/school_list.html', context)

def school_news(request, slug):
    """Enhanced school news view with better error handling"""
    try:
        school = get_object_or_404(School, slug=slug, is_active=True)
        news_list = News.objects.filter(
            school=school, 
            is_published=True
        ).select_related('category')
        
        paginator = Paginator(news_list, 12)
        page_number = request.GET.get('page')
        
        try:
            news = paginator.get_page(page_number)
        except Exception:
            # Invalid page number, redirect to first page
            news = paginator.get_page(1)
        
        context = {
            'school': school,
            'news': news,
        }
        return render(request, 'news/school_news.html', context)
        
    except Http404:
        # School not found
        schools = School.objects.filter(is_active=True)[:6]
        context = {
            'schools': schools,
            'missing_slug': slug,
        }
        return render(request, 'news/404.html', context, status=404)
    

def news_detail(request, slug):
    """Enhanced news detail view with better error handling"""
    try:
        news = get_object_or_404(News, slug=slug, is_published=True)
        
        # Get related news
        related_news = News.objects.filter(
            category=news.category,
            is_published=True
        ).exclude(id=news.id).select_related('school', 'category')[:4]
        
        context = {
            'news': news,
            'related_news': related_news,
        }
        return render(request, 'news/news_detail.html', context)
        
    except Http404:
        # Custom handling for news not found
        recent_news = News.objects.filter(
            is_published=True
        ).select_related('school', 'category')[:3]
        
        context = {
            'recent_news': recent_news,
            'missing_slug': slug,
        }
        return render(request, 'news/404.html', context, status=404)
    
def category_news(request, slug):
    """Enhanced category news view with better error handling"""
    try:
        category = get_object_or_404(Category, slug=slug, is_active=True)
        news_list = News.objects.filter(
            category=category, 
            is_published=True
        ).select_related('school')
        
        paginator = Paginator(news_list, 12)
        page_number = request.GET.get('page')
        
        try:
            news = paginator.get_page(page_number)
        except Exception:
            news = paginator.get_page(1)
        
        context = {
            'category': category,
            'news': news,
        }
        return render(request, 'news/category_news.html', context)
        
    except Http404:
        # Category not found
        categories = Category.objects.filter(is_active=True)
        recent_news = News.objects.filter(is_published=True)[:3]
        
        context = {
            'categories': categories,
            'recent_news': recent_news,
            'missing_slug': slug,
        }
        return render(request, 'news/404.html', context, status=404)
    
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
    question.save()
    
    response = HttpResponse(question.file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{question.title}.pdf"'
    return response

def search(request):
    """Enhanced search view with better error handling"""
    query = request.GET.get('q', '').strip()
    results = []
    
    if query:
        try:
            results = News.objects.filter(
                Q(title__icontains=query) | 
                Q(content__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(school__name__icontains=query) |
                Q(category__name__icontains=query),
                is_published=True
            ).select_related('school', 'category').distinct()[:50]  # Limit to 50 results
            
        except Exception as e:
            # Log error in production
            if settings.DEBUG:
                print(f"Search error: {e}")
            results = []
    
    context = {
        'query': query,
        'results': results,
        'total_results': len(results),
    }
    return render(request, 'news/search.html', context)

@cache_control(max_age=86400)  # Cache for 24 hours
def manifest(request):
    """Serve PWA manifest with proper headers"""
    manifest_data = {
        "name": "NextMedia - Latest News",
        "short_name": "NextMedia",
        "description": "Latest news from schools and around the world",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a2e",
        "theme_color": "#ff6b35",
        "orientation": "portrait-primary",
        "scope": "/",
        "icons": [
            {
                "src": "/static/img/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/img/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable any"
            }
        ],
        "categories": ["news", "education", "information"],
        "lang": "en-US",
        "shortcuts": [
            {
                "name": "School News",
                "short_name": "Schools",
                "description": "Browse news from schools",
                "url": "/schools/",
                "icons": [
                    {
                        "src": "/static/img/icon-192x192.png",
                        "sizes": "192x192"
                    }
                ]
            },
            {
                "name": "Global News",
                "short_name": "Global",
                "description": "Read global news",
                "url": "/category/global-news/",
                "icons": [
                    {
                        "src": "/static/img/icon-192x192.png",
                        "sizes": "192x192"
                    }
                ]
            }
        ]
    }
    
    response = JsonResponse(manifest_data)
    response['Content-Type'] = 'application/manifest+json'
    return response
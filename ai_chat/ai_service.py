# ai_chat/ai_service.py
import requests
from datetime import datetime
from django.conf import settings
from groq import Groq
import logging

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """AI Service with real-time data capabilities"""
    
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.news_api_key = getattr(settings, 'NEWS_API_KEY', None)
        
    def get_current_date_time(self):
        """Get current date and time"""
        now = datetime.now()
        return {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'day': now.strftime('%A'),
            'formatted': now.strftime('%B %d, %Y at %I:%M %p')
        }
    
    def search_news(self, query, max_results=3):
        """
        Search news using NewsAPI.org (Free tier: 100 requests/day)
        Alternative: Use RSS feeds if API limit is reached
        """
        if not self.news_api_key:
            return self._search_news_rss(query, max_results)
        
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'apiKey': self.news_api_key,
                'pageSize': max_results,
                'language': 'en',
                'sortBy': 'publishedAt'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                articles = []
                
                for article in data.get('articles', [])[:max_results]:
                    articles.append({
                        'title': article.get('title', 'No title'),
                        'description': article.get('description', 'No description'),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'url': article.get('url', ''),
                        'published': article.get('publishedAt', '')
                    })
                
                return articles
            else:
                logger.warning(f"NewsAPI error: {response.status_code}")
                return self._search_news_rss(query, max_results)
                
        except Exception as e:
            logger.error(f"News search error: {str(e)}")
            return self._search_news_rss(query, max_results)
    
    def _search_news_rss(self, query, max_results=3):
        """
        Fallback: Search news using free RSS feeds
        No API key needed, unlimited requests
        """
        try:
            import feedparser
            
            # Use Google News RSS (no API key needed)
            rss_url = f'https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en'
            
            feed = feedparser.parse(rss_url)
            articles = []
            
            for entry in feed.entries[:max_results]:
                articles.append({
                    'title': entry.get('title', 'No title'),
                    'description': entry.get('summary', 'No description')[:200],
                    'source': entry.get('source', {}).get('title', 'Google News'),
                    'url': entry.get('link', ''),
                    'published': entry.get('published', '')
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"RSS feed error: {str(e)}")
            return []
    
    def get_platform_data(self, intent, message=""):
        """Get data from NextMedia database"""
        from news.models import News, School, Category, PastQuestion
        from django.db.models import Count
        from datetime import datetime, timedelta
        
        data = {}
        
        try:
            if 'identity' in intent:
                data['identity'] = {
                    'name': 'Next AI',
                    'tagline': 'YOUR TRUSTED SOURCE FOR FAST AND CREDIBLE INFORMATION',
                    'platform': 'NextMedia',
                    'website': 'nextmediahq.net',
                    'description': 'I help you find the latest news from schools, entertainment, sports, and global events. You can also access past questions and educational resources.'
                }
            
            if 'platform_news' in intent:
                # Check if asking for specific date
                message_lower = message.lower()
                
                if 'yesterday' in message_lower:
                    # Get yesterday's news
                    yesterday = datetime.now().date() - timedelta(days=1)
                    news_queryset = News.objects.filter(
                        is_published=True,
                        created_at__date=yesterday
                    ).select_related('school', 'category').order_by('-created_at')[:5]
                else:
                    # Get latest news
                    news_queryset = News.objects.filter(is_published=True).select_related('school', 'category').order_by('-created_at')[:5]
                
                if news_queryset.exists():
                    data['latest_news'] = [{
                        'title': news.title,
                        'category': news.category.name,
                        'school': news.school.name if news.school else 'General',
                        'date': news.created_at.strftime('%B %d, %Y at %I:%M %p'),
                        'excerpt': news.excerpt[:150] if news.excerpt else news.content[:150]
                    } for news in news_queryset]
            
            if 'school_info' in intent:
                # Get schools from database
                schools = School.objects.filter(is_active=True).annotate(
                    news_count=Count('news')
                ).order_by('name')[:10]
                
                if schools.exists():
                    data['schools'] = [{
                        'name': school.name,
                        'abbreviation': school.abbreviation,
                        'news_count': school.news_count,
                        'established': school.established.year if school.established else 'N/A'
                    } for school in schools]
            
            if 'categories' in intent:
                # Get categories from database
                categories = Category.objects.filter(is_active=True).annotate(
                    news_count=Count('news')
                ).order_by('-news_count')
                
                if categories.exists():
                    data['categories'] = [{
                        'name': cat.name,
                        'news_count': cat.news_count
                    } for cat in categories]
            
            if 'past_questions' in intent:
                # Get past questions info
                questions_count = PastQuestion.objects.count()
                recent_questions = PastQuestion.objects.select_related('school').order_by('-created_at')[:3]
                
                data['past_questions'] = {
                    'total': questions_count,
                    'recent': [{
                        'title': q.title,
                        'school': q.school.name,
                        'subject': q.subject,
                        'year': f"{q.start_year}-{q.end_year}" if q.start_year != q.end_year else str(q.start_year)
                    } for q in recent_questions]
                }
        
        except Exception as e:
            logger.error(f"Error fetching platform data: {str(e)}")
        
        return data
        """
        Get weather using OpenWeatherMap (Free tier: 1000 requests/day)
        Alternative: wttr.in (unlimited, no API key)
        """
        try:
            # Using wttr.in (free, no API key needed)
            url = f'https://wttr.in/{city}?format=j1'
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                
                return {
                    'temperature': f"{current['temp_C']}°C",
                    'condition': current['weatherDesc'][0]['value'],
                    'humidity': f"{current['humidity']}%",
                    'wind': f"{current['windspeedKmph']} km/h",
                    'feels_like': f"{current['FeelsLikeC']}°C"
                }
        except Exception as e:
            logger.error(f"Weather error: {str(e)}")
            return None
    
    def detect_intent(self, message):
        """Detect user intent from message"""
        message_lower = message.lower()
        
        intents = {
            'identity': ['who are you', 'what are you', 'your name', 'who made you', 'who created you', 'who owns', 'your owner', 'who built you', 'developer', 'creator'],
            'platform_news': ['nextmedia news', 'latest news from nextmedia', 'our platform news', 'latest school news', 'school news from platform'],
            'external_news': ['yesterday news', 'news yesterday', 'breaking news', 'global news', 'world news', 'international news', 'news today from', 'latest nigerian news', 'latest news about', 'news on', 'news regarding'],
            'school_info': ['schools', 'universities', 'colleges', 'which schools', 'list schools', 'available schools'],
            'past_questions': ['past questions', 'past papers', 'exam papers', 'download questions', 'study materials'],
            'categories': ['categories', 'sections', 'topics', 'what categories'],
            'weather': ['weather', 'temperature', 'forecast', 'climate', 'rain'],
            'datetime': ['date', 'time', 'today', 'day', 'when', 'what day', 'current time'],
            'sports': ['sports', 'football', 'soccer', 'basketball', 'match', 'game'],
            'entertainment': ['entertainment', 'movie', 'music', 'celebrity', 'actor'],
            'education': ['school', 'education', 'exam', 'study']
        }
        
        detected_intents = []
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intents.append(intent)
        
        return detected_intents if detected_intents else ['general']
    
    def enhance_context(self, message):
        """Enhance message context with real-time data"""
        intents = self.detect_intent(message)
        context = {}
        
        # Always include current date/time
        context['datetime'] = self.get_current_date_time()
        
        # Add platform database data
        platform_data = self.get_platform_data(intents, message)
        if platform_data:
            context['platform'] = platform_data
        
        # Add external news for specific queries
        if 'external_news' in intents or ('platform_news' in intents and 'yesterday' in message.lower() and not platform_data.get('latest_news')):
            # External news search
            search_query = self._extract_search_query(message, intents)
            news = self.search_news(search_query, max_results=5)
            if news:
                context['external_news'] = news
        
        # Add weather
        if 'weather' in intents:
            weather = self.get_weather()
            if weather:
                context['weather'] = weather
        
        return context
    
    def _extract_search_query(self, message, intents):
        """Extract relevant search query from user message"""
        # Remove common question words
        query = message.lower()
        stop_words = ['what', 'when', 'where', 'who', 'how', 'tell me', 'show me', 
                      'give me', 'about', 'the', 'is', 'are', 'can you']
        
        for word in stop_words:
            query = query.replace(word, '')
        
        # Add intent-specific keywords
        if 'sports' in intents:
            query = f"sports {query}"
        elif 'entertainment' in intents:
            query = f"entertainment {query}"
        elif 'education' in intents:
            query = f"education nigeria {query}"
        
        return query.strip() or "latest news"
    
    def build_enhanced_prompt(self, message, context):
        """Build enhanced system prompt with real-time context"""
        
        current_info = f"""Current Date & Time: {context['datetime']['formatted']}
Today is {context['datetime']['day']}.

"""
        
        # Platform identity
        identity_info = ""
        if 'platform' in context and 'identity' in context['platform']:
            identity = context['platform']['identity']
            identity_info = f"""Your Identity:
- You are {identity['name']} - {identity['tagline']}
- Platform: {identity['platform']} ({identity['website']})
- What you do: {identity['description']}

"""
        
        # Platform news
        platform_news_info = ""
        if 'platform' in context and 'latest_news' in context['platform']:
            platform_news_info = "Latest News from NextMedia Platform:\n"
            for i, news in enumerate(context['platform']['latest_news'], 1):
                platform_news_info += f"{i}. {news['title']}\n   Category: {news['category']} | School: {news['school']} | Date: {news['date']}\n   {news['excerpt']}...\n\n"
        
        # Schools info
        schools_info = ""
        if 'platform' in context and 'schools' in context['platform']:
            schools_info = "Available Schools on NextMedia:\n"
            for school in context['platform']['schools']:
                schools_info += f"- {school['name']} ({school['abbreviation']}) - {school['news_count']} news articles | Est. {school['established']}\n"
            schools_info += "\n"
        
        # Categories info
        categories_info = ""
        if 'platform' in context and 'categories' in context['platform']:
            categories_info = "News Categories Available:\n"
            for cat in context['platform']['categories']:
                categories_info += f"- {cat['name']} ({cat['news_count']} articles)\n"
            categories_info += "\n"
        
        # Past questions info
        pq_info = ""
        if 'platform' in context and 'past_questions' in context['platform']:
            pq = context['platform']['past_questions']
            pq_info = f"Past Questions Database:\nTotal: {pq['total']} past question papers available\n\nRecent additions:\n"
            for q in pq['recent']:
                pq_info += f"- {q['title']} | {q['school']} | {q['subject']} | Year: {q['year']}\n"
            pq_info += "\n"
        
        # External news
        external_news_info = ""
        if 'external_news' in context and context['external_news']:
            external_news_info = "External News Sources:\n"
            for i, article in enumerate(context['external_news'], 1):
                external_news_info += f"{i}. {article['title']}\n   Source: {article['source']}\n   {article['description'][:150]}...\n\n"
        
        # Weather
        weather_info = ""
        if 'weather' in context and context['weather']:
            w = context['weather']
            weather_info = f"""Current Weather (Port Harcourt):
Temperature: {w['temperature']} (Feels like {w['feels_like']})
Condition: {w['condition']}
Humidity: {w['humidity']} | Wind: {w['wind']}

"""
        
        system_prompt = f"""You are Next AI - YOUR TRUSTED SOURCE FOR FAST AND CREDIBLE INFORMATION.
You are an intelligent assistant for NextMedia (nextmediahq.net), a leading Nigerian news platform.

{identity_info}{current_info}{platform_news_info}{schools_info}{categories_info}{pq_info}{external_news_info}{weather_info}

CRITICAL INSTRUCTIONS:
- When asked "who are you" or about your identity: Say "I'm Next AI - YOUR TRUSTED SOURCE FOR FAST AND CREDIBLE INFORMATION"
- Mention you're from NextMedia (nextmediahq.net) when relevant
- NEVER mention any personal owner names - only refer to "NextMedia platform"
- DO NOT repeat the date, time, or introduce yourself unless specifically asked
- Answer naturally and conversationally like a human would
- Use the date/time information only when relevant to the question
- If asking about platform news (latest school news, our news), use platform database first
- If asking about external/global/yesterday news, use external news sources
- When both platform and external news are available, mention both but prioritize platform news
- For past questions, guide users to the platform's past questions section
- Keep responses direct, concise, and focused on answering the user's question
- Don't mention that you have access to current information unless asked

User's question: {message}

Provide a direct, natural response without unnecessary preamble:"""

        return system_prompt
    
    def generate_response(self, message, conversation_history=None):
        """Generate AI response with enhanced context"""
        try:
            # Enhance context with real-time data
            context = self.enhance_context(message)
            
            # Build enhanced prompt
            enhanced_prompt = self.build_enhanced_prompt(message, context)
            
            # Prepare messages for Groq
            messages = [
                {
                    "role": "system",
                    "content": "You are Next AI, a helpful assistant for NextMedia."
                },
                {
                    "role": "user",
                    "content": enhanced_prompt
                }
            ]
            
            # Call Groq API
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            
            ai_response = response.choices[0].message.content
            
            return {
                'success': True,
                'message': ai_response,
                'context_used': list(context.keys())
            }
            
        except Exception as e:
            logger.error(f"AI generation error: {str(e)}")
            return {
                'success': False,
                'message': "I apologize, but I'm having trouble processing your request right now. Please try again.",
                'error': str(e)
            }
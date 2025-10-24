# ai_chat/ai_service.py
import requests
from datetime import datetime, timedelta
from django.conf import settings
from groq import Groq
import logging
import re

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """AI Service with real-time data capabilities and improved context memory"""
    
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
            'formatted': now.strftime('%B %d, %Y at %I:%M %p'),
            'year': now.year,
            'timestamp': now.isoformat()
        }
    
    def search_news(self, query, max_results=5):
        """Search news using NewsAPI.org with RSS fallback"""
        if not self.news_api_key:
            logger.info("No NewsAPI key, using RSS fallback")
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
                
                logger.info(f"NewsAPI returned {len(articles)} articles for query: {query}")
                return articles
            else:
                logger.warning(f"NewsAPI error: {response.status_code}, using RSS fallback")
                return self._search_news_rss(query, max_results)
                
        except Exception as e:
            logger.error(f"News search error: {str(e)}, using RSS fallback")
            return self._search_news_rss(query, max_results)
    
    def _search_news_rss(self, query, max_results=5):
        """Fallback: Search news using free RSS feeds"""
        try:
            import feedparser
            
            # Use Google News RSS
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
            
            logger.info(f"RSS returned {len(articles)} articles for query: {query}")
            return articles
            
        except Exception as e:
            logger.error(f"RSS feed error: {str(e)}")
            return []
    
    def get_platform_data(self, intent, message=""):
        """Get data from NextMedia database"""
        from news.models import News, School, Category, PastQuestion
        from django.db.models import Count
        
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
            
            if 'platform_news' in intent or 'school_info' in intent:
                message_lower = message.lower()
                
                # Check for specific school mentions
                school_query = None
                if 'futo' in message_lower:
                    school_query = School.objects.filter(abbreviation__iexact='FUTO').first()
                elif 'uniport' in message_lower:
                    school_query = School.objects.filter(abbreviation__iexact='UNIPORT').first()
                elif 'uniben' in message_lower:
                    school_query = School.objects.filter(abbreviation__iexact='UNIBEN').first()
                
                if school_query:
                    # Get news for specific school
                    news_queryset = News.objects.filter(
                        is_published=True,
                        school=school_query
                    ).select_related('school', 'category').order_by('-created_at')[:5]
                    
                    if news_queryset.exists():
                        data['school_news'] = {
                            'school_name': school_query.name,
                            'news': [{
                                'title': news.title,
                                'category': news.category.name,
                                'date': news.created_at.strftime('%B %d, %Y at %I:%M %p'),
                                'excerpt': news.excerpt[:150] if news.excerpt else news.content[:150],
                                'url': f"https://nextmediahq.net/news/{news.slug}/"
                            } for news in news_queryset]
                        }
                else:
                    # Get latest general news
                    if 'yesterday' in message_lower:
                        yesterday = datetime.now().date() - timedelta(days=1)
                        news_queryset = News.objects.filter(
                            is_published=True,
                            created_at__date=yesterday
                        ).select_related('school', 'category').order_by('-created_at')[:5]
                    else:
                        news_queryset = News.objects.filter(is_published=True).select_related('school', 'category').order_by('-created_at')[:5]
                    
                    if news_queryset.exists():
                        data['latest_news'] = [{
                            'title': news.title,
                            'category': news.category.name,
                            'school': news.school.name if news.school else 'General',
                            'date': news.created_at.strftime('%B %d, %Y at %I:%M %p'),
                            'excerpt': news.excerpt[:150] if news.excerpt else news.content[:150],
                            'url': f"https://nextmediahq.net/news/{news.slug}/"
                        } for news in news_queryset]
            
            if 'past_questions' in intent:
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
    
    def extract_conversation_context(self, conversation_history):
        """Extract comprehensive context from conversation history"""
        context = {
            'topics': set(),
            'entities': set(),
            'locations': set(),
            'timeframes': [],
            'questions': [],
            'last_topic': None,
            'last_entities': [],
            'conversation_flow': []
        }
        
        try:
            if not conversation_history:
                return context
            
            # Process recent messages (last 10 for better context)
            recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            for msg in recent_messages:
                if not isinstance(msg, dict):
                    continue
                    
                content = str(msg.get('content', '')).lower()
                role = msg.get('role', '')
                
                # Store conversation flow
                context['conversation_flow'].append({
                    'role': role,
                    'preview': content[:100]
                })
                
                # Extract topics
                topic_keywords = {
                    'politics': ['president', 'leader', 'government', 'politics', 'election', 'minister', 'senator'],
                    'news': ['news', 'breaking', 'latest', 'update', 'report'],
                    'education': ['school', 'university', 'futo', 'uniport', 'student', 'exam', 'lecture'],
                    'sports': ['football', 'soccer', 'champions league', 'match', 'game', 'player', 'team', 'premier league'],
                    'entertainment': ['movie', 'music', 'celebrity', 'actor', 'singer', 'entertainment'],
                    'technology': ['tech', 'technology', 'ai', 'computer', 'software', 'app']
                }
                
                for topic, keywords in topic_keywords.items():
                    if any(word in content for word in keywords):
                        context['topics'].add(topic)
                
                # Extract entities (proper nouns, organizations, people)
                entity_patterns = [
                    r'\b(?:Nigeria|FUTO|UNIPORT|UNIBEN|Champions League|Premier League|Real Madrid|Barcelona|Manchester|Liverpool|Arsenal|Chelsea)\b',
                    r'\b(?:Messi|Ronaldo|Neymar|Haaland|Mbappe)\b',
                    r'\b(?:Tinubu|Biden|Trump|Putin)\b'
                ]
                
                for pattern in entity_patterns:
                    entities = re.findall(pattern, content, re.IGNORECASE)
                    context['entities'].update([e.title() for e in entities])
                
                # Extract locations
                locations = re.findall(r'\b(?:Nigeria|Lagos|Abuja|Port Harcourt|Owerri|Benin|Europe|Africa|America)\b', content, re.IGNORECASE)
                context['locations'].update([loc.title() for loc in locations])
                
                # Extract years and dates
                years = re.findall(r'\b(19\d{2}|20\d{2})\b', content)
                context['timeframes'].extend(years)
                
                # Check for temporal references
                temporal_terms = ['yesterday', 'today', 'last night', 'last week', 'this week', 'recent', 'latest']
                for term in temporal_terms:
                    if term in content:
                        context['timeframes'].append(term)
                
                # Extract questions from user messages
                if role == 'user' and ('?' in content or any(q in content for q in ['what', 'when', 'where', 'who', 'how', 'why'])):
                    context['questions'].append(content)
            
            # Identify last discussed topic and entities
            if context['conversation_flow']:
                last_user_msg = None
                for msg in reversed(context['conversation_flow']):
                    if msg['role'] == 'user':
                        last_user_msg = msg['preview']
                        break
                
                if last_user_msg:
                    for topic, keywords in topic_keywords.items():
                        if any(word in last_user_msg for word in keywords):
                            context['last_topic'] = topic
                            break
                    
                    # Extract entities from last message
                    for pattern in entity_patterns:
                        last_entities = re.findall(pattern, last_user_msg, re.IGNORECASE)
                        context['last_entities'].extend([e.title() for e in last_entities])
            
            # Convert sets to lists for JSON serialization
            context['topics'] = list(context['topics'])
            context['entities'] = list(context['entities'])
            context['locations'] = list(context['locations'])
            context['timeframes'] = list(set(context['timeframes']))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting context: {str(e)}")
        
        return context
    
    def is_follow_up_question(self, message, conv_context):
        """Improved follow-up detection"""
        message_lower = message.lower().strip()
        
        # Pronouns and references that indicate follow-up
        follow_up_indicators = [
            'what about', 'what of', 'how about', 'and in', 'what in',
            'also', 'too', 'as well', 'similarly', 'that time', 'those',
            'he', 'she', 'they', 'them', 'his', 'her', 'their',
            'it', 'its', 'this', 'that', 'these', 'those',
            'there', 'then', 'same', 'other'
        ]
        
        # Check for follow-up indicators
        for indicator in follow_up_indicators:
            if message_lower.startswith(indicator) or f' {indicator} ' in message_lower:
                return True
        
        # Check if message is very short and context exists
        word_count = len(message.split())
        if word_count <= 5 and (conv_context['topics'] or conv_context['entities']):
            return True
        
        # Check if message starts with a year (common follow-up pattern)
        if re.match(r'^\d{4}', message_lower):
            return True
        
        # Check if message lacks a clear subject but has a verb
        question_words = ['what', 'when', 'where', 'who', 'how', 'why', 'which']
        has_question_word = any(word in message_lower for word in question_words)
        
        if not has_question_word and word_count <= 8 and conv_context['last_topic']:
            return True
        
        return False
    
    def build_contextual_query(self, message, conv_context):
        """Build enhanced query from message and conversation context"""
        message_lower = message.lower()
        query_parts = []
        
        # Add last topic if it's a follow-up
        if conv_context.get('last_topic'):
            query_parts.append(conv_context['last_topic'])
        
        # Add recent entities (prioritize last entities)
        if conv_context.get('last_entities'):
            query_parts.extend(conv_context['last_entities'][:2])
        elif conv_context.get('entities'):
            query_parts.extend(list(conv_context['entities'])[:2])
        
        # Add locations if mentioned
        if conv_context.get('locations'):
            query_parts.extend(list(conv_context['locations'])[:1])
        
        # Extract and add year from current message
        years = re.findall(r'\b(19\d{2}|20\d{2})\b', message)
        if years:
            query_parts.append(years[0])
        elif conv_context.get('timeframes'):
            # Add most recent timeframe
            query_parts.append(conv_context['timeframes'][-1])
        
        # Add the original message
        query_parts.append(message)
        
        # Build final query
        contextual_query = ' '.join(query_parts)
        logger.info(f"Built contextual query: {contextual_query}")
        
        return contextual_query.strip()
    
    def detect_intent(self, message, conv_context=None):
        """Enhanced intent detection with context awareness"""
        message_lower = message.lower()
        
        intents = {
            'identity': ['who are you', 'what are you', 'your name', 'who made you', 'introduce yourself'],
            'platform_news': ['nextmedia news', 'latest news from nextmedia', 'platform news', 'school news'],
            'external_news': ['breaking news', 'global news', 'world news', 'latest news', 'current news', 'news today'],
            'school_info': ['futo', 'uniport', 'uniben', 'university', 'school'],
            'sports': ['football', 'soccer', 'champions league', 'premier league', 'match', 'game', 'player', 'team'],
            'entertainment': ['movie', 'music', 'celebrity', 'entertainment'],
            'past_questions': ['past questions', 'past papers', 'exam papers'],
            'current_events': ['yesterday', 'today', 'last night', 'this week', 'recent', 'latest']
        }
        
        detected_intents = []
        
        # Check explicit intents
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intents.append(intent)
        
        # Add context-based intents
        if conv_context:
            if self.is_follow_up_question(message, conv_context):
                detected_intents.append('follow_up')
                
                # Inherit topic from context
                if conv_context.get('last_topic'):
                    topic_intent_map = {
                        'sports': 'sports',
                        'education': 'school_info',
                        'entertainment': 'entertainment',
                        'news': 'external_news'
                    }
                    inherited_intent = topic_intent_map.get(conv_context['last_topic'])
                    if inherited_intent and inherited_intent not in detected_intents:
                        detected_intents.append(inherited_intent)
        
        # Default to general if no specific intent
        return detected_intents if detected_intents else ['general']
    
    def enhance_context(self, message, conversation_history=None):
        """Enhanced context building with better follow-up handling"""
        try:
            # Extract conversation context
            conv_context = self.extract_conversation_context(conversation_history or [])
            
            # Detect intents with context
            intents = self.detect_intent(message, conv_context)
            
            logger.info(f"Detected intents: {intents}")
            logger.info(f"Conversation context: Topics={conv_context.get('topics')}, Entities={conv_context.get('entities')}")
            
            context = {}
            context['datetime'] = self.get_current_date_time()
            context['conversation_context'] = conv_context
            
            # Build query (contextual for follow-ups)
            if 'follow_up' in intents:
                contextual_query = self.build_contextual_query(message, conv_context)
                context['contextual_query'] = contextual_query
                context['is_follow_up'] = True
                search_query = contextual_query
            else:
                search_query = message
                context['is_follow_up'] = False
            
            # Get platform data
            platform_data = self.get_platform_data(intents, message)
            if platform_data:
                context['platform'] = platform_data
            
            # Determine if external news search is needed
            should_search_external = (
                'external_news' in intents or 
                'sports' in intents or 
                'current_events' in intents or
                'follow_up' in intents or
                (not platform_data and 'school_info' not in intents)
            )
            
            if should_search_external:
                try:
                    final_search_query = self._build_search_query(search_query, intents, conv_context)
                    logger.info(f"Searching external news for: {final_search_query}")
                    news = self.search_news(final_search_query, max_results=6)
                    if news:
                        context['external_news'] = news
                        logger.info(f"Found {len(news)} external news articles")
                except Exception as e:
                    logger.error(f"Error searching external news: {str(e)}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error enhancing context: {str(e)}")
            return {'datetime': self.get_current_date_time()}
    
    def _build_search_query(self, message, intents, conv_context):
        """Build optimized search query"""
        query = message.lower()
        
        # Remove common stop words
        stop_words = ['what', 'when', 'where', 'who', 'tell', 'me', 'show', 'about', 'the', 'is', 'are', 'was', 'were']
        for word in stop_words:
            query = re.sub(r'\b' + word + r'\b', '', query, flags=re.IGNORECASE)
        
        query = ' '.join(query.split())  # Remove extra spaces
        
        # Add context modifiers for better results
        if 'sports' in intents:
            if not any(sport in query for sport in ['football', 'champions league', 'premier league']):
                query = f"football {query}"
        
        if conv_context.get('timeframes') and 'yesterday' in conv_context['timeframes']:
            query = f"{query} yesterday"
        
        return query.strip() or "latest news"
    
    def build_enhanced_prompt(self, message, context, conversation_history):
        """Build system prompt with full context awareness"""
        
        try:
            # Current date/time
            current_info = f"""Current Date & Time: {context['datetime']['formatted']}
Today is {context['datetime']['day']}, {context['datetime']['year']}.

"""
            
            # Conversation context summary
            conv_context_info = ""
            if 'conversation_context' in context:
                conv_ctx = context['conversation_context']
                
                if context.get('is_follow_up'):
                    conv_context_info += "🔄 **FOLLOW-UP QUESTION DETECTED**\n"
                    if conv_ctx.get('last_topic'):
                        conv_context_info += f"Previous Topic: {conv_ctx['last_topic']}\n"
                    if conv_ctx.get('last_entities'):
                        conv_context_info += f"Discussed Previously: {', '.join(conv_ctx['last_entities'])}\n"
                    if context.get('contextual_query'):
                        conv_context_info += f"Enhanced Query: {context['contextual_query']}\n"
                    conv_context_info += "\n"
                
                if conv_ctx.get('topics'):
                    conv_context_info += f"Conversation Topics: {', '.join(conv_ctx['topics'])}\n"
                if conv_ctx.get('entities'):
                    conv_context_info += f"Entities Mentioned: {', '.join(list(conv_ctx['entities'])[:5])}\n"
                if conv_ctx.get('timeframes'):
                    conv_context_info += f"Time References: {', '.join(conv_ctx['timeframes'][:3])}\n"
                if conv_context_info:
                    conv_context_info += "\n"
            
            # Platform news
            platform_news_info = ""
            if 'platform' in context:
                if 'school_news' in context['platform']:
                    school_data = context['platform']['school_news']
                    if school_data.get('news'):
                        platform_news_info = f"📰 Latest News for {school_data['school_name']} from NextMedia:\n"
                        for i, news in enumerate(school_data['news'], 1):
                            platform_news_info += f"{i}. {news['title']}\n   Category: {news['category']} | {news['date']}\n   {news['excerpt']}\n   URL: {news['url']}\n\n"
                
                elif 'latest_news' in context['platform']:
                    platform_news_info = "📰 Latest News from NextMedia Platform:\n"
                    for i, news in enumerate(context['platform']['latest_news'], 1):
                        platform_news_info += f"{i}. {news['title']}\n   School: {news['school']} | Category: {news['category']}\n   {news['date']}\n   {news['excerpt']}\n   URL: {news['url']}\n\n"
            
            # External news
            external_news_info = ""
            if 'external_news' in context and context['external_news']:
                external_news_info = "🌐 Current News from External Sources:\n"
                for i, article in enumerate(context['external_news'], 1):
                    external_news_info += f"{i}. {article['title']}\n   Source: {article['source']} | Published: {article['published']}\n   {article['description'][:150]}...\n\n"
            
            # Build system prompt
            system_prompt = f"""You are Next AI - YOUR TRUSTED SOURCE FOR FAST AND CREDIBLE INFORMATION.
You are an intelligent assistant for NextMedia (nextmediahq.net).

{current_info}{conv_context_info}{platform_news_info}{external_news_info}

🎯 **CRITICAL INSTRUCTIONS:**

1. **Context Awareness**: Use the conversation context above to understand follow-up questions and references
2. **Current Information**: The external news sources contain the LATEST, CURRENT information - use them to answer questions about recent events
3. **Anti-Hallucination**: ONLY use information explicitly provided above. NEVER invent facts
4. **Source Citation**: Always cite sources:
   - "According to [source name]..."
   - "Based on current reports from [source]..."
   - "From NextMedia database..."
5. **Follow-Up Handling**: If this is a follow-up question, use the previous context to provide coherent answers
6. **No Data Available**: If no relevant information is provided, say: "I don't have current information about [topic]. For the latest updates, please check nextmediahq.net or reliable news sources."

User's question: {message}

Provide accurate, context-aware response based ONLY on the information provided above:"""

            return system_prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {str(e)}")
            return f"You are Next AI. Answer honestly based on available information: {message}"
    
    def generate_response(self, message, conversation_history=None):
        """Generate AI response with enhanced context"""
        try:
            if conversation_history is None:
                conversation_history = []
            
            # Enhance context
            context = self.enhance_context(message, conversation_history)
            
            # Build system prompt
            enhanced_prompt = self.build_enhanced_prompt(message, context, conversation_history)
            
            # Prepare messages for Groq
            messages = [
                {
                    "role": "system",
                    "content": "You are Next AI, a helpful and context-aware assistant. You understand follow-up questions and provide accurate information from reliable sources."
                }
            ]
            
            # Add conversation history (last 6 messages for context)
            if conversation_history:
                recent_history = conversation_history[-6:]
                for hist_msg in recent_history:
                    if isinstance(hist_msg, dict) and 'role' in hist_msg and 'content' in hist_msg:
                        role = str(hist_msg['role'])
                        if role == 'ai':
                            role = 'assistant'
                        
                        if role in ['user', 'assistant']:
                            messages.append({
                                "role": role,
                                "content": str(hist_msg['content'])
                            })
            
            # Add current query with enhanced prompt
            messages.append({
                "role": "user",
                "content": enhanced_prompt
            })
            
            # Call Groq API
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.4,  # Balanced creativity and accuracy
                max_tokens=800,
                top_p=0.9
            )
            
            ai_response = response.choices[0].message.content
            
            return {
                'success': True,
                'message': ai_response,
                'context_used': list(context.keys()),
                'is_follow_up': context.get('is_follow_up', False)
            }
            
        except Exception as e:
            logger.error(f"AI generation error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'message': "I apologize, but I'm having trouble processing your request right now. Please try again.",
                'error': str(e)
            }
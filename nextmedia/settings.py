# Create a separate settings_dev.py file for development

import os
from pathlib import Path
import dj_database_url
from decouple import config
from celery.schedules import crontab

# Import cloudinary
import cloudinary
import cloudinary.uploader
import cloudinary.api

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = os.path.join(BASE_DIR, 'news/templates')

SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')

# DEBUG = True
DEBUG = config('DEBUG', default=False, cast=bool)

# FORCE DEVELOPMENT MODE
DEVELOPMENT_MODE = False


# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'news',
    'ai_chat',
    'events',
    'learning',
    'tickets',
    'cloudinary',
    'cloudinary_storage',
    'ads',
]

# MINIMAL middleware for development
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nextmedia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ads.context_processors.active_ads',
            ],
        },
    },
]

WSGI_APPLICATION = 'nextmedia.wsgi.application'

DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'))
}

# Cloudinary configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
    'SECURE': False,  # Set to False for development
}

cloudinary.config( 
    cloud_name=config('CLOUDINARY_CLOUD_NAME'), 
    api_key=config('CLOUDINARY_API_KEY'), 
    api_secret=config('CLOUDINARY_API_SECRET'),
    secure=False  # Add this for development
)

CLOUDINARY_URL = config('CLOUDINARY_URL')
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# DISABLE ALL HTTPS ENFORCEMENT IN DEVELOPMENT
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None

# Cookie settings for development (HTTP)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Static files for development
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Basic security settings (non-HTTPS)
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = 'SAMEORIGIN'


# Security Settings (MUST have for production payments)
# SECURE_SSL_REDIRECT = True  # Force HTTPS
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# Paystack requires HTTPS
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = False
USE_TZ = False

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Development logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        # Log Celery task activity to console
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'news.tasks': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# ============================================
# AI CONFIGURATION
# ============================================
GROQ_API_KEY = config('GROQ_API_KEY', default='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')

# Optional: NewsAPI.org (Free tier: 100 requests/day)
NEWS_API_KEY = config('NEWS_API_KEY', default='1e08a5cefedb4e27bf357d95800ef7f5')

# Optional: OpenWeatherMap (Free tier: 1000 requests/day)
OPENWEATHER_API_KEY = config('OPENWEATHER_API_KEY', default='9ec8d46ed93e645a0e98fac1397dda00')

# ============================================
# PAYSTACK CONFIGURATION
# ============================================
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='pk_test_82cbf50854af160f931f8b9e6f9c84af8489536e')
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='sk_test_3e89989f81e42e78b1bce3d756f9da62ff9c8612')


# ============================================
# REDIS CONFIGURATION
# ============================================
REDIS_URL = config(
    'REDIS_URL',
    default='redis://default:nFnXllmZuxw4Az4mgkLXIBThXljw4I3E@knee-fortified-chatty-65675.db.redis.io:12561'
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'socket_connect_timeout': 5,
            'socket_timeout': 5,
            'retry_on_timeout': True,
        },
    }
}


# ============================================
# CELERY CONFIGURATION
# ============================================
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone — matches Django's TIME_ZONE above
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Keep task results for 24 hours then auto-expire
CELERY_RESULT_EXPIRES = 60 * 60 * 24

# Prevent a single worker from swamping memory on long scrapes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True

# ── Beat schedule: both scrapers run every 3 hours ─────────────
# They are offset by 5 minutes so they don't hammer the DB at
# the exact same second.
#
#   Punch       → 00:00, 03:00, 06:00, 09:00 … UTC
#   Sporting Sun→ 00:05, 03:05, 06:05, 09:05 … UTC
#
CELERY_BEAT_SCHEDULE = {
    'scrape-punch-every-3-hours': {
        'task': 'news.tasks.run_punch_scraper',
        'schedule': crontab(minute=0, hour='*/3'),
        'options': {'expires': 60 * 60 * 2},   # drop if not picked up within 2 h
    },
    'scrape-sportingsun-every-3-hours': {
        'task': 'news.tasks.run_sportingsun_scraper',
        'schedule': crontab(minute=5, hour='*/3'),
        'options': {'expires': 60 * 60 * 2},
    },
}
# nextmedia/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from news.views import custom_404_view, custom_500_view, custom_403_view, custom_400_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('news.urls')),
]

# Custom error handlers
handler404 = custom_404_view
handler500 = custom_500_view
handler403 = custom_403_view
handler400 = custom_400_view

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

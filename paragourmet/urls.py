# paragourmet/urls.py

from django.contrib import admin
from django.urls import path
from prompt.views import health_check_view, prompt_view, suggestion_view, index_view

urlpatterns = [
    # Admin site (optional)
    path('admin/', admin.site.urls),

    # API endpoints
    path('health', health_check_view, name='health_check'),
    path('api/prompt', prompt_view, name='prompt_api'),
    path('api/suggestion', suggestion_view, name='suggestion_api'),
    path('kr/', index_view, {'lang': 'ko'}, name='index_ko'),
    path('en/', index_view, {'lang': 'en'}, name='index_en'),
    path('', index_view, {'lang': 'ko'}, name='index'), # Default to Korean
]

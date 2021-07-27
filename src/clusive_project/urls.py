"""clusive_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import debug_toolbar
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pages.urls')),
    url(r'^robots.txt', lambda x: HttpResponse("User-Agent: *\nDisallow: /account", content_type="text/plain"), name="robots_file"),
    path('account/', include('roster.urls')),
    path('assessment/', include('assessment.urls')),
    path('author/', include('authoring.urls')),
    path('sessions/', include('django_session_timeout.urls')),
    path('glossary/', include('glossary.urls')),
    path('library/', include('library.urls')),
    path('tips/', include('tips.urls')),
    path('messagequeue/', include('messagequeue.urls')),
    path('progressbarupload/', include('progressbarupload.urls')),
    path('accounts/', include('allauth.socialaccount.providers.google.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

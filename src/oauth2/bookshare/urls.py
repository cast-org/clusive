from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import BookshareProvider

urlpatterns = default_urlpatterns(BookshareProvider)

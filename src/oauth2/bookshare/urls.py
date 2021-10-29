from django.urls import include, path
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from allauth.socialaccount import views as socialaccount_views
import allauth

from .provider import BookshareProvider

urlpatterns = default_urlpatterns(BookshareProvider) + [
    # Need the connection handlers to support multiple logins
    path('connections/', socialaccount_views.connections, name="socialaccount_connections"),

    # The templates for the following are automatically included by the
    # `connections` views above.  The urls are included here so that when
    # the connection view is called, there won't be a, e.g., "Reverse for
    # 'account_email' not found ..." exception.  Ultimately, we want to get rid
    # of these urls and the connections page itself since it includes
    # extraneous signup, login, logout, reset password, and email endpoints.
    # And, the OAuth2 workflow with Bookshare ends up back at allauth's
    # connections page, not a Clusive page.
    path('', include('allauth.account.urls'))
]

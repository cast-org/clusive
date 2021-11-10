from django.urls import path
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from . import views
from .provider import BookshareProvider

urlpatterns = default_urlpatterns(BookshareProvider) + [
    # Map 'socialaccount_connections' to a default Clusive's reader page.  This 
    # is because allauth hard codes a reverse('socialaccount_connections') as
    # the default redirect at the end of the workflow triggered by 
    # '.../login?process=connect'.  By adding this path, the default is set to 
    # one of Clusive's pages.
    #
    # Also, bookshare_connected() sets the session's 'bookshare_connected'
    # attribute to true.
    path('bookshare_connected', views.bookshare_connected, name='socialaccount_connections')
]

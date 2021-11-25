from django.urls import path
from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from pages.views import ReaderIndexView
from .provider import BookshareProvider

urlpatterns = default_urlpatterns(BookshareProvider) + [
    # Map 'socialaccount_connections' to Clusive's reader page.  This is because
    # allauth hard codes a reverse('socialaccount_connections') to handle the
    # end of the workflow triggered by '.../login?process=connect'.  By adding
    # this path, the end of that workflow will end up on Clusive's reader page.
    path('reader', ReaderIndexView.as_view(), name='socialaccount_connections')
]

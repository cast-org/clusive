import requests
from urllib.parse import urlencode
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseRedirect

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken

from .provider import BookshareProvider

import pdb

class BookshareOAuth2Adapter(OAuth2Adapter):
    provider_id = BookshareProvider.id
    basic_auth = True   # Use basic Authorization in access token request
    authorize_url = 'https://auth.bookshare.org/oauth/authorize'
    access_token_url = 'https://auth.bookshare.org/oauth/token'
    profile_url = 'https://api.bookshare.org/v2/me'

    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(
            self.profile_url,
            headers = { "Authorization": "Bearer " + token.token },
            params = { "api_key": app.client_id }
        )
        resp.raise_for_status()
        extra_data = resp.json()

        login = self.get_provider().sociallogin_from_response(request, extra_data)
        return login

    def is_connected(self):
        provider = self.get_provider()
        try:
            social_app = SocialApp.objects.get(provider=provider.id)
            social_account = SocialAccount.objects.get(user=self.request.user, provider=provider.id)
            access_token = SocialToken.objects.get(account=social_account, app_id=social_app.id)
            return not is_token_expired(access_token)

        except (SocialAccount.DoesNotExist, SocialToken.DoesNotExist):
            return False

def is_token_expired(token):
    return token.expires_at < timezone.now()

def is_bookshare_connected(request):
    bookshare_adapter = BookshareOAuth2Adapter(request)
    return bookshare_adapter.is_connected()

def bookshare_connected(request, *args, **kwargs):
    request.session['bookshare_connected'] = True
    return HttpResponseRedirect(reverse('reader_index'))

oauth2_login = OAuth2LoginView.adapter_view(BookshareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BookshareOAuth2Adapter)

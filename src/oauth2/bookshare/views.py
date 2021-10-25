import requests
from urllib.parse import urlencode

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)

from allauth.socialaccount.providers.oauth2.client import OAuth2Error

from .provider import BookshareProvider

import pdb

class BookshareOAuth2Adapter(OAuth2Adapter):
    provider_id = BookshareProvider.id
    basic_auth = True   # Use basic Authorization in access token request
    authorize_url = 'https://auth.bookshare.org/oauth/authorize'
    access_token_url = 'https://auth.bookshare.org/oauth/token'
    profile_url = 'https://api.bookshare.org/v2/me'

    def complete_login(self, request, app, token, **kwargs):
        pdb.set_trace()
        api_key = urlencode({
            'api_key': app.client_id
        })
        print('BOOKSHAREOAUTH2ADAPTER.COMPLETE_LOGIN(): ', self.profile_url + '?' + urlencode({'api_key': app.client_id}))

        resp = requests.get(
            self.profile_url,
            headers = { "Authorization": "Bearer " + token.token },
            params = { "api_key": app.client_id }
#            self.profile_url + '?' + api_key,
        )
        resp.raise_for_status()
        extra_data = resp.json()

        # This current fails with "The provider must implement the extract_uid()
        # method".  That is, add an extract_uid() to BookshareProvider class.
        login = self.get_provider().sociallogin_from_response(request, extra_data)
        print('BookshareOAuth2Adapter: %s', login)
        
        return login

oauth2_login = OAuth2LoginView.adapter_view(BookshareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BookshareOAuth2Adapter)

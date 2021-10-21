import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from allauth.socialaccount.providers.oauth2.client import OAuth2Error

from .provider import BookshareProvider

class BookshareOAuth2Adapter(OAuth2Adapter):
    provider_id = BookshareProvider.id
    access_token_url = 'https://auth.bookshare.org/oauth/token'
    authorize_url = 'https://auth.bookshare.org/oauth/authorize'
    # Need to determine what is available from Bookshare in terms of user info
    # In fact, this may not be an URL at all, but just an identfier.
    profile_url = ''

    # This is run after completing the OAuth2 workflow where Clusive has a
    # fresh access token and can use it to request Bookshare user information.
    # It then said user info in the associated SocialAccount.
    # TODO: find out if Bookshare supports GET or POST for the user information
    # It's possilble that allauth only implements GET.
    # Note: the following is basically a copy of the GoogleOAuth2Adapter
    # implementation and is just a placeholder for now.
    def complete_login(self, request, app, token, **kwargs):
        resp = requests.get(
            self.profile_url,
            params={"access_token": token.token, "alt": "json"},
        )
        resp.raise_for_status()
        extra_data = resp.json()
        login = self.get_provider().sociallogin_from_response(request, extra_data)
        print('BookshareOAuth2Adapter: %s', login)
        
        return login

oauth2_login = OAuth2LoginView.adapter_view(BookshareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BookshareOAuth2Adapter)


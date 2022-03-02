import requests
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone

from .provider import BookshareProvider


GENERIC_ORG_NAME = 'Organizational Account'
SINGLE_USER_NOT_ORG = 'single user'
NOT_A_BOOKSHARE_ACCOUNT = 'not bookshare'

BOOKSHARE_ACCOUNT_NAMES = {
    GENERIC_ORG_NAME, SINGLE_USER_NOT_ORG, NOT_A_BOOKSHARE_ACCOUNT
}


class BookshareOAuth2Adapter(OAuth2Adapter):
    provider_id = BookshareProvider.id
    basic_auth = True   # Use basic Authorization in access token request
    authorize_url = 'https://auth.bookshare.org/oauth/authorize'
    access_token_url = 'https://auth.bookshare.org/oauth/token'
    profile_url = 'https://api.bookshare.org/v2/me'
    account_summary_url = 'https://api.bookshare.org/v2/myaccount'
    organization_members_url = 'https://api.bookshare.org/v2/myOrganization/members'

    def complete_login(self, request, app, token, **kwargs):
        # 1. Get user profile info, e.g., name, and username
        resp = requests.get(
            self.profile_url,
            headers = { "Authorization": "Bearer " + token.token },
            params = { "api_key": app.client_id }
        )
        resp.raise_for_status()
        extra_data = resp.json()

        # 2. Get "proofOfDisability" and "studentStatus" (organizational account)
        resp = requests.get(
            self.account_summary_url,
            headers = { "Authorization": "Bearer " + token.token },
            params = { "api_key": app.client_id }
        )
        resp.raise_for_status()
        json_resp = resp.json()
        extra_data.update( {'proofOfDisabilityStatus': json_resp['proofOfDisabilityStatus']} )
        extra_data.update( {'studentStatus': json_resp['studentStatus']} )

        # 3. Ask for a list of organization members if `studentStatus` was null.
        # If the request for members succeeds, then conclude it's an
        # organizational account; otherwise, it isn't.
        if extra_data['studentStatus'] == None:
            resp = requests.get(
                self.organization_members_url,
                headers = { "Authorization": "Bearer " + token.token },
                params = { "api_key": app.client_id }
            )
            try:
                resp.raise_for_status()
                extra_data.update( { 'organizational': True } )
            except requests.exceptions.HTTPError:
                extra_data.update( { 'organizational': False } )
        else:
            extra_data.update( { 'organizational': True } )

        login = self.get_provider().sociallogin_from_response(request, extra_data)
        return login

    def is_connected(self):
        try:
            access_keys = self.get_access_keys()
            return not is_token_expired(access_keys.get('access_token'))
        except (SocialApp.DoesNotExist, SocialAccount.DoesNotExist, SocialToken.DoesNotExist):
            return False

    def has_account(self):
        try:
            return True if self.social_account else False
        except SocialAccount.DoesNotExist:
            return False

    def get_access_keys(self):
        provider = self.get_provider()
        social_app = SocialApp.objects.get(provider=provider.id)
        access_tokens = SocialToken.objects.filter(account__user=self.request.user, account__provider=provider.id)\
            .order_by('-expires_at')
        if len(access_tokens) == 0:
            raise SocialToken.DoesNotExist
        # There should be only one SocialAccount/SocialToken for this (user, provider).
        # If there is more than one, delete all but the most recent.
        the_access_token = access_tokens.first()
        for token in access_tokens:
            if token != the_access_token:
                try:
                    social_account = SocialAccount.objects.get(id=token.account.id)
                    social_account.delete() # cascades and deletes the token
                except:
                    token.delete()
        return {
            'access_token': the_access_token,
            'api_key': social_app.client_id,
            'proof_status': self.proof_of_disability_status()
        }

    def proof_of_disability_status(self):
        try:
            return self.social_account.extra_data.get('proofOfDisabilityStatus', 'missing')
        except SocialAccount.DoesNotExist:
            return 'missing'

    def is_organizational_account(self):
        try:
            return self.social_account.extra_data.get('organizational');
        except SocialAccount.DoesNotExist:
            return False

    @property
    def social_account(self):
        provider = self.get_provider()
        return SocialAccount.objects.get(user=self.request.user, provider=provider.id)

    @property
    def organization_name(self):
        try:
            return get_organization_name(self.social_account)
        except SocialAccount.DoesNotExist:
            return NOT_A_BOOKSHARE_ACCOUNT


def is_token_expired(token):
    return token.expires_at < timezone.now()

def is_bookshare_connected(request):
    return BookshareOAuth2Adapter(request).is_connected()

def has_bookshare_account(request):
    return BookshareOAuth2Adapter(request).has_account()

def get_access_keys(request):
    return BookshareOAuth2Adapter(request).get_access_keys()

def bookshare_connected(request, *args, **kwargs):
    request.session['bookshare_connected'] = True
    return HttpResponseRedirect(reverse('reader_index'))

def is_organizational_account(request):
    return BookshareOAuth2Adapter(request).is_organizational_account()

def get_organization_name(account):
    """
    If this represents an organizational account, return the
    organization's name.  If the organizational account does not provide
    a name, the generic name 'Organizational Account' is returned.  If the
    account is a single user account, the string 'single user' is returned.
    """
    is_organizational = account.extra_data.get('organizational', False)
    studentStatus = account.extra_data.get('studentStatus');
    if studentStatus != None:
        return studentStatus.get('organizationName', GENERIC_ORG_NAME)
    elif is_organizational:
        return GENERIC_ORG_NAME
    else:
        return SINGLE_USER_NOT_ORG


oauth2_login = OAuth2LoginView.adapter_view(BookshareOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(BookshareOAuth2Adapter)

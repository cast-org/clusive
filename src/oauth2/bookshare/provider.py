from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

# A ProviderAccount gets a number of pieces of info stored in the User's
# SocialAccount associated with a Provider, including (using Google as example)
# - user profile:           get_profile_url()
# - user's avatar:          get_avatar_url()
# - provider's logo/name:   get_brand() (ProviderAccount method)
# This sort of information is retrieved at the end of the OAuth2 workflow after
# the provider (i.e. Bookshare) has sent back an access token.  The client uses
# the access token to get information about the Bookshare user.  What you can
# get depends on Bookshare's API.  For example, there is a reference to a 
# `userIdentifier` to use in requests, but need to determine how to reqeust this
# `userIdentifier` using the Bookshare API.
# Note: initialize the base ProviderAccount:  ProviderAccount.__init__(self, social_account)
class BookshareAccount(ProviderAccount):
    
    def to_str(self):
        basic = super(BookshareAccount, self).to_str()
        return self.account.extra_data.get("name", basic)


# An OAuth2Provider gets information about the SSO provider
# - login url:                  get_login_url(self, request, kwargs)
# -- this is the "local" server url that kicks off the SSO authorization
# -- workflow that ends with receiving an access token from the provider.
# -- for Bookshare, it's Clusive's '/accounts/bookshare/login'
#
# - authorization parameters:    get_auth_params(self, request, action)
# -- gets the AUTH_PARAMS from settings.py for this provider and other optional
# -- params given in the current GET request's 'auth_params' entry.  It combines
# -- the two and returns the combination of authorization parameters.
# -- unclear if this is needed by Bookshare implementation
#
# - scope of authorization:      get_sope(self, request)
# -- get the SCOPE from the settings.py for this provider and other optional
# -- scopes in the current GET request's 'scope' entry.  It combines the two
# -- and returns the combination
#
# - default scope:               get_default_scope(self)
# -- return the default scope for this provider
# -- for Google SSO, returns 'profile' and sometimes 'profile email'
# -- Bookshare OAuth2 documentation lists 'basic' as the only scope.
# -- https://www.bookshare.org/cms/api-v2-oauth
class BookshareProvider(OAuth2Provider):
    id = 'bookshare'
    name = 'Bookshare'
    account_class = BookshareAccount
    
    def get_default_scope(self):
        return 'basic'

provider_classes = [BookshareProvider]

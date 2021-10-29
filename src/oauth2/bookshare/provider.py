from allauth.socialaccount import providers
from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.account.models import EmailAddress

# A ProviderAccount gets a number of pieces of information about the user from
# the provider based on a set of Provider's endpoints as stored in the User's 
# SocialAccount.  Examples:
# - user profile:           get_profile_url()
# - provider's logo/name:   get_brand() (ProviderAccount method)
# This sort of information is retrieved at the end of the OAuth2 workflow after
# the provider (i.e. Bookshare) has sent back an access token.  The client uses
# the access token and the extra_data in the SocialAccount to get information
# about the Bookshare user.  What you can get depends on Bookshare's API.
# Currently, we are using Bookshare's `/me` endpoint to which Bookshare responds
# with the User's name and email.
#
# The base ProviderAccount is initialized with a reference to the User's
# SocialAccount:  ProviderAccount.__init__(self, social_account)
class BookshareAccount(ProviderAccount):
    
    def to_str(self):
        basic = super(BookshareAccount, self).to_str()
        name = self.account.extra_data.get('name', None)
        if name is None:
            return self.account.extra_data.get('username', basic)
        else:
            return name.get("firstName", basic)

# An OAuth2Provider extracts information about the SSO user
# TODO (?):
# - authorization parameters:    get_auth_params(self, request, action)
#   gets the AUTH_PARAMS from settings.py for this provider and other optional
#   params given in the current GET request's 'auth_params' entry.  It combines
#   the two and returns the combination of authorization parameters.
#   unclear if this is needed by Bookshare implementation.  It may be needed
#   for the refresh token workflow
class BookshareProvider(OAuth2Provider):
    id = 'bookshare'
    name = 'Bookshare'
    account_class = BookshareAccount
    
    def get_default_scope(self):
        return 'basic'

    def extract_uid(self, data):
        return str(data.get('username'))

    def extract_common_fields(self, data):
        name = data.get('name')
        if name:
            firstName = name.get('firstName', '')
            lastName = name.get('lastName', '')
        else:
            firstName = ''
            lastName = ''

        return dict(
            email=data.get("username"),
            last_name=lastName,
            first_name=firstName,
        )

    def extract_email_addresses(self, data):
        ret = []
        email = data.get("username")
        ret.append(EmailAddress(email=email, verified=True, primary=False))
        return ret

provider_classes = [BookshareProvider]

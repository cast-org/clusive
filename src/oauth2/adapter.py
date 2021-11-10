from django.urls import reverse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class ClusiveSocialAccountAdapter(DefaultSocialAccountAdapter):

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the default URL to redirect to after successfully
        connecting to Bookshare
        """
        assert request.user.is_authenticated
        return reverse('reader_index')

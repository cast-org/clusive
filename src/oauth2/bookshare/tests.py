import logging

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from allauth.socialaccount.models import SocialAccount

from .provider import BookshareProvider
from .views import BookshareOAuth2Adapter, is_organizational_account, get_organization_name, \
    GENERIC_ORG_NAME, SINGLE_USER_NOT_ORG, NOT_A_BOOKSHARE_ACCOUNT

logger = logging.getLogger(__name__)

SINGLE_USER_EXTRADATA = {
    'username': 'singleUser@somewhere.org',
    'links': [],
    'name': {
        'firstName': 'Single',
        'lastName': 'User',
        'middle': None,
        'prefix': None,
        'suffix': None,
        'links': []
    },
    'proofOfDisabilityStatus': 'active',
    'studentStatus': None,
    'organizational': False
}

ORGANIZATIONAL_EXTRADATA = {
    'username': 'user@somewhere.org',
    'links': [],
    'name': {
        'firstName': 'Organizational',
        'lastName': 'Sponsor',
        'middle': None,
        'prefix': None,
        'suffix': None,
        'links': []
    },
    'proofOfDisabilityStatus': 'active',
    'studentStatus': {
        'organizationName': 'Anonymous Organization'
    },
    'organizational': True
}


class BookshareTestCase(TestCase):

    def setUp(self) -> None:
        self.request_factory = RequestFactory()
        # Create a user that has a single user Bookshare account
        single_user = User.objects.create_user(username='bookshareSingle', password='password1')
        self.single_user = single_user
        self.single_user.save()
        single_account = SocialAccount.objects.create(user=single_user, provider=BookshareProvider.id)
        single_account.uid = SINGLE_USER_EXTRADATA['username']
        single_account.extra_data = SINGLE_USER_EXTRADATA
        self.single_user_account = single_account
        self.single_user_account.save()

        # Create a user that has an organizational Bookshare account
        org_user = User.objects.create_user(username='bookshareOrganizational', password='password2')
        self.org_user = org_user
        self.org_user.save()
        org_account = SocialAccount.objects.create(user=org_user, provider=BookshareProvider.id)
        org_account.uid = ORGANIZATIONAL_EXTRADATA['username']
        org_account.extra_data = ORGANIZATIONAL_EXTRADATA
        self.org_account = org_account
        self.org_account.save()

        # Create a non-bookshare user
        user_no_bookshare = User.objects.create_user(username='userNoBookshare', password='password3')
        self.user_no_bookshare = user_no_bookshare
        self.user_no_bookshare.save()

    def test_create(self):
        self.assertNotEqual(None, self.single_user)
        self.assertNotEqual(None, self.single_user_account)
        self.assertNotEqual(None, self.org_user)
        self.assertNotEqual(None, self.org_account)
        self.assertNotEqual(None, self.user_no_bookshare)

    def test_is_organizational_account(self):
        request = self.request_factory.get('/my_account')
        request.user = self.org_user
        self.assertTrue(is_organizational_account(request))
        request.user = self.single_user
        self.assertFalse(is_organizational_account(request))
        request.user = self.user_no_bookshare
        self.assertFalse(is_organizational_account(request))

    def test_get_organization_name(self):
        soc_account = SocialAccount.objects.get(user=self.org_user)
        self.assertEqual(
            get_organization_name(soc_account),
            ORGANIZATIONAL_EXTRADATA['studentStatus']['organizationName']
        )
        soc_account = SocialAccount.objects.get(user=self.single_user)
        self.assertEqual(
            get_organization_name(soc_account),
            SINGLE_USER_NOT_ORG
        )

    def test_adapter_get_organization_name(self):
        request = self.request_factory.get('/my_account')
        request.user = self.single_user
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            SINGLE_USER_NOT_ORG
        )
        request.user = self.org_user
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            ORGANIZATIONAL_EXTRADATA['studentStatus']['organizationName']
        )
        request.user = self.user_no_bookshare
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            NOT_A_BOOKSHARE_ACCOUNT
        )

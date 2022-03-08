import json
import logging
import os

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from allauth.socialaccount.models import SocialAccount

from .provider import BookshareProvider
from .views import BookshareOAuth2Adapter, UserTypes, \
    is_organizational_account, get_organization_name, \
    get_organization_members, get_user_type, \
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
        # Read secrets.  These must be supplied by the developer in a json file
        # that resides in the parent directory.  For example, assuming this code
        # is run from 'target', the parent is 'clusive'.   The name of the file
        # itself is 'keysForTesting.json'.  The structure of the
        # file is:
        # {
        #   "singleUserKeys": {
        #       "userId":"partnerdemo@bookshare.org",
        #       "accessToken":"actual-access-token-value-goes-here",
        #       "apiKey":"actual-api-key-goes-here"
        #   },
        #   "organizationalUserKeys": {
        #       "userId":"partnerorgdemo@bookshare.org",
        #       "accessToken":"actual-access-token-value-goes-here",
        #       "apiKey":"actual-api-key-goes-here"
        #    }
        # }
        # If the keys can't be loaded the test_get_organization_members() and
        # test_get_user_type() tests are not run.
        try:
            parent_dir = os.path.dirname(os.getcwd())
            json_file = open(os.path.join(parent_dir, 'keysForTesting.json'))
            self.keys = json.load(json_file)
        except Exception as e:
            self.keys = None
            logger.debug('Error retrieving keys "%s"', e)

    def test_create(self):
        self.assertIsNotNone(self.single_user)
        self.assertIsNotNone(self.single_user_account)
        self.assertIsNotNone(self.org_user)
        self.assertIsNotNone(self.org_account)
        self.assertIsNotNone(self.user_no_bookshare)

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

    def test_display_user_type(self):
        name = UserTypes.display_name(UserTypes.INDIVIDUAL)
        self.assertEquals(name, 'Individual')
        name = UserTypes.display_name(UserTypes.ORGANIZATIONAL)
        self.assertEquals(name, 'Organizational')
        name = UserTypes.display_name(UserTypes.UNKNOWN)
        self.assertEquals(name, 'Unknown')

    def test_get_organization_members(self):
        if self.keys:
            # Test organizational account
            organization = self.keys['organizationalUserKeys']
            member_list = get_organization_members(
                organization['accessToken'],
                organization['apiKey']
            )
            # Test individual account
            individual = self.keys['individualUserKeys']
            self.assertIsNotNone(member_list)
            member_list = get_organization_members(
                individual['accessToken'],
                individual['apiKey']
            )
            self.assertIsNone(member_list)
        else:
            logger.debug('Ignoring "test_get_organization_members()", no access keys.')

    def test_get_user_type(self):
        if self.keys:
            # Test individual account
            individual = self.keys['individualUserKeys']
            user_type = get_user_type(
                individual['userId'],
                individual['accessToken'],
                individual['apiKey']
            )
            self.assertEqual(user_type, UserTypes.INDIVIDUAL)
            # Test organizational account
            organization = self.keys['organizationalUserKeys']
            user_type = get_user_type(
                organization['userId'],
                organization['accessToken'],
                organization['apiKey']
            )
            self.assertEqual(user_type, UserTypes.ORGANIZATIONAL)
            # Test for unknown.
            user_type = get_user_type('foo', 'bar', individual['apiKey'])
            self.assertEqual(user_type, UserTypes.UNKNOWN)
        else:
            logger.debug('Ignoring "test_get_user_type()", no access keys.')

import json
import logging
import os

from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from allauth.socialaccount.models import SocialAccount

from .provider import BookshareProvider
from .views import BookshareOAuth2Adapter, UserTypes, \
    is_organization_sponsor, get_organization_name, \
    get_organization_members, get_user_type, \
    GENERIC_ORG_NAME, INDIVIDUAL_NOT_ORG, NOT_A_BOOKSHARE_ACCOUNT

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
    'organizational': UserTypes.INDIVIDUAL,
    'dateOfBirth': '1990-01-01'
}

ORG_SPONSOR_EXTRADATA = {
    'username': 'sponsor@somewhere.org',
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
    'studentStatus': None,
    'organizational': UserTypes.ORG_SPONSOR,
    'dateOfBirth': None
}

# Old way of designating organizational accounts with boolean value, for
# testing update code.
OLD_ORG_SPONSOR_EXTRADATA = {
    'username': 'anotherSponsor@somewhere.org',
    'links': [],
    'name': {
        'firstName': 'Another',
        'lastName': 'Sponsor',
        'middle': None,
        'prefix': None,
        'suffix': None,
        'links': []
    },
    'proofOfDisabilityStatus': 'active',
    'studentStatus': None,
    'organizational': True
}

ORG_MEMBER_EXTRADATA = {
    'username': 'member@somewhere.org',
    'links': [],
    'name': {
        'firstName': 'Organizational',
        'lastName': 'Member',
        'middle': None,
        'prefix': None,
        'suffix': None,
        'links': []
    },
    'proofOfDisabilityStatus': 'active',
    'studentStatus': {
        'organizationName': 'Anonymous Organization'
    },
    'organizational': UserTypes.ORG_MEMBER,
    'dateOfBirth': '2001-02-14'
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

        # Create a user that has an organization sponsor Bookshare account
        org_sponsor = User.objects.create_user(username='bookshareOrganizational', password='password2')
        self.org_sponsor = org_sponsor
        self.org_sponsor.save()
        org_sponsor_account = SocialAccount.objects.create(user=org_sponsor, provider=BookshareProvider.id)
        org_sponsor_account.uid = ORG_SPONSOR_EXTRADATA['username']
        org_sponsor_account.extra_data = ORG_SPONSOR_EXTRADATA
        self.org_sponsor_account = org_sponsor_account
        self.org_sponsor_account.save()

        # Create a user that has an organization member Bookshare account
        org_member = User.objects.create_user(username='bookshareOrgMember', password='password3')
        self.org_member = org_member
        self.org_member.save()
        org_member_account = SocialAccount.objects.create(user=org_member, provider=BookshareProvider.id)
        org_member_account.uid = ORG_MEMBER_EXTRADATA['username']
        org_member_account.extra_data = ORG_MEMBER_EXTRADATA
        self.org_member_account = org_member_account
        self.org_member_account.save()

        # Create a user that has an organization sponsor Bookshare account, but
        # using the old way to designate that it is an organizational account
        # (true vs. false)
        old_org_sponsor = User.objects.create_user(username='oldBookshareOrganizational', password='password2')
        self.old_org_sponsor = old_org_sponsor
        self.old_org_sponsor.save()
        old_org_sponsor_account = SocialAccount.objects.create(user=old_org_sponsor, provider=BookshareProvider.id)
        old_org_sponsor_account.uid = OLD_ORG_SPONSOR_EXTRADATA['username']
        old_org_sponsor_account.extra_data = OLD_ORG_SPONSOR_EXTRADATA
        self.old_org_sponsor_account = old_org_sponsor_account
        self.old_org_sponsor_account.save()

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
        self.assertIsNotNone(self.org_sponsor)
        self.assertIsNotNone(self.org_sponsor_account)
        self.assertIsNotNone(self.old_org_sponsor)
        self.assertIsNotNone(self.old_org_sponsor_account)
        self.assertIsNotNone(self.org_member)
        self.assertIsNotNone(self.org_member_account)
        self.assertIsNotNone(self.user_no_bookshare)

    def test_is_organizational_sponsor(self):
        request = self.request_factory.get('/my_account')
        request.user = self.org_sponsor
        self.assertTrue(is_organization_sponsor(request))
        request.user = self.org_member
        self.assertFalse(is_organization_sponsor(request))
        request.user = self.single_user
        self.assertFalse(is_organization_sponsor(request))
        request.user = self.user_no_bookshare
        self.assertFalse(is_organization_sponsor(request))

    def test_get_organization_name(self):
        # self.org_sponsor has no student status; hence, no organization
        # name.
        soc_account = SocialAccount.objects.get(user=self.org_sponsor)
        self.assertEqual(
            get_organization_name(soc_account),
            GENERIC_ORG_NAME
        )
        # self.org_member has a student status; and an organization naem
        soc_account = SocialAccount.objects.get(user=self.org_member)
        self.assertEqual(
            get_organization_name(soc_account),
            ORG_MEMBER_EXTRADATA['studentStatus']['organizationName']
        )
        soc_account = SocialAccount.objects.get(user=self.single_user)
        self.assertEqual(
            get_organization_name(soc_account),
            INDIVIDUAL_NOT_ORG
        )

    def test_adapter_get_organization_name(self):
        request = self.request_factory.get('/my_account')
        request.user = self.single_user
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            INDIVIDUAL_NOT_ORG
        )
        # self.org_sponsor has no student status; hence, no organization
        # name.
        request.user = self.org_sponsor
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            GENERIC_ORG_NAME
        )
        # self.org_member has a student status; and an organization naem
        request.user = self.org_member
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            ORG_MEMBER_EXTRADATA['studentStatus']['organizationName']
        )
        request.user = self.user_no_bookshare
        self.assertEqual(
            BookshareOAuth2Adapter(request).organization_name,
            NOT_A_BOOKSHARE_ACCOUNT
        )

    def test_display_user_type(self):
        name = UserTypes.display_name(UserTypes.INDIVIDUAL)
        self.assertEquals(name, 'Individual')
        name = UserTypes.display_name(UserTypes.ORG_SPONSOR)
        self.assertEquals(name, 'Sponsor')
        name = UserTypes.display_name(UserTypes.ORG_MEMBER)
        self.assertEquals(name, 'Organization Member')
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
            self.assertIsNotNone(member_list)
            # Test individual account
            individual = self.keys['individualUserKeys']
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
            self.assertEqual(user_type, UserTypes.ORG_SPONSOR)
            # Test for unknown.
            user_type = get_user_type('foo', 'bar', individual['apiKey'])
            self.assertEqual(user_type, UserTypes.UNKNOWN)
        else:
            logger.debug('Ignoring "test_get_user_type()", no access keys.')

    def test_adapter_set_org_status(self):
        if self.keys:
            request = self.request_factory.get('/my_account')
            # Test the sponsor and individual test accounts.  Since the test
            # accounts are already properly set, calling set_org_status() will
            # reset to the correct value; hence, asserting equality.
            soc_account = SocialAccount.objects.get(user=self.org_sponsor)
            extra_data = soc_account.extra_data
            pre_set_org_status = extra_data['organizational']
            account_keys = self.keys['organizationalUserKeys']
            request.user = self.org_sponsor
            BookshareOAuth2Adapter(request).set_org_status(
                extra_data,
                account_keys['accessToken'],
                account_keys['apiKey']
            )
            soc_account = SocialAccount.objects.get(user=self.org_sponsor)
            post_set_org_status = soc_account.extra_data['organizational']
            self.assertEquals(pre_set_org_status, post_set_org_status)

            soc_account = SocialAccount.objects.get(user=self.single_user)
            extra_data = soc_account.extra_data
            pre_set_org_status = extra_data['organizational']
            account_keys = self.keys['individualUserKeys']
            request.user = self.single_user
            BookshareOAuth2Adapter(request).set_org_status(
                extra_data,
                account_keys['accessToken'],
                account_keys['apiKey']
            )
            soc_account = SocialAccount.objects.get(user=self.single_user)
            post_set_org_status = soc_account.extra_data['organizational']
            self.assertEquals(pre_set_org_status, post_set_org_status)
        else:
            logger.debug('Ignoring "test_adapter_set_org_status()", no access keys.')

    def test_adapter_update_org_status(self):
        if self.keys:
            request = self.request_factory.get('/my_account')
            # Test old organizational account -- should switch from true
            # (= Organizational) to '2' (= Sponsor Organization)
            soc_account = SocialAccount.objects.get(user=self.old_org_sponsor)
            self.assertTrue(soc_account.extra_data['organizational'])
            org_keys = self.keys['organizationalUserKeys']
            request.user = self.old_org_sponsor
            BookshareOAuth2Adapter(request).update_org_status(
                org_keys['accessToken'],
                org_keys['apiKey']
            )
            soc_account = SocialAccount.objects.get(user=self.old_org_sponsor)
            self.assertEquals(soc_account.extra_data['organizational'], '2')

            # Test member organizational account -- should not switch
            soc_account = SocialAccount.objects.get(user=self.org_member)
            org_status_before_update = soc_account.extra_data['organizational']
            request.user = self.org_member
            BookshareOAuth2Adapter(request).update_org_status(
                org_keys['accessToken'],
                org_keys['apiKey']
            )
            soc_account = SocialAccount.objects.get(user=self.org_member)
            org_status_after_update = soc_account.extra_data['organizational']
            self.assertEquals(org_status_before_update, org_status_after_update)
        else:
            logger.debug('Ignoring "test_adapter_update_org_status()", no access keys.')

    def test_adapter_date_of_birth(self):
        # Test case where the user's date of birth is in the database
        request = self.request_factory.get('/my_account')
        request.user = self.org_member
        birthday = BookshareOAuth2Adapter(request).date_of_birth()
        expected = datetime.strptime(
            ORG_MEMBER_EXTRADATA.get('dateOfBirth', ''), '%Y-%m-%d'
        )
        self.assertEquals(expected, birthday)

        # Test case where date of birth is explicitly "null"
        request.user = self.org_sponsor
        birthday = BookshareOAuth2Adapter(request).date_of_birth()
        self.assertEquals(datetime.now().date(), birthday.date())

        # Test case where date of birth is missing.
        request.user = self.old_org_sponsor
        birthday = BookshareOAuth2Adapter(request).date_of_birth()
        self.assertEquals(datetime.now().date(), birthday.date())

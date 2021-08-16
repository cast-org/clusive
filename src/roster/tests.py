from contextlib import contextmanager
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from eventlog.signals import preference_changed
from .models import Preference, MailingListMember
from .models import Site, Period, ClusiveUser, Roles, ResearchPermissions
# TODO: make sure all tests have helpful messages
from .signals import user_registered


def set_up_test_sites():
    Site.objects.create(name="CAST Collegiate", city="Wakefield", state_or_province="MA", country="USA").save()
    Site.objects.create(name="IDRC Institute", city="Toronto", state_or_province="ON", country="Canada").save()

def set_up_test_periods():
    cast_collegiate = Site.objects.get(name="CAST Collegiate")
    Period.objects.create(name="Universal Design For Learning 101", anon_id='p1', site=cast_collegiate).save()
    Period.objects.create(name="Universal Design For Learning 201", anon_id='p2', site=cast_collegiate).save()

def set_up_test_users():
    user_1 = User.objects.create_user(username="user1", password="password1")
    user_1.save()
    ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST').save()

    user_2 = User.objects.create_user(username="user2", password="password2")
    user_2.save()
    ClusiveUser.objects.create(anon_id="Student2", user=user_2, role='ST').save()

    user_3 = User.objects.create_user(username="t1", password="teacher1")
    user_3.save()
    ClusiveUser.objects.create(anon_id="Teacher1", user=user_3, role='TE').save()

class SiteTestCase(TestCase):
    def setUp(self):
        set_up_test_sites()

    def test_defaults(self):
        """ A created site has expected defaults if not set """
        underdetailed_university = Site.objects.create(name="Underdetailed University")

        self.assertEqual(underdetailed_university.timezone, 'America/New_York')
        self.assertEqual(underdetailed_university.anon_id, None)
        self.assertEqual(underdetailed_university.city, "")
        self.assertEqual(underdetailed_university.state_or_province, "")
        self.assertEqual(underdetailed_university.country, "")

    def test_manual_anon_id(self):
        """ A site can have an anon_id set manually """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.anon_id = "Site1"

        try:
            cast_collegiate.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")

        self.assertEqual(cast_collegiate.anon_id, "Site1")

    def test_anon_id_unique_enforcement(self):
        """ Two sites cannot have the same anon_id"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        idrc_institute = Site.objects.get(name="IDRC Institute")
        cast_collegiate.anon_id = "Site1"
        cast_collegiate.save()

        idrc_institute.anon_id = "Site1"

        try:
            idrc_institute.full_clean()
            self.fail("Validation should have failed due to same anon_id")
        except ValidationError as e:
            self.assertEqual(e.message_dict["anon_id"][0], "Site with this Anon id already exists.")

    def test_timezone_validation(self):
        """ A site won't accept an invalid timezone"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        cast_collegiate.timezone = "America/Boston"

        try:
            cast_collegiate.full_clean()
        except ValidationError as e:
            self.assertEqual(e.message_dict["timezone"][0], "Value 'America/Boston' is not a valid choice.")

    def test_site_deletion_cascade_to_periods(self):
        """ If a site is deleted, all its associated periods are deleted """
        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate)
        Period.objects.create(name="Universal Design For Learning 201", site=cast_collegiate)

        self.assertEqual(Period.objects.count(), 2)

        cast_collegiate.delete()

        self.assertEqual(Period.objects.count(), 0)

class PeriodTestCase(TestCase):

    def setUp(self):
        set_up_test_sites()
        set_up_test_periods()

    def test_site_assignment(self):
        """ Multiple periods can created and assigned to the same site"""

        cast_collegiate = Site.objects.get(name="CAST Collegiate")
        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_201 = Period.objects.get(name="Universal Design For Learning 201")

        self.assertEqual(cast_collegiate.period_set.count(), 2)

        self.assertEqual(udl_101.site.name, 'CAST Collegiate')
        self.assertEqual(udl_201.site.name, 'CAST Collegiate')

    def test_manual_anon_id(self):
        """ A period can have an anon_id set manually """
        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_101.anon_id = "Period1"

        try:
            udl_101.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")

        self.assertEqual(udl_101.anon_id, "Period1")

    def test_anon_id_unique_enforcement(self):
        """ Two periods cannot have the same anon_id"""

        udl_101 = Period.objects.get(name="Universal Design For Learning 101")
        udl_201 = Period.objects.get(name="Universal Design For Learning 201")
        udl_101.anon_id = "Period1"
        udl_101.save()

        udl_201.anon_id = "Period1"

        try:
            udl_201.full_clean()
            self.fail("Validation should have failed due to same anon_id")
        except ValidationError as e:
            self.assertEqual(e.message_dict["anon_id"][0], "Period with this Anonymous identifier already exists.")

class ClusiveUserTestCase(TestCase):
    maxDiff = None

    # Load the preference sets
    fixtures = ['preferencesets.json']

    def setUp(self):
        set_up_test_users()

    def test_defaults(self):
        """ A user has the expected defaults, if not set """
        new_user = User.objects.create_user(username="newuser")
        new_clusive_user = ClusiveUser.objects.create(user=new_user)

        self.assertEqual(new_clusive_user.anon_id, None)
        self.assertEqual(new_clusive_user.permission, ResearchPermissions.TEST_ACCOUNT)
        self.assertEqual(new_clusive_user.role, Roles.GUEST)
        self.check_user_has_default_preferences(new_clusive_user)

    def test_manual_anon_id(self):
        """ A user can have an anon_id set manually """
        clusive_user_1 = ClusiveUser.objects.get(anon_id="Student1")
        clusive_user_1.anon_id = "Student3"

        try:
            clusive_user_1.full_clean()
        except ValidationError as e:
            self.fail("Validation should not have failed")

        self.assertEqual(clusive_user_1.anon_id, "Student3")

    def test_anon_id_unique_enforcement(self):
        """ Two users cannot have the same anon_id """
        clusive_user_1 = ClusiveUser.objects.get(anon_id="Student1")
        clusive_user_2 = ClusiveUser.objects.get(anon_id="Student2")
        clusive_user_1.anon_id = "Student3"
        clusive_user_1.save()

        clusive_user_2.anon_id = "Student3"

        try:
            clusive_user_2.full_clean()
            self.fail("Validation should have failed due to same anon_id")
        except ValidationError as e:
            self.assertEqual(e.message_dict["anon_id"][0], "Clusive user with this Anon id already exists.")

    def test_permissioned_property(self):
        """ The 'is_permissioned' property function returns TRUE for 'permissioned' state and 'false' for all others """
        clusive_user_1 = ClusiveUser.objects.get(anon_id="Student1")
        clusive_user_2 = ClusiveUser.objects.get(anon_id="Student2")

        clusive_user_1.permission = ResearchPermissions.PERMISSIONED

        self.assertTrue(clusive_user_1.is_permissioned)

        nonpermissioned_states = [
            ResearchPermissions.TEST_ACCOUNT,
            ResearchPermissions.PENDING,
            ResearchPermissions.WITHDREW,
            ResearchPermissions.DECLINED
        ]

        for state in nonpermissioned_states:
            clusive_user_2.permission = state
            self.assertFalse(clusive_user_2.is_permissioned)

    def test_adopt_preferences_set(self):
        user = ClusiveUser.objects.get(user__username='user1')
        user.delete_preferences()
        user.adopt_preferences_set("default_display")
        user.adopt_preferences_set("default_reading_tools")
        self.check_user_has_default_preferences(user)

    def check_user_has_default_preferences(self, user):
        default_pref_set = {'fluid_prefs_contrast':'default', 'fluid_prefs_textFont':'default', 'fluid_prefs_textSize':'1', 'fluid_prefs_lineSpace':'1.6', 'cisl_prefs_glossary':'True', 'cisl_prefs_readVoices': '[]', 'cisl_prefs_readSpeed': '1.0'}
        user_prefs = user.get_preferences()

        for p_key in default_pref_set.keys():
            self.assertEqual(default_pref_set[p_key], user.get_preference(p_key).value, "preference '%s' not at expected default value of '%s'" % (p_key, default_pref_set[p_key]))

    def test_preference_convert_from_string(self):
        self.assertEqual(Preference.convert_from_string("[]"), [], "empty array as string was not converted as expected")
        self.assertEqual(Preference.convert_from_string("['Foo', 'Bar', 'Baz']"), ['Foo', 'Bar', 'Baz'], "array of string values as string was not converted as expected")
        self.assertEqual(Preference.convert_from_string("1"), 1, "int as string was not converted as expected")
        self.assertEqual(Preference.convert_from_string("1.57"), 1.57, "float as string was not converted as expected")
        self.assertEqual(Preference.convert_from_string("False"), False, "boolean:False as string was converted as expected")
        self.assertEqual(Preference.convert_from_string("True"), True, "boolean:True as string was converted as expected")

    default_pref_set_json = '{"fluid_prefs_contrast":"default", "fluid_prefs_textFont":"default", "fluid_prefs_textSize":1, "fluid_prefs_lineSpace":1.6, "fluid_prefs_letterSpace":1, "cisl_prefs_glossary":true, "cisl_prefs_scroll":true, "cisl_prefs_readVoices": [], "cisl_prefs_readSpeed": 1.0, "cisl_prefs_translationLanguage": "default"}'

    def test_preference_sets(self):
        # delete any existing preferences so we're starting with a clean set
        user = ClusiveUser.objects.get(user__username='user1')
        user.delete_preferences()

        login = self.client.login(username='user1', password='password1')

        self.client.post('/account/prefs/profile', {'adopt': 'default_reading_tools', 'eventId': None}, content_type='application/json')

        self.client.post('/account/prefs/profile', {'adopt': 'default_display', 'eventId': None}, content_type='application/json')

        response = self.client.get('/account/prefs')

        self.assertJSONEqual(response.content, self.default_pref_set_json, 'Changing to default preferences profile did not return expected response')

    def test_preferences(self):
        # delete any existing preferences so we're starting with a clean set
        user = ClusiveUser.objects.get(user__username='user1')
        user.delete_preferences()

        login = self.client.login(username='user1', password='password1')

        # Setting one preference
        response = self.client.post('/account/prefs', {'foo': 'bar'}, content_type='application/json')
        self.assertJSONEqual(response.content, {'success': 1}, 'Setting pref did not return expected response')

        response = self.client.get('/account/prefs')

        self.assertContains(response, '"foo": "bar"')

        # Now that defaults are established, we should get accurate event logging
        with catch_signal(preference_changed) as handler:
            response = self.client.post('/account/prefs', {'foo': 'baz'}, content_type='application/json')
            self.assertJSONEqual(response.content, {'success': 1}, 'Setting pref to new value did not return expected response')

            response = self.client.post('/account/prefs', {'foo': 'baz'}, content_type='application/json')
            self.assertJSONEqual(response.content, {'success': 1}, 'Setting pref to same value did not return expected response')

        # Setting two preferences where one already exists at the same value; handler should
        # still only get triggered once
        with catch_signal(preference_changed) as handler:
            response = self.client.post('/account/prefs', {'foo': 'bar', 'baz': 'lur'}, content_type='application/json')
            self.assertJSONEqual(response.content, {'success': 1}, 'Setting prefs did not return expected response')

            response = self.client.get('/account/prefs')
            # TODO: currently default settings are always applied, so more than this one item is returned.
            # self.assertJSONEqual(response.content, {'foo': 'bar', 'baz': 'lur'}, 'Fetching prefs did not return values that were set')
            self.assertContains(response, '"foo": "bar", "baz": "lur"')

    def test_non_self_created_user_not_added_to_mailing_list(self):
        user_registered.send(self.__class__, clusive_user=ClusiveUser.objects.get(user__username='user1'))
        subscriptions = MailingListMember.objects.all()
        self.assertEqual(0, len(subscriptions))

    def test_registered_user_added_to_mailing_list(self):
        user = ClusiveUser.objects.get(user__username='user1')
        user.permission = ResearchPermissions.SELF_CREATED
        user.save()
        user_registered.send(self.__class__, clusive_user=user)
        subscriptions = MailingListMember.objects.all()
        self.assertEqual(1, len(subscriptions))


class PageTestCases(TestCase):

        def setUp(self):
            set_up_test_sites()
            set_up_test_periods()
            set_up_test_users()

        def test_login_page(self):
            url = reverse('login')
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            html = response.content.decode('utf8')
            self.assertIn('Username', html)
            self.assertIn('Password', html)

        def test_logged_in_message(self):
            login = self.client.login(username='user1', password='password1')
            self.assertTrue(login)
            url = reverse('index')
            response = self.client.get(url, follow=True)
            html = response.content.decode('utf8')
            self.assertIn('user1', html)
            self.assertIn('Dashboard', html)

        def test_logout_url(self):
            login = self.client.login(username='user1', password='password1')
            self.assertTrue(login)

            url = reverse('index')
            response = self.client.get(url, follow=True)
            html = response.content.decode('utf8')
            self.assertIn('user1', html)

            url = reverse('logout')
            response = self.client.get(url, follow=True)

            self.assertEqual(response.status_code, 200)
            html = response.content.decode('utf8')
            self.assertIn('Username', html)
            self.assertIn('Password', html)

        def test_manage_page_denied_to_students(self):
            login = self.client.login(username='user1', password='password1')
            response = self.client.get(reverse('manage'))
            self.assertEqual(403, response.status_code, 'Manage page should be denied to students')

        def test_manage_page_denied_if_not_my_period(self):
            user = ClusiveUser.objects.get(anon_id='Teacher1')
            user.periods.add(Period.objects.get(anon_id='p1'))
            login = self.client.login(username='user1', password='password1')
            response = self.client.get(reverse('manage',
                                               kwargs={'period_id': Period.objects.get(anon_id='p2').id }))
            self.assertEqual(403, response.status_code, 'Managing periods you are not in should be denied')

        def test_manage_page_renders(self):
            user = ClusiveUser.objects.get(anon_id='Teacher1')
            user.periods.add(Period.objects.get(anon_id='p1'))
            login = self.client.login(username=user.user.username, password='teacher1')
            response = self.client.get(reverse('manage'))
            self.assertContains(response, 'Universal Design For Learning 101', status_code=200)

        def test_manage_edit_page_denied_to_students(self):
            login = self.client.login(username='user1', password='password1')
            response = self.client.get(reverse('manage_edit',
                                               kwargs={'period_id': Period.objects.get(anon_id='p1').id,
                                                       'pk' : ClusiveUser.objects.get(anon_id='Student2').id}))
            self.assertEqual(403, response.status_code, 'Manage_edit page should be denied to students')

        def test_manage_edit_page_denied_if_not_my_period(self):
            # Make teacher part of p1, but try to edit p2 student
            user = ClusiveUser.objects.get(anon_id='Teacher1')
            user.periods.add(Period.objects.get(anon_id='p1'))
            login = self.client.login(username=user.user.username, password='teacher1')
            response = self.client.get(reverse('manage_edit',
                                               kwargs={'period_id': Period.objects.get(anon_id='p2').id,
                                                       'pk' : ClusiveUser.objects.get(anon_id='Student2').id}))
            self.assertEqual(403, response.status_code, 'Managing periods you are not in should be denied')

        def test_manage_edit_page_denied_if_target_not_in_period(self):
            p1 = Period.objects.get(anon_id='p1')
            p2 = Period.objects.get(anon_id='p2')
            # Teacher is in p1
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            teacher.periods.add(p1)
            # Student is in p2
            student = ClusiveUser.objects.get(anon_id='Student2')
            student.periods.add(p2)
            student.save()
            # Call edit page with p1 but student is in p2
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_edit',
                                               kwargs={'period_id': p1.id,
                                                       'pk' : student.id}))
            self.assertEqual(403, response.status_code, 'Should be denied')

        def test_manage_edit_page_renders(self):
            p1 = Period.objects.get(anon_id='p1')
            # Teacher in p1
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            teacher.periods.add(p1)
            # Student also in p1
            student = ClusiveUser.objects.get(anon_id='Student2')
            student.periods.add(p1)
            # Make call correctly
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_edit',
                                               kwargs={'period_id': p1.id,
                                                       'pk' : student.id}))
            self.assertContains(response, 'user2', status_code=200)
            # Should not show anonymous ID on the page
            self.assertNotContains(response, 'Student2')

        def test_manage_edit_period_page_renders(self):
            p1 = Period.objects.get(anon_id='p1')
            # Teacher in p1
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            teacher.periods.add(p1)
            # Make call correctly
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_edit_period',
                                               kwargs={'pk': p1.id}))
            # Shows name of period
            self.assertContains(response, 'Universal Design For Learning 101', status_code=200)
            # Should not show anonymous ID on the page
            self.assertNotContains(response, 'p1')

        def test_manage_edit_period_page_denied_to_students(self):
            login = self.client.login(username='user1', password='password1')
            response = self.client.get(reverse('manage_edit_period',
                                               kwargs={'pk': Period.objects.get(anon_id='p1').id}))
            self.assertEqual(403, response.status_code, 'Manage_edit_period page should be denied to students')

        def test_manage_edit_period_page_denied_to_teacher_not_in_period(self):
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_edit_period',
                                               kwargs={'pk': Period.objects.get(anon_id='p1').id}))
            self.assertEqual(403, response.status_code, 'Manage_edit_period page should be denied to students')

        def test_manage_create_period_page_renders(self):
            p1 = Period.objects.get(anon_id='p1')
            # Teacher in p1
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            teacher.periods.add(p1)
            # Make call correctly
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_create_period'))
            self.assertTemplateUsed(response, 'roster/manage_create_period.html')

        def test_manage_create_period_page_denied_to_students(self):
            p1 = Period.objects.get(anon_id='p1')
            student = ClusiveUser.objects.get(anon_id='Student1')
            student.periods.add(p1)
            login = self.client.login(username=student.user.username, password='password1')
            response = self.client.get(reverse('manage_create_period'))
            self.assertEqual(403, response.status_code, 'Manage_create_period page should be denied to students')

        def test_manage_create_user_page_renders(self):
            p1 = Period.objects.get(anon_id='p1')
            teacher = ClusiveUser.objects.get(anon_id='Teacher1')
            teacher.periods.add(p1)
            login = self.client.login(username=teacher.user.username, password='teacher1')
            response = self.client.get(reverse('manage_create_user',
                                               kwargs={'period_id': Period.objects.get(anon_id='p1').id}))
            self.assertTemplateUsed(response, 'roster/manage_create_user.html')
            self.assertTemplateUsed(response, 'roster/partial/user_form.html')

        def test_manage_create_user_page_denied_to_students(self):
            p1 = Period.objects.get(anon_id='p1')
            student = ClusiveUser.objects.get(anon_id='Student1')
            student.periods.add(p1)
            login = self.client.login(username=student.user.username, password='password1')
            response = self.client.get(reverse('manage_create_user',
                                               kwargs={'period_id': Period.objects.get(anon_id='p1').id}))
            self.assertEqual(403, response.status_code, 'Manage_create_user page should be denied to students')


@contextmanager
def catch_signal(signal):
    """Catch django signal and return the mocked call."""
    handler = mock.Mock()
    signal.connect(handler)
    yield handler
    signal.disconnect(handler)

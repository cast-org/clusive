import logging
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from roster.models import ClusiveUser, Roles

from .models import TipType, TEACHER_ONLY_TIPS, DASHBOARD_TIPS, READING_TIPS, \
    LIBRARY_TIPS, WORD_BANK_TIPS, MANAGE_TIPS, RESOURCES_TIPS, \
    PAGES_WITH_OWN_TIP, PAGE_TIPS_MAP, TipHistory
import pdb

logger = logging.getLogger(__name__)

# TODO: Load these from tooltips.json?
TIP_TYPE_NAMES = [
    'student_reactions',
    'reading_data',
    'activity',
    'manage',
    'switch',
    'settings',
    'readaloud',
    'context',
    'thoughts',
    'wordbank',
    'view',
    'filters',
    'search',
    'book_actions',
    'resources'
]

STUDENT_CAN_SHOW = {
    'Dashboard': ['student_reactions', 'reading_data'],
    'Reading': ['switch', 'settings', 'readaloud', 'context', 'thoughts', 'wordbank'],
    'Library': ['view', 'filters', 'search'],
    'Wordbank': ['wordbank'],
}

TEACHER_CAN_SHOW = {
    'Dashboard': ['student_reactions', 'reading_data', 'activity', 'manage'],
    'Reading': ['switch', 'settings', 'readaloud', 'context', 'wordbank'],
    'Library': ['view', 'filters', 'search', 'book_actions'],
    'Wordbank': ['wordbank'],
    'Resources': ['resources'],
    'Manage': ['manage'],
}

PARENT_CAN_SHOWN = TEACHER_CAN_SHOW

NO_SUCH_PAGE = 'My backyard'

def set_up_users():
    # Users - a student, a teacher, and a parent
    student = User.objects.create_user(username="student", password="student_pass")
    student.save()
    ClusiveUser.objects.create(
        anon_id="Student", user=student, role=Roles.STUDENT
    ).save()

    teacher = User.objects.create_user(username="teacher", password="teacher_pass")
    teacher.save()
    ClusiveUser.objects.create(
        anon_id="Teacher", user=teacher, role=Roles.TEACHER
    ).save()

    parent = User.objects.create_user(username="parent", password="parent_pass")
    parent.save()
    ClusiveUser.objects.create(
        anon_id="Parent", user=parent, role=Roles.PARENT
    ).save()

def set_up_pages():
    # Pages
    page_names = [
        'Dashboard', 'Reading', 'Library', 'Wordbank', 'Manage', 'Resources',
        NO_SUCH_PAGE
    ]
    return (NO_SUCH_PAGE, page_names)

def set_up_tip_types():
        # TipType
        priority = 1
        interval = timedelta(days=7)
        for tip_name in TIP_TYPE_NAMES:
            TipType.objects.create(
                name=tip_name, priority=priority, interval=interval, max=3
            ).save()
            priority += 1

class TipTypeTestCase(TestCase):
    def setUp(self):
        set_up_users()
        set_up_tip_types()
        self.no_such_page, self.page_names = set_up_pages()

    def look_up_expected(self, clusive_user, page_name, tip):
        role = clusive_user.role
        if role == Roles.STUDENT:
            return tip.name in STUDENT_CAN_SHOW.get(page_name, [])
        elif role == Roles.TEACHER or role == Roles.PARENT:
            return tip.name in TEACHER_CAN_SHOW.get(page_name, [])
        else:
            return False

    def can_show_tips(self, clusive_user):
        """
        Tests all tip types on all pages for the given user.
            - testing TipType.can_show(page, version_count, user).
            - note that only version counts greater than one are tested here.
            - TipType.can_show(page: str, version_count: int, user: ClusiveUser)
        """
        version_count = 3
        for page_name in self.page_names:
            for tip in TipType.objects.all():
                actual = tip.can_show(page_name, version_count, clusive_user)
                expected = self.look_up_expected(clusive_user, page_name, tip)
                self.assertEqual(
                    actual, expected,
                    f"Can show {tip.name} tip for {clusive_user.user.username} on {page_name} page"
                )

    def test_can_show(self):
        """
        Test all users for all tips on all pages with a version count greater
        than 1 (one).
        """
        for clusive_user in ClusiveUser.objects.all():
            self.can_show_tips(clusive_user)

    def test_can_show_switch_single_version(self):
        """
        Special case: Test all users for the `switch` tip with only one book
        version and for the 'Reading' page only.  It should always be `False`.
        """
        for clusive_user in ClusiveUser.objects.all():
            switch_tip = TipType.objects.get(name='switch')
            actual = switch_tip.can_show('Reading', 1, clusive_user)
            self.assertFalse(
                actual,
                f"Can show 'switch' tip for {clusive_user.user.username} on Reading page"
            )


class TipHistoryTestCase(TestCase):

    def setUp(self):
        set_up_users()
        set_up_tip_types()
        self.no_such_page, self.page_names = set_up_pages()

    def test_initialize_histories(self):
        """ Test initializaion of TipHistory objects for all users """
        for clusive_user in ClusiveUser.objects.all():
            TipHistory.initialize_histories(clusive_user)
            histories = TipHistory.objects.filter(user=clusive_user)
            for history in histories:
                self.assertTrue(history.type.name in TIP_TYPE_NAMES, 'Check tip type')
                self.assertEqual(history.show_count, 0, 'Check initial history show_count')
                self.assertEqual(history.last_attempt, None, 'Check initial last_attempt')
                self.assertEqual(history.last_show, None, 'Check initial last_show')
                self.assertEqual(history.last_action, None, 'Check initial last_action')
            # Check that there is one history per tip type
            self.assertEqual(len(histories), len(TIP_TYPE_NAMES), 'One-to-one mapping of tip histories and tip types')

    def test_register_show(self):
        START_DELTA = 250 # msec
        tips = TipType.objects.all()
        for clusive_user in ClusiveUser.objects.all():
            TipHistory.initialize_histories(clusive_user)
            # Loop to set the `last_show` times for the user.  The `last_show`
            # has a base `start_time` of `now()` and is constantly increased by
            # `add_delta` msec so that the times will be different across users
            # and tips, but in a predictable way.
            start_time = timezone.now()
            add_delta = START_DELTA
            for tip in tips:
                delta = timedelta(milliseconds=add_delta)
                TipHistory.register_show(clusive_user, tip.name, start_time + delta)
                add_delta += START_DELTA

            # Loop again to test that the `show_count` and `last_show` times are
            # as expected.
            add_delta = START_DELTA
            for tip in tips:
                delta = timedelta(milliseconds=add_delta)
                history = TipHistory.objects.get(user=clusive_user, type=tip)
                self.assertEquals(history.show_count, 1, "Check show_count for {history}")
                # The actual timestamp set by `TipHistory.register_show()` is
                # _not_ the timestamp passed in but `now()`, which is likely
                #  microseconds later.  The tests considers the `last_show` time
                # correct if is are within `START_DELTA` msec of the expected
                # timestamp
                expected_last_show = start_time + delta
                # Test equality ignoring the microseconds
                self.assertEquals(
                    history.last_show.replace(microsecond=0),
                    expected_last_show.replace(microsecond=0),
                    f"Check last_show for {history} ignoring microsecond field"
                )
                # Test that ths microseconds difference is within START_DELTA
                diff = abs(history.last_show.microsecond - expected_last_show.microsecond)/1000
                self.assertTrue(diff < START_DELTA, f"Check last_show microsecond field for {history}")
                # Test that a time earlier than what is stored in the history
                # will not change the time.
                current_last_show = history.last_show
                TipHistory.register_show(clusive_user, tip.name, start_time)
                self.assertEquals(
                    history.last_show, current_last_show,
                    f"Check last_show for {history} when setting to an earlier time than recorded in the history"
                )

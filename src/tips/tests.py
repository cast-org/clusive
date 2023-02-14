import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from roster.models import ClusiveUser, Roles
from .models import TipType, TipHistory

logger = logging.getLogger(__name__)

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
    'resources',
]

NO_SUCH_PAGE = 'My backyard'
PAGE_NAMES = [
    'Dashboard',
    'Reading',
    'Library',
    'Wordbank',
    'Manage',
    'Resources',
    'ResourceReading',
    NO_SUCH_PAGE,
]

# For testing TipType.can_show().  Also, the tip types that can show for guest
# users is the same as for students.  Similarly for which tips typs can show
# for teachers and parents
STUDENT_OR_GUEST_CAN_SHOW = {
    'Dashboard': ['student_reactions', 'reading_data'],
    'Reading': ['switch', 'settings', 'readaloud', 'context', 'thoughts', 'wordbank'],
    'Library': ['view', 'filters', 'search'],
    'Wordbank': ['wordbank'],
    # can_show() is true, but doesn't really matter since student shouldn't ever end up on the ResourceReading page:
    'ResourceReading': ['settings', 'readaloud', 'context', 'wordbank'],
}

TEACHER_OR_PARENT_CAN_SHOW = {
    'Dashboard': ['student_reactions', 'reading_data', 'activity', 'manage'],
    'Reading': ['switch', 'settings', 'readaloud', 'context', 'thoughts', 'wordbank'],
    'Library': ['view', 'filters', 'search', 'book_actions'],
    'Wordbank': ['wordbank'],
    'Resources': ['resources'],
    'Manage': ['manage'],
    'ResourceReading': ['settings', 'readaloud', 'context', 'wordbank'],
}

START_DELTA = 250 # msec
ONE_WEEK = timedelta(days=7)
LESS_THAN_A_WEEK = timedelta(days=6, hours=23, minutes=55)
SIX_MINUTES = timedelta(minutes=6)
MINUTE_TOLERANCE = timedelta(minutes=1)

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

    guest = User.objects.create_user(username="guest", password="guest_pass")
    guest.save()
    ClusiveUser.objects.create(
        anon_id="Guest", user=guest, role=Roles.GUEST
    ).save()

def set_up_tip_types():
        # TipType
        priority = 1
        interval = timedelta(days=7)
        for tip_name in TIP_TYPE_NAMES:
            TipType.objects.create(
                name=tip_name, priority=priority, interval=interval, max=3
            ).save()
            priority += 1

def init_history_as_ready_to_show(tip_history):
    """
    Configure the given TipHistory with reasonable values but so that its
    `ready_to_show()` still returns True.  The `show_count` is set to one less
    than the maximum count, `last_attempt` to more than five minutes ago (six
    minutes ago), and `last_show` and `last_action` to a week ago.
    """
    now = timezone.now()
    tip_history.show_count = tip_history.type.max - 1
    tip_history.last_attempt = now - SIX_MINUTES
    tip_history.last_show = tip_history.last_action = now - ONE_WEEK
    return tip_history


class TipTypeTestCase(TestCase):
    def setUp(self):
        set_up_users()
        set_up_tip_types()

    def look_up_expected(self, clusive_user, page_name, tip):
        role = clusive_user.role
        if role == Roles.STUDENT or role == Roles.GUEST:
            return tip.name in STUDENT_OR_GUEST_CAN_SHOW.get(page_name, [])
        elif role == Roles.TEACHER or role == Roles.PARENT:
            return tip.name in TEACHER_OR_PARENT_CAN_SHOW.get(page_name, [])
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
        for page_name in PAGE_NAMES:
            for tip in TipType.objects.all():
                actual = tip.can_show(page=page_name, is_pdf=False, version_count=version_count, user=clusive_user, stats=None)
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
            actual = switch_tip.can_show(page='Reading', is_pdf=False, version_count=1, user=clusive_user, stats=None)
            self.assertFalse(
                actual,
                f"Can show 'switch' tip for {clusive_user.user.username} on Reading page"
            )


class TipHistoryTestCase(TestCase):

    def setUp(self):
        set_up_users()
        set_up_tip_types()

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
                # _not_ the timestamp passed in but `now()`, which is possibly
                # seconds later.  The tests consider the `last_show` time is
                # set properly if it is the same timestamp within a minute.
                expected_last_show = start_time + delta
                self.assertTrue(
                    (history.last_show - expected_last_show) < MINUTE_TOLERANCE,
                    f"Check last_show for {history} is within a minute of expected; actual: {history.last_show}, expected: {expected_last_show}"
                )
                # Test that a time earlier than what is stored in the history
                # will not change the time.
                current_last_show = history.last_show
                TipHistory.register_show(clusive_user, tip.name, start_time)
                self.assertEquals(
                    history.last_show, current_last_show,
                    f"Check last_show for {history} when setting to an earlier time than recorded in the history"
                )

    def test_register_action(self):
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
                TipHistory.register_action(clusive_user, tip.name, start_time + delta)
                add_delta += START_DELTA

            # Loop again to test that the `last_action` times are as expected
            # Unlike `last_show`, they should match the timestamp passsed to
            # `TipHistory.register_action()` above.
            # as expected.
            add_delta = START_DELTA
            for tip in tips:
                delta = timedelta(milliseconds=add_delta)
                history = TipHistory.objects.get(user=clusive_user, type=tip)
                self.assertEquals(
                    history.last_action, start_time + delta,
                    f"Check last_action for {history}"
                )
                add_delta += START_DELTA
                # Test that a time earlier than what is stored in the history
                # will not change the time.
                current_last_action = history.last_action
                TipHistory.register_action(clusive_user, tip.name, start_time)
                self.assertEquals(
                    history.last_action, current_last_action,
                    f"Check last_action for {history} when setting to an earlier time than recorded in the history"
                )

    def test_ready_to_show(self):
        tips = TipType.objects.all()
        for clusive_user in ClusiveUser.objects.all():
            TipHistory.initialize_histories(clusive_user)
            # All tips should be ready_to_show() at this point
            for history in TipHistory.objects.filter(user=clusive_user):
                self.assertTrue(history.ready_to_show(), f"Check just initialized history {history}")

        # Using the teacher user, configure their 'activity' TipHistory with
        # values such that it will show.
        teacher = ClusiveUser.objects.get(role=Roles.TEACHER)
        tip = TipType.objects.get(name='activity')
        history = init_history_as_ready_to_show(
            TipHistory.objects.get(type=tip, user=teacher)
        )
        self.assertTrue(history.ready_to_show(), f"Check {history} configured as ready to show")
        # Set each of `history`'s fields in turn such that ready_to_show() will
        # return False
        # Test `show_count`
        history.show_count = tip.max
        self.assertFalse(history.ready_to_show(), f"Check {history} maximum number of times to show")

        # Test `last_attempt`
        history = init_history_as_ready_to_show(history)
        history.last_attempt = timezone.now() - timedelta(minutes=4)
        self.assertFalse(history.ready_to_show(), f"Check {history} last attempt less than five minutes ago")

        # Test `last_show`
        history = init_history_as_ready_to_show(history)
        history.last_show = timezone.now() - LESS_THAN_A_WEEK
        self.assertFalse(history.ready_to_show(), f"Check {history} last shown less than a week ago")

        # Test `last_action`
        history = init_history_as_ready_to_show(history)
        history.last_action = timezone.now() - LESS_THAN_A_WEEK
        self.assertFalse(history.ready_to_show(), f"Check {history} last action less than a week ago")

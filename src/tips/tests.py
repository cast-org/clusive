import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from roster.models import ClusiveUser, Roles

from .models import TipType, TEACHER_ONLY_TIPS, DASHBOARD_TIPS, READING_TIPS, \
    LIBRARY_TIPS, WORD_BANK_TIPS, MANAGE_TIPS, RESOURCES_TIPS, \
    PAGES_WITH_OWN_TIP, PAGE_TIPS_MAP

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


class TipTypeTestCase(TestCase):
    def setUp(self):
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

        # Pages
        self.no_such_page = 'MyBackyard'
        self.page_names = [
            'Dashboard', 'Reading', 'Library', 'Wordbank', 'Manage', 'Resources',
            self.no_such_page
        ]

        # TipTypes
        priority = 1
        interval = timedelta(days=7)
        for tip_name in TIP_TYPE_NAMES:
            TipType.objects.create(
                name=tip_name, priority=priority, interval=interval, max=3
            ).save()
            priority += 1

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

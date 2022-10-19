import logging
from datetime import timedelta

from django.db import models
from django.utils import timezone

from roster.models import ClusiveUser, UserStats, Roles

logger = logging.getLogger(__name__)

TEACHER_ONLY_TIPS = [
    'book_actions',
    'activity',
    'student_reactions',
    'reading_details',
    'reading_data',
    'manage',
    'resources',
]

DASHBOARD_TIPS = [
    'activity',
    'student_reactions',
    'reading_data',
    'thoughts',
    'manage',
]

LIBRARY_TIPS = [
    'view',
    'book_actions',
    'filters',
    'search',
]

READING_TIPS = [
    'context',
    'settings',
    'readaloud',
    'wordbank',
    'switch',   # Note: special case requires versions -- see TipType.can_show()
]


class TipType(models.Model):
    """
    A tip is a short message that is displayed to introduce or remind users of a feature.
    They are shown with a certain frequency (eg, once a week), no more than one at a time,
    with certain visibility restrictions. Showing of tips can be pre-empted by related user actions:
    we don't need to remind users of features they have recently used.
    """
    name = models.CharField(max_length=20, unique=True)
    priority = models.PositiveSmallIntegerField(unique=True)
    max = models.PositiveSmallIntegerField(verbose_name='Maximum times to show')
    interval = models.DurationField(verbose_name='Interval between shows')

    def can_show(self, page: str, version_count: int, user: ClusiveUser):
        """Test whether this tip can be shown on a particular page"""
        # Teacher/parent-only tips
        if user.role == Roles.STUDENT and self.name in TEACHER_ONLY_TIPS:
            return False
        # Switch tooltip requires multiple versions
        if self.name == 'switch':
            return page == 'Reading' and version_count > 1
        # Most tooltips need to check if on correct page
        if self.name in DASHBOARD_TIPS:
            return page == 'Dashboard'
        if self.name in LIBRARY_TIPS:
            return page == 'Library'
        if self.name in READING_TIPS:
            return page == 'Reading'
        if self.name == 'resources':
            return page == 'Resources'
        if self.name == 'manage':
            return page == 'Manage'
        if self.name == 'wordbank':
            return page == 'WordBank'
        # Unknown tip never shown
        return False

    def __str__(self):
        return '<TipType %s>' % self.name


class TipHistory(models.Model):
    type = models.ForeignKey(to=TipType, on_delete=models.CASCADE)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    show_count = models.PositiveSmallIntegerField(default=0)
    # An "attempt" is when we send this tip to the browser to be displayed. However, it may be off-screen or hidden.
    last_attempt = models.DateTimeField(null=True)
    # A "show" is when the user actually saw the tip.
    last_show = models.DateTimeField(null=True)
    # This is when the use took some related action.
    # Tips should not be shown if the user recently did the action so doesn't need reminding.
    last_action = models.DateTimeField(null=True)

    class Meta:
        unique_together = ('type', 'user')
        verbose_name = 'tip history'
        verbose_name_plural = "tip histories"

    def __str__(self):
        return '<TipHistory %s:%s>' % (self.type.name, self.user.user.username)

    def ready_to_show(self):
        # Already shown the maximum number of times?
        if self.show_count >= self.type.max:
            return False
        now = timezone.now()
        # Last attempt was very recent, may still be waiting to get the confirmation?
        if self.last_attempt and (self.last_attempt + timedelta(minutes=5)) > now:
            return False
        # Shown too recently?
        if self.last_show and (self.last_show + self.type.interval) > now:
            return False
        # Related action too recently?
        if self.last_action and (self.last_action + self.type.interval) > now:
            return False
        return True

    def register_attempt(self):
        self.last_attempt = timezone.now()
        self.save()

    @classmethod
    def initialize_histories(cls, user: ClusiveUser):
        """Make sure given user has appropriate TipHistory objects"""
        types = TipType.objects.all()
        histories = TipHistory.objects.filter(user=user)
        have_history = [h.type for h in histories]
        for type in types:
            if not type in have_history:
                TipHistory(user=user, type=type).save()

    @classmethod
    def register_show(cls, user: ClusiveUser, tip: str, timestamp):
        try:
            type = TipType.objects.get(name=tip)
            history = TipHistory.objects.get(user=user, type=type)
            history.show_count += 1
            if not history.last_show or timestamp > history.last_show:
                history.last_show = timezone.now()
            history.save()
        except TipType.DoesNotExist:
            logger.error('Tip-related action received with non-existent TipType: %s', tip)
        except TipHistory.DoesNotExist:
            logger.error('Could not find TipHistory object for user %s, type %s', user, tip)

    @classmethod
    def register_action(cls, user: ClusiveUser, action: str, timestamp):
        try:
            type = TipType.objects.get(name=action)
            history = TipHistory.objects.get(user=user, type=type)
            if not history.last_action or timestamp > history.last_action:
                history.last_action = timestamp
                history.save()
        except TipType.DoesNotExist:
            logger.error('Tip-related action received with non-existent TipType: %s', action)
        except TipHistory.DoesNotExist:
            logger.error('Could not find TipHistory object for user %s, type %s', user, action)

    @classmethod
    def available_tips(cls, user: ClusiveUser, page: str, version_count: int):
        """Return all tips that are currently available to show this user."""

        # All tips are currently disallowed on the user's FIRST reading page view
        if page == 'Reading':
            stats: UserStats
            stats = UserStats.for_clusive_user(user)
            if stats.reading_views < 1:
                return []

        # Check tip history to see which are ready to be shown
        histories = TipHistory.objects.filter(user=user).order_by('type__priority')
        return [h for h in histories
                if h.type.can_show(page=page, version_count=version_count, user=user)
                and h.ready_to_show()]

    @classmethod
    def get_tip_to_show(cls, clusive_user: ClusiveUser, page: str, version_count=0):
        available = TipHistory.available_tips(clusive_user, page, version_count)
        if available:
            first_available = available[0]
            logger.debug('Displaying tip: %s', first_available)
            first_available.register_attempt()
            return first_available.type
        else:
            return None


class CallToAction(models.Model):
    """
    A Call To Action is a message that is displayed to prompt a certain action.
    Unlike a Tip, a CTA does not have an interval between showings.
    It will continue to be displayed until the action is taken, up to a max number of times, and then never again.
    The "enabled" field can be used to remove old calls to action without deleting their data,
    or put in a placeholder to begin at a later date.
    """
    name = models.CharField(max_length=20, unique=True)
    priority = models.PositiveSmallIntegerField(unique=True)
    enabled = models.BooleanField(default=False)
    max = models.PositiveSmallIntegerField(verbose_name='Maximum times to show', null=True)

    def can_show(self, page: str):
        """
        Test whether this CTA is enabled and can be shown on a particular page.
        Currently, they are all enabled only on the dashboard so this is trivial.
        """
        return self.enabled and page == 'Dashboard'

    def __str__(self):
        return '<CTA %s>' % self.name


class CompletionType:
    """Why this CTA is listed as completed. Was the action taken or not?"""
    TAKEN    = 'T'
    DECLINED = 'D'
    MAX      = 'M'

    CHOICES = (
        (TAKEN, 'Action Taken'),
        (DECLINED, 'Declined'),
        (MAX, 'Max shows'),
    )


class CTAHistory(models.Model):
    type = models.ForeignKey(to=CallToAction, on_delete=models.CASCADE)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    show_count = models.PositiveSmallIntegerField(default=0)
    first_show = models.DateTimeField(null=True, blank=True)
    last_show = models.DateTimeField(null=True, blank=True)
    completed = models.DateTimeField(null=True, blank=True)
    completion_type = models.CharField(max_length=8, null=True, blank=True, choices=CompletionType.CHOICES)

    class Meta:
        unique_together = ('type', 'user')
        verbose_name = 'CTA history'
        verbose_name_plural = "CTA histories"

    def __str__(self):
        return '<CTAHistory %s:%s>' % (self.type.name, self.user.anon_id)

    def ready_to_show(self, user_stats: UserStats):
        if self.completed:
            return False
        # Welcome panel. Generally the first thing shown.
        if self.type.name == 'welcome':
            return True
        # Bookshare note. Show any time, but not to guests.
        if self.type.name == 'bookshare':
            return self.user.role != Roles.GUEST
        # Summer Reading Challenge "congrats" panel: Students only. Requires >100 minutes active reading time.
        if self.type.name == 'summer_reading_st':
            if self.user.role != Roles.STUDENT:
                return False
            return user_stats.active_duration and user_stats.active_duration > timedelta(minutes=100)
            return True
        # Summer reading promo for Guest users - shown to all guests
        if self.type.name == 'summer_reading_gu':
            return self.user.role == Roles.GUEST
        # Demographics, shown at any time, for parent & teacher.
        if self.type.name == 'demographics':
            return self.user.role == Roles.PARENT or self.user.role == Roles.TEACHER
        # Star Rating: any registered user, > 60 minutes active or > 3 logins.
        if self.type.name == 'star_rating':
            if self.user.role == Roles.GUEST:
                return False
            if user_stats.logins > 1:
                return True
            return user_stats.active_duration and user_stats.active_duration > timedelta(minutes=30)
        # Unknown type
        logger.warning('Unimplemented CTA type: %s', self)
        return False

    def show(self):
        """Update stats when this CTA is displayed to this user"""
        self.show_count += 1
        now = timezone.now()
        if not self.first_show:
            self.first_show = now
        self.last_show = now
        if self.type.max and self.show_count >= self.type.max:
            self.completed = now
            self.completion_type = CompletionType.MAX
        self.save()

    @classmethod
    def initialize_histories(cls, user: ClusiveUser):
        """Make sure given user has appropriate CTAHistory objects"""
        types = CallToAction.objects.all()
        histories = cls.objects.filter(user=user)
        have_history = [h.type for h in histories]
        for type in types:
            if not type in have_history:
                cls(user=user, type=type).save()

    @classmethod
    def register_action(cls, user: ClusiveUser, cta_name: str, completion_type: CompletionType,
                        timestamp=timezone.now()):
        try:
            type = CallToAction.objects.get(name=cta_name)
            history = cls.objects.get(user=user, type=type)
            if not history.completed:
                history.completed = timestamp
                history.completion_type = completion_type
                history.save()
        except CallToAction.DoesNotExist:
            logger.error('CTA-related action received with non-existent CTA: %s', cta_name)
        except cls.DoesNotExist:
            logger.error('Could not find CTAHistory object for user %s, type %s', user, cta_name)

    @classmethod
    def available_ctas(cls, user: ClusiveUser, page: str):
        """Return all Calls To Action that are currently available to show this user."""

        # Check history to see which are ready to be shown
        histories = cls.objects.filter(user=user).order_by('type__priority')
        user_stats = UserStats.objects.get(user=user)

        return [h for h in histories
                if h.type.can_show(page)
                and h.ready_to_show(user_stats)]

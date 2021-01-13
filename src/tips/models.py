import logging

from django.db import models
from django.utils import timezone

from roster.models import ClusiveUser, UserStats

logger = logging.getLogger(__name__)


class TipType(models.Model):
    name = models.CharField(max_length=20, unique=True)
    priority = models.PositiveSmallIntegerField(unique=True)
    max = models.PositiveSmallIntegerField(verbose_name='Maximum times to show')
    interval = models.DurationField(verbose_name='Interval between shows')

    def can_show(self, page: str, version_count: int):
        """Test whether this tip can be shown on a particular page"""
        if self.name == 'switch':
            return page == 'Reading' and version_count > 1
        if self.name in ['context', 'settings', 'readaloud', 'wordbank']:
            return page == 'Reading'
        return False

    def __str__(self):
        return '<TipType %s>' % self.name


class TipHistory(models.Model):
    type = models.ForeignKey(to=TipType, on_delete=models.CASCADE)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.CASCADE, db_index=True)
    show_count = models.PositiveSmallIntegerField(default=0)
    last_show = models.DateTimeField(null=True)
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
        # Shown too recently?
        if self.last_show and (self.last_show + self.type.interval) > now:
            return False
        # Related action too recently?
        if self.last_action and (self.last_action + self.type.interval) > now:
            return False
        return True

    def show(self):
        self.show_count += 1
        self.last_show = timezone.now()
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
                logger.debug('First reading page view. No tips')
                return []

        # Check tip history to see which are ready to be shown
        histories = TipHistory.objects.filter(user=user).order_by('type__priority')
        return [h for h in histories
                if h.type.can_show(page, version_count)
                and h.ready_to_show()]


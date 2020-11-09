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
    def available_tips(cls, user: ClusiveUser):
        """Return all tips that are currently available to show this user."""

        # All tips are currently disallowed on the user's FIRST reading page view
        stats: UserStats
        stats = UserStats.for_clusive_user(user)
        if stats.reading_views < 1:
            logger.debug('First reading page view. No tips')
            return []

        # Check tip history to see which are ready to be shown
        histories = TipHistory.objects.filter(user=user).order_by('type__priority')
        return [h for h in histories if h.ready_to_show()]


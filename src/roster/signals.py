from django.db.models.signals import post_save
from django.dispatch import receiver

from eventlog.models import Event
from roster.models import UserStats

@receiver(post_save, sender=Event)
def stats_event_watcher(sender, instance, **kwargs):
    if kwargs['created']:
        UserStats.update_stats_for_event(instance)

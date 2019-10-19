import logging

from django.db.models import F
from django.dispatch import receiver

from eventlog.signals import vocab_lookup
from glossary.models import WordModel
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


@receiver(vocab_lookup)
def record_vocab_lookup(sender, **kwargs):
    """Record a user lookup of a vocabulary word as indicating interest in that word"""
    user = None
    try:
        django_user = kwargs.get('request').user
        if django_user.is_authenticated:
            user = ClusiveUser.objects.get(user=django_user)
    except ClusiveUser.DoesNotExist:
        logger.debug("Can't log, no user")
    if user:
        word=kwargs['word'].lower()
        wm, created = WordModel.objects.get_or_create(user=user, word=word)
        wm.free_lookups = F('free_lookups') + 1
        wm.save()
        if logger.isEnabledFor(logging.DEBUG):
            wm.refresh_from_db()
            logger.debug("Word lookup %s/%s: now knowledge=%d and interest=%d",
                         user, word, wm.knowledge_est(), wm.interest_est())

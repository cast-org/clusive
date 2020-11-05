import logging

from django.contrib.auth import user_logged_in
from django.dispatch import receiver

from roster.models import ClusiveUser
from tips.models import TipHistory

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def initialize_at_login(sender, **kwargs):
    try:
        clusive_user = ClusiveUser.objects.get(user=kwargs['user'])
        TipHistory.initialize_histories(clusive_user)
    except ClusiveUser.DoesNotExist:
        logger.debug('User logging in is not a ClusiveUser')

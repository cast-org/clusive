import logging

from dateutil.parser import parse as dateutil_parse
from django.contrib.auth import user_logged_in
from django.dispatch import receiver, Signal

from roster.models import ClusiveUser
from tips.models import TipHistory, CTAHistory

logger = logging.getLogger(__name__)


tip_related_action = Signal(providing_args=['timestamp', 'request', 'action'])
tip_view = Signal(providing_args=['timestamp', 'request', 'tip'])


@receiver(user_logged_in)
def initialize_at_login(sender, **kwargs):
    try:
        clusive_user = ClusiveUser.objects.get(user=kwargs['user'])
        TipHistory.initialize_histories(clusive_user)
        CTAHistory.initialize_histories(clusive_user)
    except ClusiveUser.DoesNotExist:
        logger.debug('User logging in is not a ClusiveUser')


@receiver(tip_related_action)
def handle_tip_related_action(sender, **kwargs):
    time = dateutil_parse(kwargs['timestamp'])
    action = kwargs['action']
    request = kwargs['request']
    try:
        clusive_user = request.clusive_user
        logger.debug('Handling TRA: %s for %s', action, clusive_user)
        TipHistory.register_action(clusive_user, action, time)
    except ClusiveUser.DoesNotExist:
        logger.debug('Tip-related action from non-ClusiveUser')

@receiver(tip_view)
def handle_tip_view(sender, **kwargs):
    time = dateutil_parse(kwargs['timestamp'])
    tip = kwargs['tip']
    request = kwargs['request']
    try:
        clusive_user = request.clusive_user
        logger.debug('Handling TV: %s for %s', tip, clusive_user)
        TipHistory.register_show(clusive_user, tip, time)
    except ClusiveUser.DoesNotExist:
        logger.debug('Tip view reported from non-ClusiveUser')

from django.dispatch import receiver, Signal
from django.contrib.auth import user_logged_in, user_logged_out
from django_session_timeout.signals import user_timed_out
from eventlog.models import LoginSession, Event, SESSION_ID_KEY, PERIOD_KEY
from roster.models import Period, ClusiveUser
from django.utils import timezone
import logging
import caliper

logger = logging.getLogger(__name__)

#
# Custom signals that we recognize for event logging
#

page_viewed = Signal(providing_args=['session', 'document', 'page'])
vocab_lookup = Signal(providing_args=['session', 'value'])

#
# Signal handlers that log specific events
#


@receiver(page_viewed)
def log_page_viewed(sender, **kwargs):
    """User views a page of a book"""
    event = Event.build(type='VIEW_EVENT',
                        action='VIEWED',
                        document=kwargs.get('document'),
                        page=kwargs.get('page'),
                        session=kwargs.get('session'))
    logger.info("event for %s: %s", kwargs.get('session'), event)
    if event:
        event.save()


@receiver(vocab_lookup)
def log_vocab_lookup(sender, **kwargs):
    """User looks up a vocabulary word"""
    # TODO: differentiate definition source (Wordnet, custom, ...) once there is more than one
    # TODO: differentiate lookup button from clicking a linked word to look it up.
    # TODO: indicate document and page where the event occurred
    event = Event.build(type='TOOL_USE_EVENT',
                        action='USED',
                        control='lookup',
                        value=kwargs['value'],
                        session=kwargs['session'])
    if event:
        event.save()


@receiver(user_logged_in)
def log_login(sender, **kwargs):
    """A user has logged in. Create a Session object in the database and log an event."""
    django_user = kwargs['user']
    try:
        clusive_user = ClusiveUser.objects.get(user=django_user)
        user_agent = kwargs['request'].META.get('HTTP_USER_AGENT', '')
        login_session = LoginSession(user=clusive_user, userAgent=user_agent)
        login_session.save()
        # Put the ID of the database object into the HTTP session so that we know which one to close later.
        django_session = kwargs['request'].session
        django_session[SESSION_ID_KEY] = login_session.id.__str__()
        # Store the user's "Current Period" - in the case of teachers who may be associated with more than one Period,
        # this will be the first-listed one.  Teachers should have some mechanism of changing their current period
        # in the user interface, so they can interact with any of their classes; this should update the current period
        # as stored in the session so that event logging will use the correct one.
        periods = clusive_user.periods.all()
        current_period = periods.first() if periods else None
        if (current_period):
            django_session[PERIOD_KEY] = current_period.id
        # Create an event
        event = Event.build(type='SESSION_EVENT',
                            action='LOGGED_IN',
                            login_session=login_session,
                            group=current_period)
        event.save()
        logger.debug("Login by user %s", clusive_user)
    except ClusiveUser.DoesNotExist:
        logger.warning("Login by a non-Clusive user: %s", django_user)


@receiver(user_logged_out)
def log_logout(sender, **kwargs):
    """A user has logged out. Find the Session object in the database and set the end time."""
    django_session = kwargs['request'].session
    login_session_id = django_session.get(SESSION_ID_KEY, None)
    if (login_session_id):
        login_session = LoginSession.objects.get(id=login_session_id)
        # Create an event
        event = Event.build(type='SESSION_EVENT',
                            action='LOGGED_OUT',
                            session=django_session)
        if event:
            event.save()
        # Close out session
        login_session.endedAtTime = timezone.now()
        login_session.save()
        clusive_user = login_session.user
        logger.debug("Logout user %s", clusive_user)


@receiver(user_timed_out)
def log_timeout(sender, **kwargs):
    """A user's session has been timed out after some period of inactivity"""
    if(kwargs['user'] and kwargs['user'].is_authenticated):
        django_session = kwargs['session']
        login_session_id = django_session.get(SESSION_ID_KEY, None)
        period_id        = django_session.get(PERIOD_KEY, None)
        try:
            clusive_user = ClusiveUser.objects.get(user=kwargs['user'])   # should match what's in loginsession
            login_session = LoginSession.objects.get(id=login_session_id)
            # Create an event
            event = Event.build(type='SESSION_EVENT',
                                action='TIMED_OUT',
                                login_session=login_session,
                                group=Period.objects.get(id=period_id))
            event.save()
            # Close out session
            login_session.endedAtTime = timezone.now()
            login_session.save()
            logger.debug("Timeout user %s", clusive_user)
        except ClusiveUser.DoesNotExist:
            logger.debug("Timeout of non-Clusive user session: %s", kwargs['user'])

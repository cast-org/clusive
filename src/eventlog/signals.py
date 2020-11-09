import logging
from datetime import datetime, timedelta

from django.contrib.auth import user_logged_in, user_logged_out
from django.dispatch import receiver, Signal
from django.utils import timezone
from django_session_timeout.signals import user_timed_out

from eventlog.models import LoginSession, Event, SESSION_ID_KEY, PERIOD_KEY
from roster.models import Period, ClusiveUser

logger = logging.getLogger(__name__)

#
# Custom signals that we recognize for event logging.
# (we also recognize some Django standard signals - user logged in/out, timeout)
#

page_timing = Signal(providing_args=['event_id', 'times'])
vocab_lookup = Signal(providing_args=['request', 'word', 'cued', 'source'])
preference_changed = Signal(providing_args=['request', 'event_id', 'preference', 'timestamp'])
annotation_action = Signal(providing_args=['request', 'action', 'annotation'])
control_used = Signal(providing_args=['request', 'event_id', 'control', 'value'])

#
# Signal handlers that log specific events
#

@receiver(page_timing)
def log_page_timing(sender, **kwargs):
    """
    Collects and stores page timing information, which the client may send at the end of a page view.
    The extra information will be added in to the original VIEWED event representing the page view.
    """
    event_id = kwargs['event_id']
    times = kwargs['times']
    if event_id:
        try:
            event = Event.objects.get(id=event_id)
            logger.debug('Adding page timing to %s: %s', event, times)
            loadTime = times.get('loadTime')
            duration = times.get('duration')
            activeDuration = times.get('activeDuration')
            if loadTime:
                event.loadTime = timedelta(milliseconds=loadTime)
            if duration:
                event.duration = timedelta(milliseconds=duration)
            if activeDuration:
                event.activeDuration = timedelta(milliseconds=activeDuration)
            event.save()
        except Event.DoesNotExist:
            logger.error('Received page timing for a non-existent event %s', event_id)
    else:
        logger.error('Missing event ID in page timing message')


@receiver(vocab_lookup)
def log_vocab_lookup(sender, **kwargs):
    """User looks up a vocabulary word"""
    # TODO: differentiate definition source (Wordnet, custom, ...) once there is more than one
    # TODO: differentiate lookup button from clicking a linked word to look it up.
    # TODO: indicate document and page where the event occurred
    event = Event.build(type='TOOL_USE_EVENT',
                        action='USED',
                        control='lookup',
                        value=kwargs['word'],
                        session=kwargs['request'].session)
    if event:
        event.save()

@receiver(control_used)
def log_control_used(sender, **kwargs):
    """User interacts with a UI control"""
    logger.debug("control interaction: %s " % (kwargs))
    event_id = kwargs['event_id']
    if event_id:
        try:
            associated_page_event = Event.objects.get(id=event_id)
            page = associated_page_event.page 
            document = associated_page_event.document
            document_version = associated_page_event.document_version
            event = Event.build(type='TOOL_USE_EVENT',
                                action='USED',
                                control=kwargs['control'],
                                value=kwargs['value'],
                                page=page,
                                document=document,
                                eventTime=timeStamp,
                                document_version=document_version,
                                session=kwargs['request'].session)
            if event:   
                event.save()                                                    
        except Event.DoesNotExist:
            logger.error('Received control_used with a non-existent page event ID %s', event_id)

@receiver(preference_changed)
def log_pref_change(sender, **kwargs):
    """User changes a preference setting"""
    event_id = kwargs['event_id']
    if event_id:
        try:
            associated_page_event = Event.objects.get(id=event_id)
            page = associated_page_event.page 
            document = associated_page_event.document
            document_version = associated_page_event.document_version        
            request = kwargs.get('request')
            preference = kwargs.get('preference')
            timestamp = kwargs.get('timestamp')
            logger.debug("Preference change: %s at %s" % (preference, timestamp))
            event = Event.build(type='TOOL_USE_EVENT',
                                action='USED',
                                control='pref:'+preference.pref,
                                eventTime=timestamp,
                                value=preference.value,
                                page=page,
                                document=document,
                                document_version=document_version,                            
                                session=request.session)
            if event:   
                event.save()
        except Event.DoesNotExist:
            logger.error('Received pref_change with a non-existent page event ID %s', event_id)            

@receiver(annotation_action)
def log_annotation_action(sender, **kwargs):
    """User adds, deletes, or undeletes an annotation"""
    request = kwargs.get('request')
    action = kwargs.get('action')   # Should be HIGHLIGHTED or REMOVED
    annotation = kwargs.get('annotation')
    logger.debug("Annotation %s: %s" % (action, annotation))
    event = Event.build(type='ANNOTATION_EVENT',
                        action=action,
                        document='%s:%d' % (annotation.bookVersion.book.path, annotation.bookVersion.sortOrder),
                        value=annotation.clean_text(),
                        session=request.session)
            # TODO: page?  Generated?
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
        logger.debug("Login by user %s at %s" % (clusive_user, event.eventTime))
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
        logger.debug("Logout user %s at %s" % (clusive_user, event.eventTime))


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
            period = Period.objects.filter(id=period_id).first() # May be null
            # Create an event
            event = Event.build(type='SESSION_EVENT',
                                action='TIMED_OUT',
                                login_session=login_session,
                                group=period)
            event.save()
            # Close out session
            login_session.endedAtTime = timezone.now()
            login_session.save()
            logger.debug("Timeout user %s", clusive_user)
        except ClusiveUser.DoesNotExist:
            logger.debug("Timeout of non-Clusive user session: %s", kwargs['user'])

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
preference_changed = Signal(providing_args=['request', 'event_id', 'preference', 'timestamp', 'reader_info'])
annotation_action = Signal(providing_args=['request', 'action', 'annotation'])
control_used = Signal(providing_args=['request', 'event_id', 'control', 'value', 'timestamp', 'reader_info'])

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

# Tries to get an associated page_event_id 
# First priority: event_id sent as part of keyword argument
# Second priority: event_id sent as part of request header
# Returns associated page event ID if found, or None
def get_page_event_id(kwargs):
    page_event_id = None
    try:
        page_event_id = kwargs['event_id']
    except KeyError:
        request = kwargs.get('request')
        page_event_id = request.headers.get('Clusive-Page-Event-Id')
    return page_event_id        

# Tries to get information about the current reader href
# First priority: reader_info sent as part of the keyword argument
# Second priority: Clusive-Document-Location-Href from request header
def get_resource_href(kwargs):
    reader_info = kwargs.get('reader_info') 
    resource_href = None
    try:                        
        resource_href = reader_info.get('location').get('href')
    except AttributeError:
        request = kwargs.get('request')
        resource_href = request.headers.get('Clusive-Reader-Document-Href')
    return resource_href

# Tries to get information about the current reader progression
# First priority: reader_info sent as part of the keyword argument
# Second priority: Clusive-Document-Location-Progression from request header
def get_resource_progression(kwargs):
    reader_info = kwargs.get('reader_info') 
    resource_progression = None
    try:                        
        resource_progression = reader_info.get('location').get('progression')
    except AttributeError:
        request = kwargs.get('request')        
        resource_progression = request.headers.get('Clusive-Reader-Document-Progression')
    return resource_progression

# Handle parameters non-pageview / session events should have in common
def get_common_event_args(kwargs):    
    # TODO: we don't currently store the related page event ID 
    # on generated events - should we?
    event_id = get_page_event_id(kwargs)
    timestamp = kwargs.get('timestamp')
    if event_id:
        try:
            associated_page_event = Event.objects.get(id=event_id)
            page = associated_page_event.page             
            book_version_id = associated_page_event.book_version_id
            resource_href = get_resource_href(kwargs)            
            resource_progression = get_resource_progression(kwargs)            
            common_event_args = dict(page=page,                                
                                eventTime=timestamp,
                                book_version_id=book_version_id,
                                resource_href = resource_href,
                                resource_progression=resource_progression,
                                session=kwargs['request'].session)  
            return common_event_args
        except Event.DoesNotExist:
            logger.error('get_common_event_args with a non-existent page event ID %s', event_id)                

# TODO: parameterize type / action 
def build_tool_use_event(control, value, kwargs):
    common_event_args = get_common_event_args(kwargs)
    logger.debug("build_tool_use_event: %s / %s / %s" % (control, value, common_event_args))
    event = Event.build(type='TOOL_USE_EVENT',
                        # TODO: should this be configurable for other action types?
                        action='USED',
                        control=control,
                        value=value,
                        **common_event_args)
    if event:
        event.save()

@receiver(vocab_lookup)
def log_vocab_lookup(sender, **kwargs):
    """User looks up a vocabulary word"""
    # TODO: differentiate definition source (Wordnet, custom, ...) once there is more than one        
    control = 'lookup:%s' % ("cued" if kwargs.get('cued') else "uncued")
    value = value=kwargs['word']    
    build_tool_use_event(control, value, kwargs)

@receiver(control_used)
def log_control_used(sender, **kwargs):
    """User interacts with a control"""
    control=kwargs['control'],
    value=kwargs['value'],    
    build_tool_use_event(control, value, kwargs)

@receiver(preference_changed)
def log_pref_change(sender, **kwargs):
    """User changes a preference setting"""    
    preference = kwargs.get('preference')                  
    control='pref:'+preference.pref                      
    value=preference.value    
    build_tool_use_event(control, value, kwargs)

@receiver(annotation_action)
def log_annotation_action(sender, **kwargs):
    """User adds, deletes, or undeletes an annotation"""
    common_event_args = get_common_event_args(kwargs)    
    action = kwargs.get('action')   # Should be HIGHLIGHTED or REMOVED
    annotation = kwargs.get('annotation')
    logger.debug("Annotation %s: %s" % (action, annotation))
    event = Event.build(type='ANNOTATION_EVENT',
                        action=action,                        
                        value=annotation.clean_text(),                        
                        **common_event_args)
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

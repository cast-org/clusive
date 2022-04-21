import logging
from datetime import timedelta

from django.contrib.auth import user_logged_in, user_logged_out
from django.dispatch import receiver, Signal
from django.utils import timezone
from django_session_timeout.signals import user_timed_out

from eventlog.models import LoginSession, Event, SESSION_ID_KEY, PERIOD_KEY
from library.models import Paradata
from roster.models import Period, ClusiveUser, UserStats

logger = logging.getLogger(__name__)

#
# Custom signals that we recognize for event logging.
# (we also recognize some Django standard signals - user logged in/out, timeout)
#

page_timing = Signal(providing_args=['event_id', 'times'])
vocab_lookup = Signal(providing_args=['request', 'word', 'cued', 'source', 'book'])
translation_action = Signal(providing_args=['request', 'language', 'text', 'book'])
simplification_action = Signal(providing_args=['request', 'text', 'book'])
preference_changed = Signal(providing_args=['request', 'event_id', 'preference', 'timestamp', 'reader_info'])
annotation_action = Signal(providing_args=['request', 'action', 'annotation'])
control_used = Signal(providing_args=['request', 'event_id', 'event_type', 'control', 'value', 'action', 'timestamp', 'reader_info'])
word_rated = Signal(providing_args=['request', 'event_id', 'book_id', 'control', 'word', 'rating'])
word_removed = Signal(providing_args=['request', 'event_id', 'word'])
comprehension_check_completed = Signal(providing_args=['request', 'event_id', 'book_id', 'key', 'question', 'answer', 'comprehension_check_response_id'])
affect_check_completed = Signal(providing_args=['request', 'event_id', 'book_id', 'control', 'answer', 'affect_check_response_id'])
star_rating_completed = Signal(providing_args=['request', 'question', 'answer'])
book_starred = Signal(providing_args=['request', 'book_id', 'starred'])

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
            if event.load_time is not None \
                or event.duration is not None \
                or event.active_duration is not None:
                logger.warning('Not overwriting existing page timing info on event %s', event)
            else:
                logger.debug('Adding page timing to %s: %s', event, times)
                load_time = times.get('loadTime')
                duration = times.get('duration')
                active_duration = times.get('activeDuration')
                if load_time:
                    event.load_time = timedelta(milliseconds=load_time)
                if duration:
                    event.duration = timedelta(milliseconds=duration)
                if active_duration:
                    event.active_duration = timedelta(milliseconds=active_duration)
                    # Page view events are used to calculate various totals.
                    if event.type == 'VIEW_EVENT' and event.action == 'VIEWED':
                        UserStats.add_active_time(event.actor, event.active_duration)
                        if event.session is not None:
                            event.session.add_active_time(event.active_duration)
                        # For book page views, increment time spent in Book
                        if event.book_id is not None:
                            Paradata.record_additional_time(book_id=event.book_id, user=event.actor, time=event.active_duration)
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
    event_id = get_page_event_id(kwargs)
    timestamp = kwargs.get('timestamp')
    if event_id:
        try:
            associated_page_event = Event.objects.get(id=event_id)
            page = associated_page_event.page

            # book_id and book_version id can be supplied by events;
            # if not supplied, try to fill them in from the associated
            # page event
            book_id = kwargs.get('book_id')
            if not book_id:
                book_id = associated_page_event.book_id
            book_version_id = kwargs.get('book_version_id')
            if not book_version_id:
                book_version_id = associated_page_event.book_version_id

            resource_href = get_resource_href(kwargs)
            resource_progression = get_resource_progression(kwargs)
            common_event_args = dict(page=page,
                                parent_event_id=event_id,
                                event_time=timestamp,
                                book_id=book_id,
                                book_version_id=book_version_id,
                                resource_href = resource_href,
                                resource_progression=resource_progression,
                                session=kwargs['request'].session)
            return common_event_args
        except Event.DoesNotExist:
            logger.error('get_common_event_args with a non-existent page event ID %s', event_id)
    return {}

# General function for event creation
# Defaults action and type to the most common TOOL_USE_EVENT type
def create_event(kwargs, control=None, object=None, value=None, action='USED', event_type='TOOL_USE_EVENT'):
    common_event_args = get_common_event_args(kwargs)
    event = Event.build(type=event_type,
                        action=action,
                        control=control,
                        object=object,
                        value=value,
                        **common_event_args)
    if event:
        # TODO: this doesn't validate the object by the rules like
        # limited choices for ACTION and TYPE based on Caliper's spec
        # See https://docs.djangoproject.com/en/3.1/ref/models/instances/#validating-objects
        event.save()

@receiver(comprehension_check_completed)
def log_comprehension_check_completed(sender, **kwargs):
    """User completes a comprehension check"""
    action = 'COMPLETED'
    event_type = 'ASSESSMENT_ITEM_EVENT'
    key = kwargs.get('key')
    question = kwargs.get('question')
    answer = kwargs.get('answer')
    # 'request', 'event_id', 'book_id', 'key', 'question', 'answer', 'comprehension_check_response_id
    control = 'comprehension_check_%s' % key
    create_event(kwargs, control=control, object=question, value=answer, action=action, event_type=event_type)

@receiver(affect_check_completed)
def log_affect_check_completed(sender, **kwargs):
    action = 'COMPLETED'
    event_type = 'ASSESSMENT_ITEM_EVENT'
    control = kwargs.get('control')
    question = kwargs.get('question')
    answer = kwargs.get('answer')
    create_event(kwargs, control=control, object=question, value=answer, action=action, event_type=event_type)

@receiver(star_rating_completed)
def log_star_rating_completed(sender, **kwargs):
    action = 'COMPLETED'
    event_type = 'ASSESSMENT_ITEM_EVENT'
    control = 'star_rating'
    question = kwargs.get('question')
    value = str(kwargs.get('answer'))
    create_event(kwargs, event_type=event_type, control=control, action=action, object=question, value=value)


@receiver(word_rated)
def log_word_rated(sender, **kwargs):
    """User rates a word"""
    control = kwargs.get('control')
    book_id = kwargs.get('book_id')
    word = kwargs.get('word')
    rating = str(kwargs.get('rating'))
    event_type = 'ASSESSMENT_ITEM_EVENT'
    action = 'COMPLETED'
    create_event(kwargs, control=control, object=word, value=rating, action=action, event_type=event_type)


@receiver(word_removed)
def log_word_removed(sender, **kwargs):
    """User removes a word from the Wordbank"""
    word = kwargs.get('word')
    event_type = 'TOOL_USE_EVENT'
    action = 'USED'
    create_event(kwargs, control='wb_remove', object=word, action=action, event_type=event_type)


@receiver(vocab_lookup)
def log_vocab_lookup(sender, **kwargs):
    """User looks up a vocabulary word"""
    # TODO: differentiate definition source (Wordnet, custom, ...) once there is more than one
    control = 'lookup:%s' % ("cued" if kwargs.get('cued') else "uncued")
    value = kwargs['word']
    create_event(kwargs, control=control, value=value)


@receiver(translation_action)
def log_translation_action(sender, **kwargs):
    """User requests translation of some text"""
    # provides: 'request', 'language', 'text', 'book'
    create_event(kwargs, control='translation', object=kwargs['language'], value=kwargs['text'])


@receiver(simplification_action)
def log_simplification_action(sender, **kwargs):
    """User requests simplification of some text"""
    # provides: 'request', 'text', 'book'
    create_event(kwargs, control='simplification', value=kwargs['text'])


@receiver(control_used)
def log_control_used(sender, **kwargs):
    """User interacts with a control"""
    control = kwargs.get('control')
    object = kwargs.get('object')
    value = kwargs.get('value')
    event_type = kwargs.get('event_type')
    action = kwargs.get('action')
    create_event(kwargs, control=control, object=object, value=value, action=action, event_type=event_type)


@receiver(preference_changed)
def log_pref_change(sender, **kwargs):
    """User changes a preference setting"""
    preference = kwargs.get('preference')
    control='pref:'+preference.pref
    value=preference.value
    create_event(kwargs, control=control, value=value)

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
    event.save()


@receiver(user_logged_in)
def log_login(sender, **kwargs):
    """A user has logged in. Create a Session object in the database and log an event."""
    django_user = kwargs['user']
    try:
        clusive_user = ClusiveUser.objects.get(user=django_user)
        user_agent = kwargs['request'].META.get('HTTP_USER_AGENT', '')
        login_session = LoginSession(user=clusive_user, user_agent=user_agent)
        login_session.save()
        # Put the ID of the database object into the HTTP session so that we know which one to close later.
        django_session = kwargs['request'].session
        django_session[SESSION_ID_KEY] = login_session.id.__str__()
        # Update UserStats
        UserStats.add_login(clusive_user)
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
        logger.debug("Login by user %s at %s" % (clusive_user, event.event_time))
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
        login_session.ended_at_time = timezone.now()
        login_session.save()
        clusive_user = login_session.user
        logger.debug("Logout user %s at %s" % (clusive_user, event.event_time))


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
            login_session.ended_at_time = timezone.now()
            login_session.save()
            logger.debug("Timeout user %s", clusive_user)
        except ClusiveUser.DoesNotExist:
            logger.debug("Timeout of non-Clusive user session: %s", kwargs['user'])


@receiver(book_starred)
def log_book_starred(sender, **kwargs):
    value = 'add star' if kwargs['starred'] else 'remove star'
    create_event(kwargs,
        event_type='ANNOTATION_EVENT',
        action='TAGGED',
        control='star',
        value=value)


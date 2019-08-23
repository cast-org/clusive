from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from eventlog.models import Session, Event
from django.utils import timezone
from caliper import constants

@receiver(user_logged_in)
def log_login(sender, **kwargs):
    """A user has logged in. Create a Session object in the database and log an event."""
    session = Session(user = kwargs['user'])
    session.save()
    # Put the ID of the database object into the HTTP session so that we know which one to close later.
    kwargs['request'].session['db_session_id'] = session.id.__str__()
    # Create an event
    event = Event(type='SESSION_EVENT', action='LOGGED_IN', actor = kwargs['user'], session=session)
    event.save()


@receiver(user_logged_out)
def log_logout(sender, **kwargs):
    """A user has logged out. Find the Session object in the database and set the end time."""
    session_id = kwargs['request'].session.get('db_session_id', False)
    if (session_id):
        session = Session.objects.get(id=session_id)
        # Create an event
        event = Event(type='SESSION_EVENT', action='LOGGED_OUT', actor = kwargs['user'], session=session)
        event.save()
        # Close out session
        session.endedAtTime = timezone.now()
        session.save()

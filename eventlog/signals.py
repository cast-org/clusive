from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from eventlog.models import Session, Event
from roster.models import ClusiveUser
from django.utils import timezone

@receiver(user_logged_in)
def log_login(sender, **kwargs):
    """A user has logged in. Create a Session object in the database and log an event."""
    django_user = kwargs['user']
    try:
        clusive_user = ClusiveUser.objects.get(user=django_user)
        session = Session(user=clusive_user, userAgent=kwargs['request'].META['HTTP_USER_AGENT'])
        session.save()
        # Put the ID of the database object into the HTTP session so that we know which one to close later.
        kwargs['request'].session['db_session_id'] = session.id.__str__()
        # Create an event
        event = Event(type='SESSION_EVENT', action='LOGGED_IN', actor=clusive_user, session=session)
        event.save()
    except ClusiveUser.DoesNotExist:
        print("Login by a non-Clusive user")

@receiver(user_logged_out)
def log_logout(sender, **kwargs):
    """A user has logged out. Find the Session object in the database and set the end time."""
    session_id = kwargs['request'].session.get('db_session_id', False)
    if (session_id):
        session = Session.objects.get(id=session_id)
        # Create an event
        clusive_user = ClusiveUser.objects.get(user=kwargs['user'])
        event = Event(type='SESSION_EVENT', action='LOGGED_OUT', actor=clusive_user, session=session)
        event.save()
        # Close out session
        session.endedAtTime = timezone.now()
        session.save()

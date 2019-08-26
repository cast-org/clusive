from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from eventlog.models import Session, Event
from roster.models import Period, ClusiveUser
from django.utils import timezone

@receiver(user_logged_in)
def log_login(sender, **kwargs):
    """A user has logged in. Create a Session object in the database and log an event."""
    django_user = kwargs['user']
    try:
        clusive_user = ClusiveUser.objects.get(user=django_user)
        user_agent = kwargs['request'].META.get('HTTP_USER_AGENT', '')
        session = Session(user=clusive_user, userAgent=user_agent)
        session.save()
        # Put the ID of the database object into the HTTP session so that we know which one to close later.
        http_session = kwargs['request'].session
        http_session['db_session_id'] = session.id.__str__()
        # Store the user's "Current Period" - in the case of teachers who may be associated with more than one Period,
        # this will be the first-listed one.  Teachers should have some mechanism of changing their current period
        # in the user interface, so they can interact with any of their classes; this should update the current period
        # as stored in the session so that event logging will use the correct one.
        periods = clusive_user.periods.all()
        current_period_id = periods[0].id if periods else None
        http_session['current_period'] = current_period_id
        # Create an event
        event = Event(type='SESSION_EVENT',
                      action='LOGGED_IN',
                      actor=clusive_user,
                      session=session,
                      group=Period.objects.get(id=current_period_id) if current_period_id else None,
                      membership=clusive_user.role,
                      )
        event.save()
    except ClusiveUser.DoesNotExist:
        print("Login by a non-Clusive user")

@receiver(user_logged_out)
def log_logout(sender, **kwargs):
    """A user has logged out. Find the Session object in the database and set the end time."""
    session_id = kwargs['request'].session.get('db_session_id', None)
    if (session_id):
        session = Session.objects.get(id=session_id)
        # Create an event
        clusive_user = ClusiveUser.objects.get(user=kwargs['user'])
        periods = clusive_user.periods.all()
        current_period_id = periods[0].id if periods else None
        event = Event(type='SESSION_EVENT',
                      action='LOGGED_OUT',
                      actor=clusive_user,
                      session=session,
                      group=Period.objects.get(id=current_period_id) if current_period_id else None,
                      membership=clusive_user.role,
                      )
        event.save()
        # Close out session
        session.endedAtTime = timezone.now()
        session.save()

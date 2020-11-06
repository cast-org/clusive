import logging

from django.db import models
from uuid import uuid4
from roster.models import Period, ClusiveUser, Roles
from django.utils import timezone
import caliper

logger = logging.getLogger(__name__)

# Keys for data we store in the session
PERIOD_KEY = 'current_period'
SESSION_ID_KEY = 'db_session_id'

# A user session
class LoginSession(models.Model):
    id = models.CharField(primary_key=True, default=uuid4, max_length=36)
    user = models.ForeignKey(to=ClusiveUser, on_delete=models.PROTECT)
    startedAtTime = models.DateTimeField(auto_now_add=True)
    endedAtTime = models.DateTimeField(null=True)  # time stamp when session ended (logout or timeout)
    # TODO appVersion: the current version of the Clusive application that the user is interacting with
    userAgent = models.CharField(max_length=256)

    def __str__(self):
        return '%s [%s - %s] (%s)' % (self.user.anon_id, self.startedAtTime, self.endedAtTime, self.id)

class Event(models.Model):
    id = models.CharField(primary_key=True, default=uuid4, max_length=36)
    session = models.ForeignKey(to=LoginSession, on_delete=models.PROTECT)
    actor = models.ForeignKey(to=ClusiveUser, on_delete=models.PROTECT)
    group = models.ForeignKey(to=Period, null=True, on_delete=models.PROTECT)
    membership = models.CharField(
        max_length=2,
        choices=Roles.ROLE_CHOICES,
        default=Roles.GUEST
    )
    # Date and time the event started
    eventTime = models.DateTimeField(default=timezone.now())
    # (VIEW events:) time for the browser to retrieve and render the content
    loadTime = models.DurationField(null=True)
    # (VIEW events:) total time from when the page was loaded to when it was exited
    duration = models.DurationField(null=True)
    # (VIEW events:) time that this page was focused, computer was awake, and no timeout dialog was in play.
    activeDuration = models.DurationField(null=True)
    # type of the event, based on Caliper spec
    type = models.CharField(max_length=32, choices=[(k,v) for k,v in caliper.constants.EVENT_TYPES.items()])
    # action of the event, based on Caliper spec
    action = models.CharField(max_length=32, choices=[(k,v) for k, v in caliper.constants.CALIPER_ACTIONS.items()])
    # What document the user was looking at; null if none (eg, the library page)
    document = models.CharField(max_length=128, null=True)
    # What document version the user was looking at; null if none
    document_version = models.CharField(max_length=128, null=True)
    # If in a document, what page of the document the user was looking at; if not, the name of the application page
    page = models.CharField(max_length=128, null=True)
    # for TOOL_USE_EVENT, records what tool was used; for preferences, which preference
    control = models.CharField(max_length=32, null=True)
    # For events that operate on text (lookup, highlight), the actual text looked up or highlighted
    # For preferences, the new value chosen for the preference
    value = models.CharField(max_length=128, null=True)
    # TODO log source of glossary definitions?
    # TODO context (current settings, version of text (eg lexile level), list of glossary words highlighted)

    @classmethod
    def build(cls, type, action,
              session=None, login_session=None, group=None,
              document=None, document_version=None, page=None,
              control=None, value=None, eventTime=timezone.now()):
        """Create an event based on the data provided."""
        if not session and not login_session:
            logger.error("Either a session object or a login_session must be provided")
            return None
        try:
            if session and not login_session:
                login_session_id = session.get(SESSION_ID_KEY, None)
                login_session = LoginSession.objects.get(id=login_session_id)
            if session and not group:
                period_id = session.get(PERIOD_KEY, None)
                group = Period.objects.filter(id=period_id).first()
            clusive_user = login_session.user
            if value and len(value) > 128:
                value = value[:126] + '…'
            event = cls(type=type,
                        action=action,
                        actor=clusive_user,
                        membership=clusive_user.role,
                        session=login_session,
                        group=group,
                        document=document,
                        document_version=document_version,
                        page=page,
                        control=control,
                        value=value,
                        eventTime=eventTime)
            return event
        except ClusiveUser.DoesNotExist:
            logger.warning("Event could not be stored - no Clusive user found: %s/%s", type, action)
        except LoginSession.DoesNotExist:
            logger.warning("Event could not be stored - no LoginSession: %s/%s", type, action)
        except Period.DoesNotExist:
            logger.warning("Event could not be stored - period id %s not found", period_id)
        return None


    def __str__(self):
        return '%s:%s (%s)' % (self.actor.anon_id, self.action, self.id)
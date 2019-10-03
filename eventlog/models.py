from django.db import models
from uuid import uuid4
from roster.models import Period, ClusiveUser, Roles
from django.utils import timezone
import caliper

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
    eventTime = models.DateTimeField(default=timezone.now)
    # TODO eventEndTime
    type = models.CharField(max_length=32, choices=[(k,v) for k,v in caliper.constants.EVENT_TYPES.items()])
    action = models.CharField(max_length=32, choices=[(k,v) for k, v in caliper.constants.CALIPER_ACTIONS.items()])
    # TODO page
    # TODO article
    # TODO preference
    # TODO context (current settings, version of text (eg lexile level), list of glossary words highlighted)

    @classmethod
    def build(cls, type, action, login_session, group):
        clusive_user = login_session.user
        event = cls(type=type,
                    action=action,
                    actor=clusive_user,
                    membership=clusive_user.role,
                    session=login_session,
                    group=group)
        return event


    def __str__(self):
        return '%s:%s (%s)' % (self.actor.anon_id, self.action, self.id)
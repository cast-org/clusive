from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from roster.models import Site, Period, ClusiveUser
from eventlog.models import Session, Event

# TODO copied from roster tests. Is there a central place that some of this setup could be done?
def set_up_test_sites():
    Site.objects.create(name="CAST Collegiate", city="Wakefield", state_or_province="MA", country="USA").save()

def set_up_test_periods():
    cast_collegiate = Site.objects.get(name="CAST Collegiate")
    Period.objects.create(name="Universal Design For Learning 101", site=cast_collegiate).save()

def set_up_test_users():
    user_1 = User.objects.create_user(username="user1", password="password1")
    user_1.save()
    cuser_1 = ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST')
    cuser_1.periods.add(Period.objects.get(name="Universal Design For Learning 101"))
    cuser_1.save()

class EventlogTestCase(TestCase):
    def setUp(self):
        set_up_test_sites()
        set_up_test_periods()
        set_up_test_users()

    def test_session_created(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        session = Session.objects.all()[0]
        self.assertEquals(len(session.id), 36, "Session should get uuid assigned")
        self.assertEquals(session.user, ClusiveUser.objects.all()[0], "Session should connect to the user")
        self.assertEquals(session.startedAtTime.date(), timezone.now().date(), "Should set reasonable session start time")
        self.assertIsNotNone(session.userAgent)

    def test_session_closed(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        self.client.logout()
        session = Session.objects.all()[0]
        self.assertEquals(session.endedAtTime.date(), timezone.now().date(), "Should set reasonable session end time")
        self.assertLess(session.startedAtTime, session.endedAtTime, "Start time should be before end time")

    def test_log_in_event(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        event = Event.objects.all()[0]
        self.assertEquals(len(event.id), 36, "Event should have a uuid assigned")
        self.assertIsInstance(event.session, Session, "Event should link to session")
        self.assertEquals(event.actor, ClusiveUser.objects.all()[0], "Event should list the user")
        self.assertEquals(event.group, Period.objects.get(name="Universal Design For Learning 101"))
        self.assertEquals(event.membership, "ST")
        self.assertEquals(event.eventTime.date(), timezone.now().date(), "Should set reasonable eventTime")
        self.assertEquals("SESSION_EVENT", event.type, "EventType is wrong")
        self.assertEquals("LOGGED_IN", event.action, "Action is wrong")

    def test_log_out_event(self):
        login = self.client.login(username='user1', password='password1')
        self.client.logout()
        event = Event.objects.all()[1]
        self.assertIsNotNone(event.id, "Event should have an ID assigned")
        self.assertIsInstance(event.session, Session, "Event should link to session")
        self.assertEquals(event.actor, ClusiveUser.objects.all()[0], "Event should list the user")
        self.assertEquals(event.group, Period.objects.get(name="Universal Design For Learning 101"))
        self.assertEquals(event.membership, "ST")
        self.assertEquals(event.eventTime.date(), timezone.now().date(), "Should set reasonable eventTime")
        self.assertEquals("SESSION_EVENT", event.type, "EventType is wrong")
        self.assertEquals("LOGGED_OUT", event.action, "Action is wrong")


from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from roster.tests import set_up_test_sites, set_up_test_periods, set_up_test_users

from roster.models import Site, Period, ClusiveUser
from eventlog.models import LoginSession, Event

from time import sleep

class EventlogTestCase(TestCase):
    def setUp(self):
        set_up_test_sites()
        set_up_test_periods()
        set_up_test_users()
        cuser_1 = ClusiveUser.objects.get(user__username='user1')
        cuser_1.periods.add(Period.objects.get(name="Universal Design For Learning 101"))

    def test_session_created(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        session = LoginSession.objects.all().order_by('-startedAtTime').first()
        self.assertEquals(len(session.id), 36, "Session should get uuid assigned")
        self.assertEquals(session.user, ClusiveUser.objects.all()[0], "Session should connect to the user")
        self.assertEquals(session.startedAtTime.date(), timezone.now().date(), "Should set reasonable session start time")
        self.assertIsNotNone(session.userAgent)

    def test_session_closed(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        self.client.logout()
        session = LoginSession.objects.all().order_by('-startedAtTime').first()
        self.assertEquals(session.endedAtTime.date(), timezone.now().date(), "Should set reasonable session end time")
        self.assertLess(session.startedAtTime, session.endedAtTime, "Start time should be before end time")

    def test_login_event(self):
        login = self.client.login(username='user1', password='password1')
        self.assertTrue(login)
        event = Event.objects.all().order_by('-eventTime').first()
        user = ClusiveUser.objects.get(user=User.objects.get(username='user1'))
        self.assertEquals(len(event.id), 36, "Event should have a uuid assigned")
        self.assertIsInstance(event.session, LoginSession, "Event should link to session")
        self.assertEquals(event.actor, user, "Event should list the user")
        self.assertEquals(event.group, Period.objects.get(name="Universal Design For Learning 101"))
        self.assertEquals(event.membership, "ST")
        self.assertEquals(event.eventTime.date(), timezone.now().date(), "Should set reasonable eventTime")
        self.assertEquals("SESSION_EVENT", event.type, "EventType is wrong")
        self.assertEquals("LOGGED_IN", event.action, "Action is wrong")

    def test_logout_event(self):
        login = self.client.login(username='user1', password='password1')        
        self.client.logout()
        event = Event.objects.all().order_by('-eventTime').first()
        self.assertIsNotNone(event.id, "Event should have an ID assigned")
        self.assertIsInstance(event.session, LoginSession, "Event should link to session")
        self.assertEquals(event.actor, ClusiveUser.objects.all()[0], "Event should list the user")
        self.assertEquals(event.group, Period.objects.get(name="Universal Design For Learning 101"))
        self.assertEquals(event.membership, "ST")
        self.assertEquals(event.eventTime.date(), timezone.now().date(), "Should set reasonable eventTime")
        self.assertEquals("SESSION_EVENT", event.type, "EventType is wrong")
        self.assertEquals("LOGGED_OUT", event.action, "Action is wrong")


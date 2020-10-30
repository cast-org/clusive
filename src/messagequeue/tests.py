from django.test import TestCase
import json

from roster.tests import set_up_test_users

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as dateutil_parse

from .models import Message, client_side_prefs_change
from .views import get_delta_from_now, adjust_message_timestamp

from eventlog.models import Event

now = datetime.now(timezone.utc)
first_pref_timestamp = now+relativedelta(seconds=-9)
second_pref_timestamp = now+relativedelta(seconds=-6)
third_pref_timestamp = now+relativedelta(seconds=-4)

now_str = now.isoformat()
first_pref_timestamp_str = first_pref_timestamp.isoformat()
second_pref_timestamp_str = second_pref_timestamp.isoformat()
third_pref_timestamp_str = third_pref_timestamp.isoformat()

preference_change_message_queue = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

invalid_type_message_queue = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user1", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

wrong_username_message_queue = '{"username": "user2", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

wrong_username_individual_messages = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user2", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user2", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"username": "user2", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

class MessageQueueTestCase(TestCase):

    # Load the preference sets 
    fixtures = ['preferencesets.json']    

    def setUp(self):
        set_up_test_users()
        login = self.client.login(username='user1', password='password1')
        library_page_response = self.client.get('/library/public')
        page_view_event = Event.objects.latest('eventTime')
        self.event_id = page_view_event.id

    def test_catch_invalid_message_type(self):
        response = self.client.post('/messagequeue/', preference_change_message_queue.replace("[eventId]", self.event_id), content_type='application/json')
        self.assertRaises(AttributeError, msg="Invalid message type did not raise expected AttributeError")

    def test_send_message(self):                            
        response = self.client.post('/messagequeue/', preference_change_message_queue.replace("[eventId]", self.event_id), content_type='application/json')
        self.assertJSONEqual(response.content, {'success': 1}, 'Sending messages did not return expected response')

    def test_filter_wrong_username_message_queue(self):                
        
        response = self.client.post('/messagequeue/', wrong_username_message_queue.replace("[eventId]", self.event_id), content_type='application/json')
        self.assertJSONEqual(response.content, {'message': 'Invalid user'}, 'Wrong username on message queue was not properly filtered')

    def test_time_adjustment(self):
        queue_timestamp = now_str
        client_reported_time = dateutil_parse(queue_timestamp)    
        delta = get_delta_from_now(client_reported_time)        
        
        adjusted_queue_timestamp = adjust_message_timestamp(queue_timestamp, delta)
        adjusted_first = adjust_message_timestamp(first_pref_timestamp_str, delta)
        adjusted_second = adjust_message_timestamp(second_pref_timestamp_str, delta)
        adjusted_third = adjust_message_timestamp(third_pref_timestamp_str, delta)

        def test_deltas(adjusted_message_timestamp, expected_seconds):
            testing_delta = relativedelta(dateutil_parse(adjusted_queue_timestamp), dateutil_parse(adjusted_message_timestamp))
            self.assertEqual(testing_delta.seconds, expected_seconds, "Delta of timestamp not as expected after adjustment")                 

        test_deltas(adjusted_first, 9)
        test_deltas(adjusted_second, 6)
        test_deltas(adjusted_third, 4)

    def test_client_side_prefs_change_message(self):            

        self.client.post('/messagequeue/', preference_change_message_queue.replace("[eventId]", self.event_id), content_type='application/json')
        prefs_response = self.client.get('/account/prefs')
        prefs = json.loads(prefs_response.content)
        self.assertEqual(prefs["fluid_prefs_contrast"], "sepia", "fluids_prefs_contrast value was not as expected")        
        self.assertEqual(prefs["fluid_prefs_textFont"], "times", "fluid_prefs_textFont value was not as expected")        

    def test_send_message_signal(self):            

        # Following pattern for testing signals described at https://www.freecodecamp.org/news/how-to-testing-django-signals-like-a-pro-c7ed74279311/
        self.signal_was_called = False;
        def handler(sender, timestamp, content, request, **kwargs):            
            self.signal_was_called = True;

        client_side_prefs_change.connect(handler)

        response = self.client.post('/messagequeue/', preference_change_message_queue.replace("[eventId]", self.event_id), content_type='application/json')                
        self.assertTrue(self.signal_was_called)
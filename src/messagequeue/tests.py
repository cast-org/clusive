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

preference_change_message_queue = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

invalid_type_message_queue = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_textFont":"comic","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"AA","preferences":{"fluid_prefs_contrast":"sepia","fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user1", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

wrong_username_message_queue = '{"username": "user2", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","fluid_prefs_textSize":0.9}},"timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

wrong_username_individual_messages = '{"username": "user1", "timestamp":"%s","messages":[{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"comic","fluid_prefs_textSize":0.9}},"username": "user2", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user2", "timestamp":"%s"},{"content":{"eventId": "[eventId]", "type":"PC","preferences":{"fluid_prefs_contrast":"sepia","fluid_prefs_textFont":"times","fluid_prefs_textSize":0.9}},"username": "user2", "timestamp":"%s"}]}' % (now_str, first_pref_timestamp_str, second_pref_timestamp_str, third_pref_timestamp_str)

content_for_multipart_form = [{
    'content': {
        'type': 'PT',
        'eventId': '915f752c-e2dd-47d9-8aa7-7ed7b07193e9?',
        'loadTime': 1967,
        'duration': 36577,
        'activeDuration': 180089
    },
    'timestamp': now_str,
    'username': 'user1'
}]
multipart_form_message = {
    'csrfmiddlewaretoken': 'dummycsrftoken',
    'timestamp': now_str,
    'messages': json.dumps(content_for_multipart_form),
    'username': 'user1'
}

class MessageQueueTestCase(TestCase):

    # Load the preference sets 
    fixtures = ['preferencesets.json']    

    def setUp(self):
        set_up_test_users()
        login = self.client.login(username='user1', password='password1')
        library_page_response = self.client.get('/library/public')
        page_view_event = Event.objects.latest('event_time')
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
        
        # Test that preferences have been changed
        prefs_response = self.client.get('/account/prefs')
        prefs = json.loads(prefs_response.content)
        self.assertEqual(prefs["fluid_prefs_contrast"], "sepia", "fluids_prefs_contrast value was not as expected")        
        self.assertEqual(prefs["fluid_prefs_textFont"], "times", "fluid_prefs_textFont value was not as expected")
        self.assertEqual(prefs["fluid_prefs_textSize"], 0.9, "fluid_prefs_textSize value was not as expected")

        # Test that events are created with expected values

        latest_contrast_event = Event.objects.filter(control='pref:fluid_prefs_contrast').order_by('-event_time').first()
        latest_textFont_event = Event.objects.filter(control='pref:fluid_prefs_textFont').order_by('-event_time').first()
        latest_textSize_event = Event.objects.filter(control='pref:fluid_prefs_textSize').order_by('-event_time').first()

        self.assertEqual(latest_contrast_event.value, "sepia", "value recorded in contrast change event was not as expected")
        self.assertEqual(latest_textFont_event.value, "times", "value recorded in textFont change event was not as expected")
        self.assertEqual(latest_textSize_event.value, '0.9', "value recorded in textFont change event was not as expected")        

    def test_send_message_signal(self):            

        # Following pattern for testing signals described at https://www.freecodecamp.org/news/how-to-testing-django-signals-like-a-pro-c7ed74279311/
        self.signal_was_called = False;
        def handler(sender, timestamp, content, request, **kwargs):            
            self.signal_was_called = True;

        client_side_prefs_change.connect(handler)

        response = self.client.post('/messagequeue/', preference_change_message_queue.replace("[eventId]", self.event_id), content_type='application/json')                
        self.assertTrue(self.signal_was_called)

    def test_send_form_message(self):
        response = self.client.post('/messagequeue/', multipart_form_message)
        self.assertJSONEqual(response.content, {'success': 1}, 'Sending messages did not return expected response')

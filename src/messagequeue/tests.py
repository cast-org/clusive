from django.test import TestCase
import json

from roster.tests import set_up_test_users

from .models import Message, client_side_prefs_change

preference_change_message_queue = '{"timestamp":"2020-07-28T21:01:29.448Z","messages":[{"content":{"type":"PC","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:26.602Z"},{"content":{"type":"PC","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:30.134Z"},{"content":{"type":"PC","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:32.938Z"}]}'    

class MessageQueueTestCase(TestCase):

    # Load the preference sets 
    fixtures = ['preferencesets.json']

    def setUp(self):
        set_up_test_users()

    def test_send_message(self):                            
        login = self.client.login(username='user1', password='password1')

        response = self.client.post('/messagequeue/', preference_change_message_queue, content_type='application/json')
        self.assertJSONEqual(response.content, {'success': 1}, 'Sending messages did not return expected response')

    def test_client_side_prefs_change_message(self):            
        login = self.client.login(username='user1', password='password1')

        self.client.post('/messagequeue/', preference_change_message_queue, content_type='application/json')
        prefs_response = self.client.get('/account/prefs')
        prefs = json.loads(prefs_response.content)
        self.assertEqual(prefs["fluid_prefs_contrast"], "sepia", "fluids_prefs_contrast value was not as expected")        
        self.assertEqual(prefs["fluid_prefs_textFont"], "times", "fluid_prefs_textFont value was not as expected")        

    def test_send_message_signal(self):            
        login = self.client.login(username='user1', password='password1')

        # Following pattern for testing signals described at https://www.freecodecamp.org/news/how-to-testing-django-signals-like-a-pro-c7ed74279311/
        self.signal_was_called = False;
        def handler(sender, timestamp, content, request, **kwargs):
            print(sender, timestamp, content, request)
            self.signal_was_called = True;

        client_side_prefs_change.connect(handler)

        response = self.client.post('/messagequeue/', preference_change_message_queue, content_type='application/json')                
        self.assertTrue(self.signal_was_called)
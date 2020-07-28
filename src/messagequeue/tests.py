from django.test import TestCase

from roster.tests import set_up_test_users

# Create your tests here.

class MessageQueueTestCase(TestCase):

    # Load the preference sets 
    fixtures = ['preferencesets.json']

    def setUp(self):
        set_up_test_users()

    def test_send_message(self):        
        
        preference_change_json = '{"timestamp":"2020-07-28T21:01:29.448Z","messages":[{"content":{"type":"PC","preferences":{"fluid_prefs_textFont":"comic","textFont":"comic","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:26.602Z"},{"content":{"type":"PC","preferences":{"fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:30.134Z"},{"content":{"type":"PC","preferences":{"fluid_prefs_contrast":"sepia","theme":"sepia","fluid_prefs_textFont":"times","textFont":"times","fluid_prefs_textSize":0.9,"textSize":0.9}},"timestamp":"2020-07-28T21:00:32.938Z"}]}'
    
        login = self.client.login(username='user1', password='password1')

        response = self.client.post('/messagequeue/', preference_change_json, content_type='application/json')
        self.assertJSONEqual(response.content, {'success': 1}, 'Sending messages did not return expected response')
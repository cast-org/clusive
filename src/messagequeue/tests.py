from django.test import TestCase

# Create your tests here.

class MessageQueueTestCase(TestCase):

    def test_send_message(self):        
        response = self.client.post('/messagequeue/', [{'foo': 'bar'}, {'baz': 'lur'}], content_type='application/json')
        self.assertJSONEqual(response.content, {'success': 1}, 'Sending messages did not return expected response')
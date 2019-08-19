from django.test import TestCase
from django.test import Client
from django.urls import reverse

# Basic example of how to write view-related tests
class PageTestCases(TestCase):

    def test_index_page(self):        
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf8')        
        self.assertIn('<h1>Welcome to Clusive</h1>', html)        
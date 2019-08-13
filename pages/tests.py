from django.test import TestCase
from .views import index
from django.http import HttpRequest
from django.urls import resolve

# Basic example of how to write view-related tests
class PagesTestCase(TestCase):
    
    def test_root_url_resolves_to_index_view(self):
        found = resolve('/')
        self.assertEqual(found.func, index)

    def test_index(self):
        request = HttpRequest()
        response = index(request)
        self.assertTrue(response.status_code, 200)
        html = response.content.decode('utf8')        
        self.assertIn('<h1>Welcome to Clusive</h1>', html)        
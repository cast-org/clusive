from django.test import TestCase
from django.test import Client
from django.urls import reverse


class PageTestCases(TestCase):

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)


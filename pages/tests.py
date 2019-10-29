from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from glossary.models import WordModel
from roster.models import ClusiveUser


class PageTestCases(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST').save()

    def test_index_page(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 302)

    def test_word_bank_page(self):
        WordModel.objects.create(user=ClusiveUser.objects.get(anon_id="Student1"),
                                 word='testword',
                                 cued=3,
                                 cued_lookups=2,
                                 free_lookups=1)
        login = self.client.login(username='user1', password='password1')
        response = self.client.get(reverse('word_bank'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['words']), 1)
        self.assertInHTML('testword', response.content.decode('utf8'), 1)


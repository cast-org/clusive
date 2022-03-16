import logging

from django.contrib.auth.models import User

import glossary.views
from eventlog.models import Event
from glossary.util import base_form, all_forms
from library.models import Book, BookVersion
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)

from django.test import TestCase

class GlossaryTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        self.clusive_user = ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST')
        self.clusive_user.save()
        self.book = Book.objects.create(title='Test Book')
        self.book.save()
        self.bv_0 = BookVersion.objects.create(book=self.book, sortOrder=0,
                                            glossary_words='["test"]',
                                            all_words='["test", "the", "end"]')
        self.bv_1 = BookVersion.objects.create(book=self.book, sortOrder=1,
                                            glossary_words='["test tricky"]',
                                            all_words='["a", "tricky", "test", "the", "end"]',
                                            new_words='["a", "tricky"]')

    def login_and_generate_page_event_id(self):
        login = self.client.login(username='user1', password='password1')
        library_page_response = self.client.get('/library/public')
        page_view_event = Event.objects.latest('event_time')
        self.event_id = page_view_event.id

    def test_set_and_get_rating(self):
        self.login_and_generate_page_event_id()
        response = self.client.get('/glossary/rating/checkin/something/2', HTTP_CLUSIVE_PAGE_EVENT_ID=self.event_id)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                             {'success': 1})
        response = self.client.get('/glossary/rating/something')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                             {'rating': 2})

    def test_get_rating_if_none(self):
        self.login_and_generate_page_event_id()
        response = self.client.get('/glossary/rating/something')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                     {'word': 'something', 'rating': False})

    def test_cuelist(self):
        words = glossary.views.choose_words_to_cue(self.bv_0, self.clusive_user)
        self.assertEqual(words, {'test': ['test', 'tested', 'testing', 'tests']})

    def test_definition(self):
        self.login_and_generate_page_event_id()
        response = self.client.get('/glossary/glossdef/%d/0/word' % (self.book.pk), HTTP_CLUSIVE_PAGE_EVENT_ID=self.event_id)
        self.assertEqual(response.status_code, 200)
        self.assertInHTML('<span class="definition-example">we had a word or two about it</span>', response.content.decode('utf8'), 1)

    def test_base_forms(self):
        self.assertEqual('noun', base_form('noun'))
        self.assertEqual('noun', base_form('nouns'))
        self.assertEqual('act', base_form('acting'))
        self.assertEqual('act', base_form('acted'))
        self.assertEqual('go', base_form('went'))
        self.assertEqual('go', base_form('goes'))
        self.assertEqual('large', base_form('largest'))
        self.assertEqual('text', base_form('texts'))
        self.assertEqual('install', base_form('installing')) # Not British 'instal'
        self.assertEqual('more', base_form('more')) # alphabetically before the other possibility, "much"
        self.assertEqual('ooblecks', base_form('ooblecks')) # unknown word is passed through as is

    def test_inflected_forms(self):
        self.assertEqual(['noun', 'nouns'], all_forms('noun'))
        self.assertEqual(['act', 'acted', 'acting', 'acts'], all_forms('ACT'))
        self.assertEqual(['fluffy', 'fluffier', 'fluffiest'], all_forms('fluffy'))
        self.assertEqual(['focus', 'foci', 'focused', 'focuses', 'focusing', 'focussed', 'focusses', 'focussing'],
                         all_forms('focus')) # Base form should be returned first despite being alphabetically later.

    def test_check_list(self):
        self.login_and_generate_page_event_id()
        response = self.client.get('/glossary/checklist/%d' % self.book.pk)
        logger.error("RESPONSE: %s", response.content)
        self.assertEqual(200, response.status_code)
        # Should pick new words but ignore "a" since it's too short.
        self.assertJSONEqual(response.content, {'words': ['tricky']})

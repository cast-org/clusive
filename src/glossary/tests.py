import json
import logging
import os

from django.contrib.auth.models import User

from glossary.util import base_form, all_forms
from library.models import Book, BookVersion
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)

from django.contrib.staticfiles import finders
from django.test import TestCase


class GlossaryTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST').save()
        book = Book.objects.create(path='test', title='Test Book')
        book.save()
        book_1 = BookVersion.objects.create(book=book, sortOrder=0,
                                            glossary_words='["test"]',
                                            all_words='["test", "the", "end"]')
        book_1.save()

    def test_set_and_get_rating(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/rating/something/2')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                             {'success': 1})
        response = self.client.get('/glossary/rating/something')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                             {'rating': 2})

    def test_get_rating_if_none(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/rating/something')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                     {'word': 'something', 'rating': False})

    def test_cuelist(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/cuelist/test/0')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                                 {'words': {'test': ['test', 'tested', 'testing', 'tests']}})

    def test_definition(self):
        #login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/glossdef/test/0/word')
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
        self.assertEqual('more', base_form('more')) # alphabetically before the other possibility, "much"
        self.assertEqual('ooblecks', base_form('ooblecks')) # unknown word is passed through as is

    def test_inflected_forms(self):
        self.assertEqual({'noun', 'nouns'}, all_forms('noun'))
        self.assertEqual({'act', 'acts', 'acting', 'acted'}, all_forms('act'))
        self.assertEqual({'fluffy', 'fluffier', 'fluffiest'}, all_forms('fluffy'))

    def test_static_glossaries(self):
            pubs_directory = finders.find('shared/pubs')
            book_dirs = os.scandir(pubs_directory)
            for book_dir in book_dirs:
                glossfile = os.path.join(book_dir, 'glossary.json')
                if os.path.exists(glossfile):
                    with open(glossfile, 'r', encoding='utf-8') as file:
                        glossary = json.load(file)
                        for entry in glossary:
                            assert 'headword' in entry, \
                                "In %s, missing headword in %s" % (glossfile, entry)
                            # assert entry['headword'] == base_form(entry['headword']) or entry['headword']=='install', \
                            #             "In %s, glossary word %s is not base form, should be %s" \
                            #             % (glossfile, entry['headword'], base_form(entry['headword']))
                            if entry['headword'] != base_form(entry['headword']):
                                logger.info("Non baseform in %s: %s (should be %s)",
                                            glossfile, entry['headword'], base_form(entry['headword']))
                            assert 'alternateForms' in entry, \
                                "In %s, %s missing alternateForms" % (glossfile, entry['headword'])
                            assert 'meanings' in entry, \
                                "In %s, %s missing meanings" % (glossfile, entry['headword'])
                            for m in entry['meanings']:
                                assert 'pos' in m, \
                                    "In %s word %s, missing pos in %s" % (glossfile, entry['headword'], m)
                                assert 'definition' in m, \
                                    "In %s word %s, missing definition in %s" % (glossfile, entry['headword'], m)
                                assert 'examples' in m, \
                                    "In %s word %s, missing examples in %s" % (glossfile, entry['headword'], m)
                                if 'images' in m:
                                    for i in m['images']:
                                        assert 'src' in i, "In %s word %s, missing src for image" % (glossfile, entry['headword'])
                                        assert os.path.exists(os.path.join(book_dir, i['src'])), \
                                            "In %s word %s, image doesn't exist: %s" % (glossfile, entry['headword'], os.path.join(book_dir, i['src']))
                                        assert 'alt' in i, "In %s word %s, missing alt for image" % (glossfile, entry['headword'])
                                        assert 'description' in i, "In %s word %s, missing description for image" % (glossfile, entry['headword'])
                                        # optional for now
                                        # assert 'caption' in i, "In %s word %s, missing caption for image" % (glossfile, entry['headword'])
                                        # assert 'source' in i, "In %s word %s, missing source for image" % (glossfile, entry['headword'])
                else:
                    logger.error("Book directory has no glossary: %s", book_dir)

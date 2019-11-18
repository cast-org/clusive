import json
import logging
import os

from django.contrib.auth.models import User
from django.urls import reverse

from library.models import Book
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)

from django.contrib.staticfiles import finders
from django.test import TestCase


class GlossaryTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST').save()
        book_1 = Book.objects.create(path='test', title='Test Book',
                                     all_words='["test", "the", "end"]',
                                     glossary_words='["test"]')
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
                     {'rating': False})

    def test_cuelist(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/cuelist/test')
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf8'),
                                 {'words': ['test']})

    def test_definition(self):
        #login = self.client.login(username='user1', password='password1')
        response = self.client.get('/glossary/glossdef/test/0/word')
        self.assertEqual(response.status_code, 200)
        self.assertInHTML('<em>we had a word or two about it</em>', response.content.decode('utf8'), 1)

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

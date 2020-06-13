import os

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import TestCase

# Create your tests here.
from django.urls import reverse

from roster.models import ClusiveUser
from .models import Book, Paradata
from .parsing import TextExtractor


class LibraryTestCase(TestCase):

    def test_text_extraction(self):
        te = TextExtractor()
        result = te.extract(
            '<html><head><title>Hi</title></head><body><p>Some nice text.</p><script type="text/javascript">Script</script><p>More and nicer texts.</p></body></html>')
        self.assertEqual(result, "Some nice text. More and nicer texts. ")
        self.assertSetEqual({'and', 'some', 'more', 'nice', 'text'}, te.get_word_set(),
                            "Did not extract correct set of words")

    def test_parse_file(self):
        te = TextExtractor()
        te.feed_file(finders.find('shared/pubs/serp-penguins/1/OEBPS/content.xhtml'))
        te.close()
        result = te.text
        self.assertRegex(result, "Penguins are funny birds")
        self.assertNotRegex(result, "Photo")
        word_set = te.get_word_set()
        print(word_set)
        self.assertTrue('penguin' in word_set, "Parser didn't find a penguin in the penguins article")
        self.assertFalse('1' in word_set, "Parser didn't exclude number")


class LibraryApiTestCase(TestCase):

    def setUp(self):
        user_1 = User.objects.create_user(username="user1", password="password1")
        user_1.save()
        ClusiveUser.objects.create(anon_id="Student1", user=user_1, role='ST').save()

    def test_setlocation_error_for_get(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.get(reverse('setlocation'))
        self.assertEqual(response.status_code, 405)

    def test_setlocation_error_for_nonexistent_book(self):
        login = self.client.login(username='user1', password='password1')
        response = self.client.post(reverse('setlocation'), { 'book' : 'book1', 'locator' : 'testtest'})
        self.assertEqual(response.status_code, 404)

    def test_setlocation(self):
        book = Book.objects.create(path='book1', title='Book One', description='')
        book.save()
        login = self.client.login(username='user1', password='password1')
        response = self.client.post(reverse('setlocation'), { 'book' : 'book1', 'locator' : 'testtest'})
        self.assertEqual(response.status_code, 200)
        pd = Paradata.objects.get(book__path='book1')
        self.assertEqual('testtest', pd.lastLocation)

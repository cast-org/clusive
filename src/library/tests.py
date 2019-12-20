import os

from django.contrib.staticfiles import finders
from django.test import TestCase

# Create your tests here.
from .parsing import TextExtractor


class LibraryTestCase(TestCase):

    def test_text_extraction(self):
        te = TextExtractor()
        result = te.extract('<html><head><title>Hi</title></head><body><p>Some nice text.</p><script type="text/javascript">Script</script><p>More and nicer texts.</p></body></html>')
        self.assertEqual(result, "Some nice text. More and nicer texts. ")
        self.assertSetEqual({'and', 'some', 'more', 'nice', 'text'}, te.get_word_set(), "Did not extract correct set of words")

    def test_parse_file(self):
        te = TextExtractor()
        te.feed_file(finders.find('shared/pubs/serp-penguins-2/OEBPS/content.xhtml'))
        te.close()
        result = te.text
        self.assertRegex(result, "Penguins are funny birds")
        self.assertNotRegex(result, "Photo")
        word_set = te.get_word_set()
        print(word_set)
        self.assertTrue('penguin' in word_set, "Parser didn't find a penguin in the penguins article")
        self.assertFalse('1' in word_set, "Parser didn't exclude number")

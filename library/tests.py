import os

from django.contrib.staticfiles import finders
from django.test import TestCase

# Create your tests here.
from .parsing import TextExtractor


class LibraryTestCase(TestCase):

    def test_text_extraction(self):
        te = TextExtractor()
        result = te.extract('<html><head><title>Hi</title></head><body><p>Some text.</p><script type="text/javascript">Script</script><p>More text.</p></body></html>')
        self.assertEqual(result, "Some text. More text. ")
        self.assertSetEqual({'some', 'more', 'text'}, te.get_word_set(), "Did not extract correct set of words")

    def test_parse_file(self):
        te = TextExtractor()
        te.feed_file(finders.find('shared/pubs/serp-penguins-2/OEBPS/content.xhtml'))
        te.close()
        result = te.text
        self.assertRegex(result, "Penguins are funny birds")
        self.assertNotRegex(result, "Photo")
        word_set = te.get_word_set()
        self.assertTrue('penguins' in word_set, "Parser didn't find penguins in penguins article")
        self.assertFalse('1' in word_set, "Parser didn't exclude number")

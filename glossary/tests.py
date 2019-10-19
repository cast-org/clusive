import json
import logging
import os

logger = logging.getLogger(__name__)

from django.contrib.staticfiles import finders
from django.test import TestCase


class GlossaryTestCase(TestCase):

    def test_static_glossaries(self):
        pubs_directory = finders.find('shared/pubs')
        book_dirs = os.scandir(pubs_directory)
        for book_dir in book_dirs:
            glossfile = os.path.join(book_dir, 'glossary.json')
            if os.path.exists(glossfile):
                with open(glossfile, 'r') as file:
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
                            # assert 'images' in m, \
                            #     "In %s word %s, missing images in %s" % (glossfile, entry['headword'], m)

            else:
                logger.error("Book directory has no glossary: %s", book_dir)

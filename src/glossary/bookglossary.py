import json
import logging

import glossary.util as glossaryutil
from library.models import Book

logger = logging.getLogger(__name__)

# Methods for looking up words in a book's glossary

class BookGlossary:

    book = None
    data = None

    def __init__(self, book_id):
        self.book_id = book_id

    def init_data(self):
        self.data = {}
        try:
            book = Book.objects.get(id=self.book_id)
            with open(book.glossary_storage, 'r', encoding='utf-8') as file:
                logger.debug("Reading glossary %s", file.name)
                rawdata = json.load(file)
                self.data = {}
                for worddata in rawdata:
                    base = glossaryutil.base_form(worddata['headword'])
                    self.data[base] = worddata
                    for altform in worddata['alternateForms']:
                        self.data[altform.lower()] = worddata
        except FileNotFoundError:
            logger.warning('Book %s has no glossary', book)
        except EnvironmentError:
            logger.error('Failed to read glossary data')

    def lookup(self, word):
        if self.data is None:
            self.init_data()
        return self.data.get(word.lower())

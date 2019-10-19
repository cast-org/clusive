import json
import logging
import os

from django.contrib.staticfiles import finders

logger = logging.getLogger(__name__)

# Methods for looking up words in a book's glossary

class BookGlossary:

    book = None
    data = None

    def __init__(self, book):
        self.book = book

    def init_data(self):
        pubs_directory = finders.find('shared/pubs')
        book_dir = os.path.join(pubs_directory, self.book)
        try:
            with open(os.path.join(book_dir, 'glossary.json'), 'r') as file:
                logger.debug("Reading glossary %s", file.name)
                rawdata = json.load(file)
                self.data = {}
                for worddata in rawdata:
                    self.data[worddata['headword'].lower()] = worddata
                    for altform in worddata['alternateForms']:
                        self.data[altform.lower()] = worddata
        except EnvironmentError:
            logger.error("Failed to read glossary data")

    def lookup(self, word):
        if not self.data:
            self.init_data()
        return self.data.get(word.lower())


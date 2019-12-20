import logging
from html.parser import HTMLParser

from nltk import RegexpTokenizer
from glossary.util import base_form

logger = logging.getLogger(__name__)


class TextExtractor(HTMLParser):
    element_stack = []
    text = ''
    file = None

    ignored_elements = {'head', 'script'}
    delimiter = ' '

    def feed_file(self, file):
        self.file = file
        with open(file, 'r', encoding='utf-8') as html:
            for line in html:
                self.feed(line)
        self.file = None

    def get_word_set(self):
        self.close()
        token_list = RegexpTokenizer(r'\w+').tokenize(self.text)
        token_set = set([base for base in
                         (base_form(w) for w in token_list if w.isalpha())
                         if base is not None])
        return token_set

    def extract(self, html):
        self.feed(html)
        self.close()
        return self.text

    def handle_starttag(self, tag, attrs):
        self.element_stack.insert(0, tag)

    def handle_endtag(self, tag):
        if not tag in self.element_stack:
            logger.warning("Warning: close tag for element that is not open: %s in %s; file=",
                        tag, self.element_stack, self.file)
            return
        index = self.element_stack.index(tag)
        if index > 0:
            logger.warning("Warning: improper nesting of end tag %s in %s; file=%s",
                        tag, self.element_stack, self.file)
        del self.element_stack[0:index+1]

    def handle_data(self, data):
        if len(self.ignored_elements.intersection(self.element_stack)) == 0:
            self.text += data + self.delimiter

    def error(self, message):
        logger.error(message)

import logging

from lemminflect import getAllLemmas, getAllInflections

from wordnet import util as wordnetutil
from .bookglossary import BookGlossary

logger = logging.getLogger(__name__)

# Note, currently lookup depends directly on Wordnet.
# Eventually, the goal is to have multiple possible backends and a way to
# configure which one(s) to use.

book_glossaries = {}


def has_definition(book_id, word):
    """Determine whether the given word exists in our dictionary.
     We don't want to query or cue words when we don't have a defintion."""
    return lookup(book_id, word) is not None


def lookup(book_id, word):
    # First try to find in a book glossary
    if not book_glossaries.get(book_id):
        book_glossaries[book_id] = BookGlossary(book_id)
    defs = book_glossaries[book_id].lookup(word)
    if (defs):
        defs['source'] = 'Book'
    else:
        # Next try Wordnet
        defs = wordnetutil.lookup(word)
        if (defs):
            defs['source'] = 'Wordnet'
    return defs


def base_form(word):
    wl = word.lower()
    all_forms = set()
    for pos, lemmas in getAllLemmas(wl).items():
        # logger.debug("%s as %s simplifies to %s", wl, pos, lemmas)
        all_forms.update(lemmas)
    # There may be multiple base forms for a word, eg "outing" is base form of noun, but inflected form of verb "out".
    # We somewhat arbitrarily choose the shortest one.
    if all_forms:
        return min(all_forms, key=base_form_sort_key)
    else:
        return wl


def base_form_sort_key(word):
    # We sort by length primarily, so that the shortest potential base form will be returned.
    # Within length, sort alphabetically. Needed so that return value is deterministic even with multiple,
    # same-length base forms possible  (eg "more" -> "more" or "much")
    return "%03d%s" % (len(word), word)


def all_forms(word):
    wl = word.lower()
    all_forms = set()
    all_forms.add(wl)
    for list in getAllInflections(wl).values():
        all_forms.update(list)
    return all_forms

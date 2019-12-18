import logging
from itertools import chain

from lemminflect import getAllLemmas, getAllInflections

logger = logging.getLogger(__name__)


# There may be multiple base forms for a word, eg "outing" is base form of noun, but inflected form of verb "out".
# We somewhat arbitrarily choose the shortest one.
def base_form(word):
    wl = word.lower()
    all_forms = set()
    for pos, lemmas in getAllLemmas(wl).items():
        # logger.debug("%s as %s simplifies to %s", wl, pos, lemmas)
        all_forms.update(lemmas)
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

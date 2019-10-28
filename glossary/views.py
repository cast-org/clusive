import json
import logging
import random

from django.shortcuts import render

from django.http import JsonResponse, HttpResponseNotFound

from glossary.apps import GlossaryConfig
from glossary.bookglossary import BookGlossary
from glossary.models import WordModel
from library.models import Book
from roster.models import ClusiveUser
from wordnet import util as wordnetutil
from eventlog.signals import vocab_lookup

logger = logging.getLogger(__name__)

# Note, currently these views depend directly on Wordnet.
# Eventually, the goal is to have multiple possible backends and a way to
# configure which one(s) to use.

book_glossaries = {}


def cuelist(request, document):
    """Return the list of words that should be cued in this document for this user"""
    try:
        user = ClusiveUser.objects.get(user=request.user)
        book = Book.objects.get(path=document)
        all_glossary_words = json.loads(book.glossary_words)
        all_words = json.loads(book.all_words)
        user_words = WordModel.objects.filter(user=user, word__in=all_words)

        # Target number of words.  For now, just pick an arbitrary number.
        # TODO: target number should depend on word count of the book.
        to_find = 10

        # First, find any words where we think the user is interested
        interest_words = [wm.word for wm in user_words if wm.interest_est() > 0]
        logger.debug("Found %d interest words: %s", len(interest_words), interest_words)
        to_find -= len(interest_words)

        # Next look for words where the user has low estimated knowledge (TODO)

        # Fill up the list with glossary words
        glossary_words = []
        if to_find > 0:
            glossary_words = random.sample(all_glossary_words, k=min(to_find, len(all_glossary_words)))
            logger.debug("Found %d glossary words: %s", len(glossary_words), glossary_words)

        cue_words = set(interest_words + glossary_words)
        WordModel.register_cues(user, cue_words)

        return JsonResponse({'words': sorted(cue_words)})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch cue words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})

def glossdef(request, document, cued, word):
    """Return a formatted HTML representation of a word's meaning(s)."""
    source = None

    # First try to find in a book glossary
    if not book_glossaries.get(document):
        book_glossaries[document] = BookGlossary(document)
    defs = book_glossaries[document].lookup(word)
    if (defs):
        source = 'Book'
    else:
        # Next try Wordnet
        defs = wordnetutil.lookup(word)
        source = 'Wordnet'

    vocab_lookup.send(sender=GlossaryConfig.__class__,
                      request=request,
                      word=word,
                      cued=cued,
                      source = source)
    # TODO might want to record how many meanings were found (especially if it's 0): len(defs['meanings'])
    if defs:
        context = {'defs': defs, 'pub_id': document}
        return render(request, 'glossary/glossdef.html', context=context)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")


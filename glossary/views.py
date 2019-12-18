import json
import logging
import random

from django.shortcuts import render

from django.http import JsonResponse, HttpResponseNotFound

from glossary.apps import GlossaryConfig
from glossary.bookglossary import BookGlossary
from glossary.models import WordModel
from glossary.utils import base_form, all_forms
from library.models import Book
from roster.models import ClusiveUser
from wordnet import util as wordnetutil
from eventlog.signals import vocab_lookup

logger = logging.getLogger(__name__)

# Note, currently these views depend directly on Wordnet.
# Eventually, the goal is to have multiple possible backends and a way to
# configure which one(s) to use.

book_glossaries = {}


def checklist(request, document):
    """Return up to five words that should be presented in the vocab check dialog"""
    try:
        user = ClusiveUser.objects.get(user=request.user)
        book = Book.objects.get(path=document)
        all_glossary_words = json.loads(book.glossary_words)
        all_words = json.loads(book.all_words) + all_glossary_words # FIXME might not be necessary with stemming, glossary should be a subset of all
        user_words = WordModel.objects.filter(user=user, word__in=all_words)

        to_find = 5
        # First, look for any glossary words that we don't have a rating for yet.
        #logger.debug("Checking: %s", all_glossary_words)
        #logger.debug("Against:  %s", [[wm.word, wm.rating] for wm in user_words])
        gloss_words = [w for w in all_glossary_words if not any(wm.word==w and wm.rating!=None for wm in user_words)]
        logger.debug("Check words from glossary: %s", gloss_words)

        check_words = random.sample(gloss_words, k=min(to_find, len(gloss_words)))
        return JsonResponse({'words': sorted(check_words)})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch check words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})
    except Book.DoesNotExist:
        logger.error("Unknown book %s", document)
        return JsonResponse({'words': []})

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
        interest_words = [wm.word for wm in user_words
                          if wm.interest_est()>0 and (wm.knowledge_est()==None or wm.knowledge_est()<3)]
        logger.debug("Found %d interest words: %s", len(interest_words), interest_words)
        cue_words = set(interest_words)

        # Next look for words where the user has low estimated knowledge
        if len(cue_words) < to_find:
            unknown_words = set([wm.word for wm in user_words if wm.knowledge_est() and wm.knowledge_est() < 2])
            logger.debug("Found:  %d low-knowledge words: %s", len(unknown_words), unknown_words)
            unknown_words = unknown_words-cue_words
            #logger.debug("Filter: %d low-knowledge words: %s", len(unknown_words), unknown_words)
            unknown_words = set(random.sample(unknown_words, k=min(to_find-len(cue_words), len(unknown_words))))
            #logger.debug("Trim:   %d low-knowledge words: %s", len(unknown_words), unknown_words)
            cue_words = cue_words | unknown_words

        # Fill up the list with glossary words
        if len(cue_words) < to_find:
            glossary_words = set(random.sample(all_glossary_words,
                                               k=min(to_find-len(cue_words), len(all_glossary_words))))
            logger.debug("Found %d glossary words: %s", len(glossary_words), glossary_words)
            cue_words = cue_words | glossary_words

        WordModel.register_cues(user, cue_words)

        map_to_forms = {}
        for word in cue_words:
            map_to_forms[word] = sorted(all_forms(word))

        return JsonResponse({'words': map_to_forms})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch cue words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})

def glossdef(request, document, cued, word):
    """Return a formatted HTML representation of a word's meaning(s)."""
    source = None
    base = base_form(word)

    # First try to find in a book glossary
    if not book_glossaries.get(document):
        book_glossaries[document] = BookGlossary(document)
    defs = book_glossaries[document].lookup(base)
    if (defs):
        source = 'Book'
    else:
        # Next try Wordnet
        defs = wordnetutil.lookup(base)
        source = 'Wordnet'

    vocab_lookup.send(sender=GlossaryConfig.__class__,
                      request=request,
                      word=base,
                      cued=cued,
                      source = source)
    # TODO might want to record how many meanings were found (especially if it's 0): len(defs['meanings'])
    if defs:
        context = {'defs': defs, 'pub_id': document}
        return render(request, 'glossary/glossdef.html', context=context)
    else:
        return HttpResponseNotFound("<p>No definition found</p>")


def get_word_rating(request, word):
    try:
        user = ClusiveUser.objects.get(user=request.user)
        base = base_form(word)
        wm = WordModel.objects.get(user=user, word=base)
        return JsonResponse({ 'rating': wm.rating })
    except WordModel.DoesNotExist:
        return JsonResponse({'word' : base,
                             'rating' : False})
    except ClusiveUser.DoesNotExist:
        logger.warning("No clusive user, can't fetch ratings")
        return JsonResponse({'word' : base,
                             'rating' : False})


def set_word_rating(request, word, rating):
    try:
        user = ClusiveUser.objects.get(user=request.user)
        base = base_form(word)
        wm, created = WordModel.objects.get_or_create(user=user, word=base)
        if WordModel.is_valid_rating(rating):
            wm.rating = rating
            wm.save()
            return JsonResponse({'success' : 1})
        else:
            return JsonResponse({'success' : 0})
    except ClusiveUser.DoesNotExist:
        logger.warning("No clusive user, can't set ratings")
        return JsonResponse({'success' : 0})

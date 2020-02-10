import json
import logging
import random

from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render

from eventlog.signals import vocab_lookup
from glossary.apps import GlossaryConfig
from glossary.models import WordModel
from glossary.util import base_form, all_forms, lookup, has_definition
from library.models import Book, BookVersion
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


def checklist(request, document):
    """Return up to five words that should be presented in the vocab check dialog"""
    try:
        user = ClusiveUser.objects.get(user=request.user)
        version = 1  # FIXME will need to look up glossary words for all versions and adjust algorithm.
        bv = BookVersion.lookup(path=document, versionNumber=version)
        all_glossary_words = json.loads(bv.glossary_words)
        all_words = json.loads(bv.all_words) + all_glossary_words # FIXME might not be necessary with stemming, glossary should be a subset of all
        user_words = WordModel.objects.filter(user=user, word__in=all_words)

        to_find = 5
        # First, look for any glossary words that we don't have a rating for yet.
        #logger.debug("Checking: %s", all_glossary_words)
        #logger.debug("Against:  %s", [[wm.word, wm.rating] for wm in user_words])
        gloss_words = [w for w in all_glossary_words if not any(wm.word==w and wm.rating!=None for wm in user_words)]
        logger.debug("Check words from glossary: %s", gloss_words)
        check_words = random.sample(gloss_words, k=min(to_find, len(gloss_words)))
        # TODO: consider other challenging words from article if all glossary words already have ratings
        return JsonResponse({'words': sorted(check_words)})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch check words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})
    except BookVersion.DoesNotExist:
        logger.error("Unknown BookVersion %s:%d", document, version)
        return JsonResponse({'words': []})


def cuelist(request, document, version):
    """Return the list of words that should be cued in this document for this user"""
    try:
        user = ClusiveUser.objects.get(user=request.user)
        bv = BookVersion.lookup(path=document, versionNumber=version)
        all_glossary_words = json.loads(bv.glossary_words)
        all_words = json.loads(bv.all_words)
        user_words = WordModel.objects.filter(user=user, word__in=all_words)

        # Target number of words.  For now, just pick an arbitrary number.
        # TODO: target number should depend on word count of the book.
        to_find = 10

        # First, find any words where we think the user is interested
        interest_words = [wm.word for wm in user_words
                          if wm.interest_est()>0
                          and (wm.knowledge_est()==None or wm.knowledge_est()<3)
                          and has_definition(document, wm.word)]
        logger.debug("Found %d interest words: %s", len(interest_words), interest_words)
        cue_words = set(interest_words)

        # Next look for words where the user has low estimated knowledge
        if len(cue_words) < to_find:
            unknown_words = set([wm.word for wm in user_words
                                 if wm.knowledge_est()
                                 and wm.knowledge_est() < 2
                                 and has_definition(document, wm.word)])
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
    base = base_form(word)
    defs = lookup(document, base)

    vocab_lookup.send(sender=GlossaryConfig.__class__,
                      request=request,
                      word=base,
                      cued=cued,
                      source = defs['source'] if defs else None)
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
            wm.register_rating(rating)
            return JsonResponse({'success' : 1})
        else:
            return JsonResponse({'success' : 0})
    except ClusiveUser.DoesNotExist:
        logger.warning("No clusive user, can't set ratings")
        return JsonResponse({'success' : 0})


def word_bank_remove(request, word):
    try:
        user = ClusiveUser.objects.get(user=request.user)
        base = base_form(word)
        wm = WordModel.objects.get(user=user, word=base)
        if wm:
            wm.register_wordbank_remove()
            return JsonResponse({'success' : 1})
        else:
            return JsonResponse({'success' : 0})
    except ClusiveUser.DoesNotExist:
        logger.warning("No clusive user, can't remove word")
        return JsonResponse({'success' : 0})

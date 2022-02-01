import logging
import random

from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render

from eventlog.signals import vocab_lookup, word_rated, word_removed
from glossary.apps import GlossaryConfig
from glossary.models import WordModel
from glossary.util import base_form, all_forms, lookup, has_definition
from library.models import Book, BookVersion, Paradata
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


def checklist(request, book_id):
    """Return up to five words that should be presented in the vocab check dialog"""
    try:
        user = request.clusive_user
        book = Book.objects.get(id=book_id)
        paradata, created = Paradata.objects.get_or_create(user=user, book=book)

        # We present a checklist only the first time a user goes to a new Book
        if paradata.view_count > 0:
            logger.debug('Book already viewed, skipping checklist')
            return JsonResponse({'words': []})

        versions = BookVersion.objects.filter(book=book)
        to_find = 5
        min_word_length = 4
        check_words = set()

        if len(versions) > 1:
            # Multiple versions, so we want to use our check words to determine which version to show.
            # Create two lists for each version above the simplest:
            #   All "new" words in this version that are not yet rated and > 3 letters
            #   The subset of that list that are glossary words.
            for bv in versions:
                if bv.sortOrder > 0:
                    logger.debug("%s all new words: %s", bv, bv.new_word_list)
                    user_words = WordModel.objects.filter(user=user, word__in=bv.new_word_list)
                    bv.potential_words = [w for w in bv.new_word_list if len(w)>=min_word_length and not any(wm.word==w and wm.rating!=None for wm in user_words)]
                    logger.debug("%s potential: %s", bv, bv.potential_words)
                    bv.potential_gloss_words = [w for w in bv.potential_words if w in bv.glossary_word_list]
                    logger.debug("%s glossary:  %s", bv, bv.potential_gloss_words)
            # Now pick words from these lists, round-robin style so we get a reasonably even distribution.
            some_potential_words_remain = True # Make sure there are words left somewhere
            while len(check_words) < to_find and some_potential_words_remain:
                some_potential_words_remain = False
                for bv in versions:
                    if bv.sortOrder > 0:
                        if len(bv.potential_gloss_words) > 0:  # Glossary word is preferred if there is one
                            word = random.choice(bv.potential_gloss_words)
                            check_words.add(word)
                            bv.potential_gloss_words.remove(word)
                            bv.potential_words.remove(word)
                        else:
                            if len(bv.potential_words) > 0:    # Otherwise any new word.
                                word = random.choice(bv.potential_words)
                                check_words.add(word)
                                bv.potential_words.remove(word)
                        if len(check_words) == to_find:
                            break
                        if len(bv.potential_words) > 0:
                            some_potential_words_remain = True
            logger.debug("Picked: %s", check_words)
        else:
            # There is only one version.  Pick a sample of unrated glossary words.
            bv = versions[0]
            glossary_words = bv.glossary_word_list
            user_words = WordModel.objects.filter(user=user, word__in=glossary_words)

            # Look for any glossary words that we don't have a rating for yet.
            #logger.debug("Checking: %s", all_glossary_words)
            #logger.debug("Against:  %s", [[wm.word, wm.rating] for wm in user_words])
            gloss_words = [w for w in glossary_words if not any(wm.word==w and wm.rating!=None for wm in user_words)]
            logger.debug("Single version. Check words from glossary: %s", gloss_words)
            check_words = random.sample(gloss_words, k=min(to_find, len(gloss_words)))

            if len(check_words) < to_find:
                # Still not enough words - maybe there was no glossary.
                # Choose other challenging words from article to fill up the list.
                for w in bv.all_word_list:
                    if len(w) < min_word_length or not has_definition(book, w):
                        continue
                    # It's a potential word; make sure it hasn't been rated already:
                    user_word = WordModel.objects.filter(user=user, word=w)
                    if len(user_word)>0 and user_word[0].rating is not None:
                        continue
                    # Add to list and see if we're done.
                    check_words.append(w)
                    if len(check_words) == to_find:
                        break

        return JsonResponse({'words': sorted(check_words)})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch check words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})
    except BookVersion.DoesNotExist:
        logger.error("No BookVersions found for book %d", book_id)
        return JsonResponse({'words': []})


def cuelist(request, book_id, version):
    """Return the list of words that should be cued in this document for this user"""
    ## TODO: can delete, no longer used.
    try:
        bv = BookVersion.lookup(book_id=book_id, version_number=version)
        map_to_forms = choose_words_to_cue(bv, request.clusive_user)
        return JsonResponse({'words': map_to_forms})
    except ClusiveUser.DoesNotExist:
        logger.warning("Could not fetch cue words, no Clusive user: %s", request.user)
        return JsonResponse({'words': []})


def choose_words_to_cue(book_version: BookVersion, user: ClusiveUser):
    """
    For a given BookVersion and ClusiveUser, choose up to 10 words to cue on the reading page.
    :param book_version:
    :param user:
    :return: a dict. The key of each entry is the baseform of a word, and the value is a list of all the forms.
    """
    all_glossary_words = book_version.glossary_word_list
    all_book_words = book_version.all_word_list

    # Get all of user's words
    all_user_words = list(WordModel.objects.filter(user=user))

    # Filter user's word list by words in the book
    user_words = [wm for wm in all_user_words
                  if wm.word in all_book_words
                  ]

    # Target number of words.  For now, just pick an arbitrary number.
    # TODO: target number should depend on word count of the book.
    to_find = 10

    # First, find any words where we think the user is interested
    interest_words = [wm.word for wm in user_words
                      if wm.interest_est() > 0
                      and (wm.knowledge_est()==None or wm.knowledge_est()<3)
                      and has_definition(book_version.book, wm.word)]
    logger.debug("Found %d interest words: %s", len(interest_words), interest_words)
    cue_words = set(interest_words)

    # Next look for words where the user has low estimated knowledge
    if len(cue_words) < to_find:
        unknown_words = set([wm.word for wm in user_words
                             if wm.knowledge_est()
                             and wm.knowledge_est() < 2
                             and has_definition(book_version.book, wm.word)])
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

    map_to_forms = {}
    for word in cue_words:
        map_to_forms[word] = all_forms(word)
    return map_to_forms


def glossdef(request, book_id, cued, word):
    """Return a formatted HTML representation of a word's meaning(s)."""
    base = base_form(word)
    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist:
        book = None
    defs = lookup(book, base)

    # logging an event in the eventlog
    vocab_lookup.send(sender=GlossaryConfig.__class__,
                      request=request,
                      word=base,
                      cued=cued,
                      book=book,
                      source = defs['source'] if defs else None)
    # TODO might want to record how many meanings were found (especially if it's 0): len(defs['meanings'])
    if defs:
        context = {'defs': defs}
        if book:
            context['book_path'] = book.path
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


def set_word_rating(request, control, word, rating):
    try:
        user = ClusiveUser.objects.get(user=request.user)
        base = base_form(word)
        wm, created = WordModel.objects.get_or_create(user=user, word=base)
        if WordModel.is_valid_rating(rating):
            wm.register_rating(rating)
            book_id = None
            if "bookId" in request.GET:
                book_id = request.GET.get("bookId")
            word_rated.send(sender=GlossaryConfig.__class__,
                            request=request,
                            book_id=book_id,
                            control=control,
                            word=word,
                            rating=rating)
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
            word_removed.send(sender=GlossaryConfig.__class__,
                              request=request,
                              word=word)
            return JsonResponse({'success' : 1})
        else:
            return JsonResponse({'success' : 0})
    except ClusiveUser.DoesNotExist:
        logger.warning("No clusive user, can't remove word")
        return JsonResponse({'success' : 0})

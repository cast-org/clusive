import logging
import random

from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render, get_object_or_404
from django.views import View

from eventlog.signals import vocab_lookup, word_rated, word_removed
from glossary.apps import GlossaryConfig
from glossary.models import WordModel
from glossary.util import base_form, all_forms, lookup, has_definition
from library.models import Book, BookVersion, Paradata, Customization
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


class ChecklistView(View):
    """Return up to five words that should be presented in the vocab check dialog"""

    def get(self, request, *args, **kwargs):
        book_id = kwargs.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        user = request.clusive_user
        paradata, created = Paradata.objects.get_or_create(user=user, book=book)

        # We present a checklist only the first time a user goes to a new Book
        if paradata.view_count > 0:
            logger.debug('Book already viewed, skipping checklist')
            return JsonResponse({'words': []})

        versions = BookVersion.objects.filter(book=book)
        customization = Customization.get_customization_for_user(book, user)
        custom_words = customization.word_list if customization else []
        logger.debug('customization: %s; words: %s', customization, custom_words)

        to_find = 5
        min_word_length = 4
        check_words = set()

        if len(versions) > 1:
            # Multiple versions, so we want to use our check words to determine which version to show.
            # Create three lists for each version above the simplest:
            #   All "new" words in this version that are not yet rated and at least min_word_length letters
            #   The subset of that list that are glossary words.
            #   the subset of that list that are custom words.
            for bv in versions:
                if bv.sortOrder > 0:
                    # logger.debug("%s all new words: %s", bv, bv.new_word_list)
                    user_words = WordModel.objects.filter(user=user, word__in=bv.new_word_list)
                    # logger.debug("  will ignore already rated: %s", list(user_words))
                    bv.potential_words = self.not_yet_rated(bv.new_word_list, user_words, min_length=min_word_length)
                    # logger.debug("%s potential: %s", bv, bv.potential_words)
                    bv.potential_gloss_words = [w for w in bv.glossary_word_list if w in bv.potential_words]
                    # logger.debug("%s glossary:  %s", bv, bv.potential_gloss_words)
                    bv.potential_custom_words = [w for w in custom_words if w in bv.potential_words]
                    # logger.debug("%s custom: %s", bv, bv.potential_custom_words)
            # Now pick words from these lists, round-robin style so we get a reasonably even distribution.
            some_potential_words_remain = True # Make sure there are words left somewhere
            while len(check_words) < to_find and some_potential_words_remain:
                some_potential_words_remain = False
                for bv in versions:
                    if bv.sortOrder > 0:
                        word = self.pick_from_lists(bv.potential_custom_words, bv.potential_gloss_words, bv.potential_words)
                        check_words.add(word)
                        if len(check_words) == to_find:
                            break
                        if len(bv.potential_words) > 0:
                            some_potential_words_remain = True
        else:
            # There is only one version.  Pick a sample of unrated words, preferring customized & glossary.
            bv = versions[0]
            glossary_words = bv.glossary_word_list
            user_words = WordModel.objects.filter(user=user, word__in=glossary_words)
            check_words = []

            # First, use custom words, if any.
            if custom_words:
                unrated_custom_words = self.not_yet_rated(custom_words, user_words)
                # logger.debug('Choosing from unrated custom words: %s', unrated_custom_words)
                check_words += random.sample(unrated_custom_words, k=min(to_find, len(unrated_custom_words)))
                # logger.debug('   words: %s', check_words)

            # Next try glossary words.
            if len(check_words) < to_find:
                unrated_glossary_words = self.not_yet_rated(glossary_words, user_words)
                # logger.debug("Choosing from unrated glossary words: %s", unrated_glossary_words)
                check_words += random.sample(unrated_glossary_words,
                                                 k=min(to_find-len(check_words), len(unrated_glossary_words)))
                # logger.debug('   words: %s', check_words)

            if len(check_words) < to_find:
                # Still not enough words - maybe there was no glossary.
                # Choose other challenging words from article to fill up the list.
                for w in bv.all_word_list:
                    if w in check_words:
                        continue
                    if len(w) < min_word_length or not has_definition(book, w, priority_lookup=False):
                        continue
                    # It's a potential word; make sure it hasn't been rated already:
                    user_word = WordModel.objects.filter(user=user, word=w)
                    if len(user_word)>0 and user_word[0].rating is not None:
                        continue
                    # Add to list and see if we're done.
                    check_words.append(w)
                    if len(check_words) == to_find:
                        break
        logger.debug("Picked: %s", check_words)
        return JsonResponse({'words': sorted(check_words)})

    def not_yet_rated(self, word_list, user_words, min_length=0):
        # Return a filtered list that does not include words already rated by the user
        return [w for w in word_list
                if len(w)>=min_length and not any(wm.word==w and wm.rating!=None for wm in user_words)]

    def pick_from_lists(self, *args):
        """
        Randomly choose a word from the first of the provided lists that has any elements.
        The word is removed from ALL lists in which it occurs, and is then returned.
        """
        word = None
        for list in args:
            if (len(list)>0):
                word = random.choice(list)
                logger.debug('    picked %s from %s', word, list)
                break
        if word:
            for list in args:
                try:
                    list.remove(word)
                except ValueError:
                    pass
        return word


def merge_into_set(old_set: set, new_set: set, max_count: int):
    """
    Add all or some items from new_set into old_set, without letting old_set get larger than max_count.
    If there isn't space to add all the items, a random sampling is chosen.
    :param old_set:
    :param new_set:
    :param max_count: desired size of set.
    :return: void
    """
    if len(old_set) >= max_count or len(new_set) == 0:
        return
    new_set_without_dups = new_set - old_set
    if len(old_set) + len(new_set_without_dups) < max_count:
        old_set |= new_set_without_dups
    else:
        sample = random.sample(new_set_without_dups, k=max_count - len(old_set))
        old_set |= set(sample)


def choose_words_to_cue(book_version: BookVersion, user: ClusiveUser):
    """
    For a given BookVersion and ClusiveUser, choose up to 10 words to cue on the reading page.
    :param book_version:
    :param user:
    :return: a dict. The key of each entry is the baseform of a word, and the value is a list of all the forms.
    """
    all_glossary_words = book_version.glossary_word_list
    all_book_words = book_version.all_word_list
    all_user_words = list(WordModel.objects.filter(user=user))

    # Filter user's word list by words in the book
    user_words = [wm for wm in all_user_words
                  if wm.word in all_book_words]

    # Target number of words.  For now, just pick an arbitrary number.
    # TODO: target number should depend on word count of the book.
    to_find = 10
    cue_words = set()

    # First, find any words where we think the user is interested & doesn't know word
    priority_lookup = False
    interest_words = [wm.word for wm in user_words
                      if wm.interest_est() > 0
                      and (wm.knowledge_est()==None or wm.knowledge_est()<3)
                      and has_definition(book_version.book, wm.word, priority_lookup)]
    logger.debug("Found %d interest words: %s", len(interest_words), interest_words)
    merge_into_set(cue_words, set(interest_words), max_count=to_find)

    # Next look for words in the teacher's Customization
    if len(cue_words) < to_find:
        customization = Customization.get_customization_for_user(book_version.book, user)
        if customization:
            custom_words = customization.word_list
            logger.debug("Found:  %d custom words: %s", len(custom_words), custom_words)
            # First, any custom words that are known to be low-knowledge
            low_knowledge_custom = [wm.word for wm in user_words
                                    if wm.word in custom_words
                                    and (wm.knowledge_est()==None or wm.knowledge_est()<3)]
            merge_into_set(cue_words, set(low_knowledge_custom), max_count=to_find)

            # Then, any others
            merge_into_set(cue_words, set(custom_words), max_count=to_find)

    # Next look for words where the user has low estimated knowledge
    if len(cue_words) < to_find:
        unknown_words = [wm.word for wm in user_words
                         if wm.knowledge_est()
                         and wm.knowledge_est() < 2
                         and has_definition(book_version.book, wm.word, priority_lookup)]
        logger.debug("Found:  %d low-knowledge words: %s", len(unknown_words), unknown_words)
        merge_into_set(cue_words, set(unknown_words), max_count=to_find)

    # Fill up the list with glossary words
    if len(cue_words) < to_find:
        merge_into_set(cue_words, set(all_glossary_words), max_count=to_find)

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
    priority_lookup = True
    defs = lookup(book, base, priority_lookup)

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

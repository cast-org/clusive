import logging
from typing import List

import math
import profanity_check
import regex
from nltk.corpus import wordnet
from wordfreq import zipf_frequency
from wordfreq.tokens import TOKEN_RE_WITH_PUNCTUATION

from glossary.models import WordModel
from glossary.util import base_form
from roster.models import ClusiveUser

logger = logging.getLogger(__name__)


class WordnetSimplifier:

    def __init__(self, lang: str) -> None:
        super().__init__()
        self.lang = lang

    def simplify_text(self, text: str, clusive_user: ClusiveUser = None, percent: int = 10, include_full=True):
        word_list = self.tokenize_no_casefold(text)
        # Returns frequency info about all distinct tokens, sorted by frequency
        # Each element of word_info returned is a dict with keys hw, alts, count, freq
        word_info = self.analyze_words(word_list)
        # How many words should we replace?
        to_replace = math.ceil(len(word_info) * percent / 100)
        # Has user indicated that they "know" or "use" any of these words?
        if clusive_user:
            known_words = WordModel.objects.filter(user=clusive_user, word__in=[i['hw'] for i in word_info], rating__gte=2).values('word')
            known_word_list = [val['word'] for val in known_words]
            logger.debug('Known words in simplification: %s', known_word_list)
            for i in word_info:
                if i['hw'] in known_word_list:
                    i['known'] = True

        # Now determine appropriate replacements for that many of the most difficult words.
        replacements = {}
        for i in word_info:
            hw = i['hw']
            if 'known' in i:
                i['errors'] = 'User knows this word'
            else:
                freq = i['freq']
                if include_full:
                    i['full_replacement'] = self.full_replacement_string(hw, freq)
                replacement_string, errors = self.best_replacement_string(hw, freq)
                if replacement_string:
                    replacements[hw] = replacement_string
                    i['replacement'] = replacement_string
                else:
                    i['errors'] = errors
                if len(replacements) >= to_replace:
                    break

        # Go through the full text again, adding in replacements where needed.
        out = ''
        for tok in word_list:
            base = base_form(tok, return_word_if_not_found=True)
            if base in replacements:
                rep = replacements[base]
                if tok[0].isupper():
                    rep = rep.title()
                outword = '<span class="text-replace" role="region" aria-label="alternate term for %s">%s</span> [<a href="#" class="simplifyLookup">%s</a>]' % (tok, rep, tok)
            else:
                outword = tok
            out += outword
        if include_full:
            total_word_count = sum([w['count'] for w in word_info])
        else:
            total_word_count = None
        return {
            'word_count': total_word_count,
            'to_replace': to_replace,
            'word_info': word_info,
            'result': out,
        }

    def tokenize_no_casefold(self, text : str) -> List[str]:
        # This is wf.simple_tokenize but without casefolding.
        # Note, it will not work for languages that don't work with simple_tokenize (eg,
        tokenize_regexp = regex.compile(TOKEN_RE_WITH_PUNCTUATION.pattern + '|\\s+',
                                        regex.V1 | regex.WORD | regex.VERBOSE)
        return tokenize_regexp.findall(text)

    def full_replacement_string(self, hw: str, freq: float):
        """
        Return a long string that shows all possible replacements marked up.
        Only used for debugging in the 'author/simplify' view.
        :param hw: original word
        :param freq: frequency of original word
        :return: HTML description of the possible replacements
        """
        alts = []
        logger.debug(hw)
        for sset in wordnet.synsets(hw):
            if not sset.definition().find('obscene')>=0 and sset.name() not in self.censored_synsets:
                logger.debug('  %s: %s', sset.name(), sset.definition())
                sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
                # logger.debug('  synset %s group=%s', sset, sgroup)
                if sgroup:
                    alts.append(', '.join([ self.mark_up(w, freq) for w in sgroup]))
            else:
                logger.debug('  censored %s: %s', sset.name(), sset.definition())
        return ' / '.join(alts)

    def best_replacement_string(self, hw, orig_freq):
        """
        Determine a replacement for the given word.
        Returns a tuple:  ( replacement string, error string )
        """
        # Query Wordnet for synonym sets that contain the given hw.
        synsets = wordnet.synsets(hw)
        if synsets:
            for sset in synsets:
                # We don't want to suggest even euphemisms that are part of obscene synsets.
                if not sset.definition().find('obscene')>=0 and sset.name() not in self.censored_synsets:
                    # List words (lemmas) other than the original word
                    sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
                    if sgroup:
                        best = self.easiest_word(sgroup)
                        if best and self.compare_frequency(best, orig_freq) > 0:
                            return best.replace('_', ' '), ''
            return None, 'No easier synonyms'
        else:
            return None, 'Not in Wordnet'

    def mark_up(self, word:str, rel_to_freq):
        disp_word = word.replace('_', ' ')
        if self.is_offensive(disp_word):
            return '<span class="offensive">%s</span>' % disp_word
        cmp = self.compare_frequency(word, rel_to_freq)
        if cmp > 0:
            return '<span class="easy">%s</span>' % disp_word
        elif cmp == 0:
            return '<span class="same">%s</span>' % disp_word
        else:
            return '<span class="hard">%s</span>' % disp_word

    def easiest_word(self, list):
        """
        Find the highest-frequency, non-offensive option from the given list of words.
        :param list: list of words
        :return: a single word, or None if all are offensive.
        """
        best_so_far = None
        best_freq = None
        for word in list:
            disp_word = word.replace('_', ' ')
            if not self.is_offensive(disp_word):
                freq = self.get_freq(word)
                if best_freq is None or freq > best_freq:
                    best_so_far = word
                    best_freq = freq
        return best_so_far

    def compare_frequency(self, word: str, rel_to_freq):
        """Return -1, 0, or 1 depending on if word has frequency less than, about the same as, or greater than freq."""
        word_freq = self.get_freq(word)
        if math.fabs(word_freq-rel_to_freq) < .2:
            return 0
        if word_freq > rel_to_freq:
            return 1
        else:
            return -1

    def is_offensive(self, word: str):
        # We currently only have a profanity checker for English.
        if self.lang != 'en':
            return False
        return profanity_check.predict([word])[0] == 1

    def get_freq(self, word: str):
        if word.find('_') >= 0:
            # Wordnet lemmas sometimes are multiple words separated by '_', eg 'get_rid_of'
            # Frequency of this item is taken to be the min frequency of any of the constituent words.
            return zipf_frequency(word.replace('_', ' '), self.lang)
            # parts = regex.split('_', word)
            # freqs = [zipf_frequency(w, self.lang) for w in parts]
            # return min(*freqs)
        else:
            return zipf_frequency(word, self.lang)

    def analyze_words(self, word_list):
        word_info = {}
        for word in word_list:
            if not regex.match('^[a-zA-Z]+$', word):
                continue
            base = base_form(word)
            w = word_info.get(base)
            if w:
                w['count'] += 1
                if word != base and word not in w['alts']:
                    w['alts'].append(word)
            else:
                w = {
                    'hw' : base,
                    'alts' : [],
                    'count' : 1,
                    'freq' : zipf_frequency(base, self.lang)
                }
                if word != base:
                    w['alts'].append(word)
                word_info[base] = w
        return sorted(word_info.values(), key=lambda x: x.get('freq'))

    # Some miscellaneous places where Wordnet has a lot of synonyms listed that can lead to unfortunate replacements
    # even though we have a filter for outright obscenities.  For example 'do it' suggested as synonym for 'love'.
    # These are the synset names from Wordnet that we ban
    # (in addition to anything that has 'obscene' in its definition string).
    censored_synsets = ['asshole.n.01', 'breast.n.02', 'fuck.n.01', 'sexual_love.n.02', 'shit.n.04',
                        'sleep_together.v.01', 'stool.v.04']

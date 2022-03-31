from collections import OrderedDict
from typing import List

import profanity_check
import regex
from nltk.corpus import wordnet
from wordfreq import zipf_frequency
from wordfreq.tokens import TOKEN_RE_WITH_PUNCTUATION

from glossary.util import base_form


class WordnetSimplifier:
    max_frequency_to_simplify = 4.0

    def __init__(self, lang: str) -> None:
        super().__init__()
        self.lang = lang

    def simplify_text(self, text: str, percent: int):
        word_list = self.tokenize_no_casefold(text)
        # Returns frequency info about all distinct tokens, sorted by frequency
        word_info = self.analyze_words(word_list)
        # How many words should we replace?
        to_replace = int(len(word_info) * percent / 100)

        # Now determine appropriate replacements for that many of the most difficult words.
        replacements = {}
        for i in word_info[0:to_replace]:
            hw = i['hw']
            freq = i['freq']
            if freq > self.max_frequency_to_simplify:
                break
            replacement_string, errors = self.best_replacement_string(hw, freq)
            if replacement_string:
                replacements[hw] = replacement_string
                i['replacement'] = replacement_string
                i['full_replacement'] = self.full_replacement_string(hw, freq)
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
                outword = '%s <span class="text-replace">[%s]</span>' % (tok, rep)
            else:
                outword = tok
            out += outword
        return {
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

    def full_replacement_string(self, hw, freq):
        alts = []
        for sset in wordnet.synsets(hw):
            sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
            # logger.debug('  synset %s group=%s', sset, sgroup)
            if sgroup:
                alts.append(', '.join([ self.mark_up(w, freq) for w in sgroup]))
        return ' / '.join(alts)

    def best_replacement_string(self, hw, orig_freq):
        """
        Determine a replacement for the given word.
        Returns a tuple:  ( replacement string, error string )
        """
        alts = []
        # Query Wordnet for synonym sets that contain the given hw.
        synsets = wordnet.synsets(hw)
        if synsets:
            for sset in synsets:
                # List words (lemmas) other than the original word
                sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
                if sgroup:
                    best = self.easiest_word(sgroup)
                    if best and self.is_easier_than(best, orig_freq):
                        alts.append(best.replace('_', ' '))
            # Remove duplicates
            alts = list(OrderedDict.fromkeys(alts))
            if alts:
                altString = ' / '.join(alts)
                return altString, ''
            else:
                return None, 'No easier synonyms'
        else:
            return None, 'Not in Wordnet'

    def mark_up(self, word:str, rel_to_freq):
        disp_word = word.replace('_', ' ')
        if self.is_offensive(disp_word):
            return '<span class="offensive">%s</span>' % disp_word
        if self.is_easier_than(word, rel_to_freq):
            return '<span class="easy">%s</span>' % disp_word
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

    def is_easier_than(self, word: str, rel_to_freq):
        word_freq = self.get_freq(word)
        return word_freq > rel_to_freq

    def is_offensive(self, word: str):
        # We currently only have a profanity checker for English.
        if self.lang != 'en':
            return False
        return profanity_check.predict([word])[0] == 1

    def get_freq(self, word: str):
        if word.find('_') >= 0:
            # Wordnet lemmas sometimes are multiple words separated by '_', eg 'get_rid_of'
            # Frequency of this item is taken to be the min frequency of any of the constituent words.
            parts = regex.split('_', word)
            freqs = [zipf_frequency(w, self.lang) for w in parts]
            return min(*freqs)
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



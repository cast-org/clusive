import logging
import math
from typing import List

import lemminflect
import nltk.tokenize
import profanity_check
import regex
from nltk import TreebankWordTokenizer
from nltk.corpus import wordnet
from unidecode import unidecode
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

    def span_tokenize(self, text: str):
        """
        Run NLTK's recommended tokenizer, returning a list of position spans which locate the tokens in the string.
        NLTK has span_ versions of all its simple tokenizers, but not for this one that does both
        sentence and word tokenization; so we have to implement our own.
        :param text: text string to operate on.
        :return: list of spans.
        """
        stoker = nltk.tokenize.punkt.PunktSentenceTokenizer()
        toker = TreebankWordTokenizer()

        sentence_spans = stoker.span_tokenize(text)

        all_spans = []

        for sent in sentence_spans:
            sent_start = sent[0]
            sent_end = sent[1]
            local_spans = toker.span_tokenize(text[sent_start:sent_end])
            # Need to add the offset to the start of the sentence to these locally-generated spans.
            adjusted_spans = [(s[0]+sent_start, s[1]+sent_start) for s in local_spans]
            all_spans.extend(adjusted_spans)
        return all_spans

    def simplify_text(self, text: str, clusive_user: ClusiveUser = None, percent: int = 10, include_full=False):
        clean_text = unidecode(text)
        spans = self.span_tokenize(clean_text)
        tokens = [clean_text[span[0]:span[1]] for span in spans]
        tagged_list = nltk.pos_tag(tokens)
        # Returns frequency info about all distinct tagged tokens, sorted by frequency
        # Each value is a dict with keys hw, alts, pos, count, freq, known
        word_info = self.analyze_words(tagged_list, clusive_user=clusive_user)
        # logger.debug('Word_info: %s', word_info)
        # How many words should we replace?
        to_replace = math.ceil(len(word_info) * percent / 100)

        # Now determine appropriate replacements for that many of the most difficult words.
        replacements = {}
        for i in word_info:
            hw = i['hw']
            pos = i['pos']
            # Only attempt to find synonyms for simple open-class parts of speech
            if pos not in ['NN', 'VB', 'JJ', 'RB']:
                i['errors'] = 'Ignoring part-of-speech ' + pos
            elif 'known' in i:
                i['errors'] = 'User knows this word'
            else:
                freq = i['freq']
                if include_full:
                    i['full_replacement'] = self.full_replacement_string(hw, pos, freq)
                replacement_string, errors = self.best_replacement_string(hw, pos, freq)
                if replacement_string:
                    replacements[(hw,pos)] = replacement_string
                    i['replacement'] = replacement_string
                else:
                    i['errors'] = errors
                if len(replacements) >= to_replace:
                    break

        # Insert the replacements wherever they occur in the original text.
        for i in range(len(spans)-1, -1, -1):
            tok = tokens[i]
            span = spans[i]
            tagged = tagged_list[i]
            pos = tagged[1]
            base = base_form(tok, return_word_if_not_found=True)
            base_pair = (base, pos[0:2])

            # Replace the word if we have a replacement and it's not being used as a proper noun.
            if base_pair in replacements and pos != 'NNP':
                rep: str
                rep = replacements[base_pair]
                # Try to inflect the word if it's a single word, and we're not looking for the base form
                if not lemminflect.isTagBaseForm(pos) and rep.find(' ') == -1:
                    rep = lemminflect.getInflection(rep, pos)[0]
                if tok[0].isupper():
                    rep = rep.title()
                replacement_text = '<span class="text-alt-pair"><span class="text-alt-src"><a href="#" class="simplifyLookup" role="button">%s</a></span><span class="text-alt-out" aria-label="%s: alternate word">%s</span></span>' % (tok, tok, rep)
                # Alternate markup for showing replacements inline, rather than above the original word
                # outword = '<span class="text-replace" role="region" aria-label="alternate term for %s">%s</span> <span class="text-replace-src">[<a href="#" class="simplifyLookup">%s</a>]</span>' % (tok, rep, tok)
                clean_text = clean_text[:span[0]] + replacement_text + clean_text[span[1]:]
        if include_full:
            total_word_count = sum([w['count'] for w in word_info])
        else:
            total_word_count = None
        return {
            'word_count': total_word_count,
            'to_replace': to_replace,
            'word_info': word_info,
            'result': '<div class="text-alt-vertical">' + clean_text + '</div>',
        }

    def tokenize_no_casefold(self, text : str) -> List[str]:
        # This is wf.simple_tokenize but without casefolding.
        # Note, it will not work for languages that don't work with simple_tokenize (eg,
        tokenize_regexp = regex.compile(TOKEN_RE_WITH_PUNCTUATION.pattern + '|\\s+',
                                        regex.V1 | regex.WORD | regex.VERBOSE)
        return tokenize_regexp.findall(text)

    def penn_pos_to_wordnet_pos(self, penn):
        """
        Convert part-of-speech tag from the Penn standard (used by NLTK taggers) to Wordnet's constants.
        Only handles the 4 basic parts of speech that we attempt to simplify and inflect.
        :return:
        """
        penn_stem = penn[0:2]
        if penn_stem == 'NN':
            return wordnet.NOUN
        if penn_stem == 'VB':
            return wordnet.VERB
        if penn_stem == 'JJ':
            return wordnet.ADJ
        if penn_stem == 'RB':
            return wordnet.ADV
        return None

    def full_replacement_string(self, hw: str, pos: str, freq: float):
        """
        Return a long string that shows all possible replacements marked up.
        Only used for debugging in the 'author/simplify' view.
        :param hw: original word
        :param pos: part-of-speech of original word
        :param freq: frequency of original word
        :return: HTML description of the possible replacements
        """
        alts = []
        logger.debug(hw)
        wordnet_pos = self.penn_pos_to_wordnet_pos(pos)
        # logger.debug('Getting synsets for %s / %s', hw, wordnet_pos)
        for sset in wordnet.synsets(hw, pos=wordnet_pos):
            if not self.is_offensive_synset(sset):
                logger.debug('  %s: %s', sset.name(), sset.definition())
                sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
                # logger.debug('  synset %s group=%s', sset, sgroup)
                if sgroup:
                    alts.append(sset.pos() + ': ' + ', '.join([ self.mark_up(w, freq) for w in sgroup]))
            else:
                logger.debug('  censored %s: %s', sset.name(), sset.definition())
        return ' / '.join(alts)

    def best_replacement_string(self, hw: str, pos: str, orig_freq: float):
        """
        Determine a replacement for the given word.
        Returns a tuple:  ( replacement string, error string )
        """
        synsets = wordnet.synsets(hw, self.penn_pos_to_wordnet_pos(pos))
        if synsets:
            for sset in synsets:
                if not self.is_offensive_synset(sset):
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
        Find the highest-frequency, non-offensive, single-word option from the given list of words.
        :param list: list of words
        :return: a single word, or None if all are offensive.
        """
        best_so_far = None
        best_freq = None
        word: str
        for word in list:
            if not '_' in word and not self.is_offensive(word):
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

    def is_offensive_synset(self, sset):
        # We don't want to use obscene or offensive synsets for generating synonyms.
        # But things like 'offensive military maneuver' are ok.
        definition = sset.definition()
        if definition.startswith('obscene') or definition.startswith('(ethnic slur)') \
                or definition.find('offensive term')>=0 or definition.find('offensive name')>=0 \
                or definition.find('sometimes offensive')>=0 or definition.find('considered offensive')>=0 \
                or definition.find('offensive and insulting')>=0:
            return True
        # Then there are a couple of synsets that don't match the above but we don't want them used.
        return sset.name() in self.censored_synsets

    def is_offensive(self, word: str):
        # We currently only have a profanity checker for English.
        if self.lang != 'en':
            return False
        return profanity_check.predict([word])[0] == 1

    def get_freq(self, word: str):
        return zipf_frequency(word, self.lang)

    def analyze_words(self, tagged_list, clusive_user=None):
        word_info = {}
        for tagged in tagged_list:
            word, pos = tagged
            base_pos = pos[0:2]
            if not regex.match('^[a-zA-Z]+$', word):
                continue
            base = base_form(word, pos=pos)
            base_pair = (base, base_pos)
            w = word_info.get(base_pair)
            if w:
                w['count'] += 1
                if word != base and word not in w['alts']:
                    w['alts'].append(word)
            else:
                w = {
                    'hw' : base,
                    'pos' : base_pos,
                    'alts' : [],
                    'count' : 1,
                    'freq' : zipf_frequency(base, self.lang)
                }
                if word != base:
                    w['alts'].append(word)
                word_info[base_pair] = w

        # Has user indicated that they "know" or "use" any of these words?
        if clusive_user is not None:
            all_words = [t[0] for t in word_info.keys()]
            known_words = WordModel.objects.filter(user=clusive_user, word__in=all_words, rating__gte=2).values('word')
            known_word_list = [val['word'] for val in known_words]
            logger.debug('Known words in simplification: %s', known_word_list)
            for key,val in word_info.items():
                if key[0] in known_word_list:
                    val['known'] = True

        return sorted(word_info.values(), key=lambda x: x.get('freq'))

    # Some miscellaneous places where Wordnet has a lot of synonyms listed that can lead to unfortunate replacements
    # even though we have a filter for outright obscenities.  For example 'do it' suggested as synonym for 'love'.
    # These are the synset names from Wordnet that we ban.
    censored_synsets = ['asshole.n.01', 'breast.n.02', 'fuck.n.01', 'sexual_love.n.02', 'shit.n.04',
                        'sleep_together.v.01', 'stool.v.04']

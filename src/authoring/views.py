import logging
from collections import OrderedDict

import wordfreq as wf
from django.views.generic import FormView, TemplateView
from nltk.corpus import wordnet
from nltk.corpus.reader import Synset
from regex import regex
from textstat import textstat

from authoring.forms import TextInputForm, TextSimplificationForm
from glossary.util import base_form
from library.models import Book

logger = logging.getLogger(__name__)


class SimplifyView(FormView):
    template_name = 'authoring/simplify.html'
    form_class = TextSimplificationForm
    lang = 'en'

    def form_valid(self, form):
        text = form.cleaned_data['text']
        percent = form.cleaned_data['percent']
        # Returns [ { 'hw' , 'alts', 'count', 'freq' }, ... ] sorted by freq
        self.extra_context = {
            'full_text': self.simplify_text(text, percent, include_all=True),
            'best_text': self.simplify_text(text, percent, include_all=False),
        }
        # Don't do normal process of redirecting to success_url.  Just stay on this form page forever.
        return self.render_to_response(self.get_context_data(form=form))

    def simplify_text(self, text:str, percent:int, include_all:bool):
        word_list = wf.tokenize(text, self.lang, include_punctuation=True)
        word_info = analyze_words(word_list, self.lang)
        # TODO: how many words should we replace?  Try 10%
        to_replace = int(len(word_info) * percent / 100)
        replacements = {}
        for i in word_info[0:to_replace]:
            hw = i['hw']

            if include_all:
                replacement_string = self.full_replacement_string(hw, i['freq'])
            else:
                replacement_string = self.best_replacement_string(hw, i['freq'])
            if replacement_string:
                replacements[hw] = replacement_string
            if len(replacements) >= to_replace:
                break
        out = ''
        for tok in word_list:
            # base = base_form(tok)
            # w = word_info.get(base)
            if tok in replacements:
                outword = '<strong>%s</strong> <span class="rep">[%s]</span>' % (tok, replacements[tok])
            else:
                outword = tok
            out += ' ' + outword
        return out

    def full_replacement_string(self, hw, freq):
        alts = []
        for sset in wordnet.synsets(hw):
            sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
            # logger.debug('  synset %s group=%s', sset, sgroup)
            if sgroup:
                alts.append(', '.join([ self.mark_up(w, freq) for w in sgroup]))
        return ' / '.join(alts)

    def best_replacement_string(self, hw, orig_freq):
        alts = []
        for sset in wordnet.synsets(hw):
            sgroup = [lem.name() for lem in sset.lemmas() if lem.name() != hw]
            if sgroup:
                best = self.easiest_word(sgroup)
                if self.is_easier_than(best, orig_freq):
                    alts.append(self.mark_up(best, orig_freq))
        # Remove duplicates
        alts = list(OrderedDict.fromkeys(alts))
        return ' / '.join(alts)

    def mark_up(self, word:str, rel_to_freq):
        disp_word = word.replace('_', ' ')
        if self.is_easier_than(word, rel_to_freq):
            return '<span class="easy">%s</span>' % disp_word
        else:
            return '<span class="hard">%s</span>' % disp_word

    def easiest_word(self, list):
        best_so_far = None
        best_freq = None
        for word in list:
            freq = self.get_freq(word)
            if best_freq is None or freq > best_freq:
                best_so_far = word
                best_freq = freq
        return best_so_far

    def is_easier_than(self, word:str, rel_to_freq):
        word_freq = self.get_freq(word)
        return word_freq > rel_to_freq

    def get_freq(self, word: str):
        if word.find('_') >= 0:
            # Wordnet lemmas sometimes are multiple words separated by '_', eg 'get_rid_of'
            # Frequency of this item is taken to be the min frequency of any of the constituent words.
            parts = regex.split('_', word)
            freqs = [wf.zipf_frequency(w, self.lang) for w in parts]
            return min(*freqs)
        else:
            return wf.zipf_frequency(word, self.lang)


class LevelingView(FormView):
    template_name = 'authoring/level.html'
    form_class = TextInputForm
    lang = 'en'
    words = []
    stats = []

    def form_valid(self, form):
        text = form.cleaned_data['text']
        word_list = wf.tokenize(text, self.lang)
        self.stats = [
            { 'name': 'Flesch-Kincaid grade level',
              'value':  textstat.flesch_kincaid_grade(text),
              'desc': 'Based on avg sentence length and syllables per word.'},
            { 'name': 'Dale-Chall grade level',
              'value': textstat.dale_chall_readability_score_v2(text),
              'desc': 'Based on avg sentence length and percent difficult words.'},
            { 'name': 'Number of words',
              'value': textstat.lexicon_count(text) },
            { 'name': 'Number of sentences',
              'value': textstat.sentence_count(text) },
            { 'name': 'Average sentence length',
              'value': textstat.avg_sentence_length(text) },
            { 'name': 'Average syllables per word',
              'value': textstat.avg_syllables_per_word(text) },
            { 'name': 'Difficult words',
              'value': "%d (%d%%): %s" % (textstat.difficult_words(text),
                                          100*textstat.difficult_words(text)/textstat.lexicon_count(text),
                                          ', '.join(textstat.difficult_words_list(text))) },
        ]
        self.words = analyze_words(word_list, self.lang)
        # Don't do normal process of redirecting to success_url.  Just stay on this form page forever.
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        logger.debug('invalid')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['words'] = self.words
        data['stats'] = self.stats
        return data


def analyze_words(word_list, lang):
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
                'freq' : wf.zipf_frequency(base, lang)
            }
            if word != base:
                w['alts'].append(word)
            word_info[base] = w
    return sorted(word_info.values(), key=lambda x: x.get('freq'))


class SynonymsView(TemplateView):
    template_name = 'authoring/partial/synonyms.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        synsets = wordnet.synsets(kwargs['word'])
        context['synonyms'] = [ self.describe_synset(synset) for synset in synsets ]
        return context

    def describe_synset(synset : Synset):
        return "(%s) %s (%s)" % (synset.pos(), ', '.join([str(lemma.name()) for lemma in synset.lemmas()]), synset.definition())


class BookInfoView(TemplateView):
    template_name = 'authoring/book_info.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = Book.objects.filter(owner=None)
        return context

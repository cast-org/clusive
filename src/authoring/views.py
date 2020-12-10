import logging

from django.views.generic import FormView, TemplateView
import wordfreq as wf
from nltk.corpus import wordnet
from nltk.corpus.reader import Synset
from textstat import textstat

from authoring.forms import TextInputForm
from glossary.util import base_form
from library.models import Book

logger = logging.getLogger(__name__)


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
        word_info = {}
        for word in word_list:
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
                    'freq' : wf.zipf_frequency(base, self.lang)
                }
                if word != base:
                    w['alts'].append(word)
                word_info[base] = w
        self.words = sorted(word_info.values(), key=lambda x: x.get('freq'))
        logger.debug('words: %s', self.words)
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

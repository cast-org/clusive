import logging

from django.views.generic import FormView
import wordfreq as wf
from textstat import textstat

from authoring.forms import TextInputForm
from glossary.util import base_form

logger = logging.getLogger(__name__)


class LevelingView(FormView):
    template_name = 'authoring/level.html'
    form_class = TextInputForm
    lang = 'en'
    word_count = 0
    words = []
    stats = {}

    def form_valid(self, form):
        text = form.cleaned_data['text']
        word_list = wf.tokenize(text, self.lang)
        self.word_count = len(word_list)
        self.stats = [
            { 'name': 'Flesch-Kincaid grade level',
              'value':  textstat.flesch_kincaid_grade(text),
              'desc': 'Based on avg sentence length and syllables per word.'},
            { 'name': 'Dale-Chall grade level',
              'value': textstat.dale_chall_readability_score_v2(text),
              'desc': 'Based on avg sentence length and percent difficult words.'},
            { 'name': 'Number of sentences',
              'value': textstat.sentence_count(text) },
            { 'name': 'Average sentence length',
              'value': textstat.avg_sentence_length(text) },
            { 'name': 'Average syllables per word',
              'value': textstat.avg_syllables_per_word(text) },
            { 'name': 'Difficult words',
              'value': "%d (%d%%): %s" % (textstat.difficult_words(text),
                                          100*textstat.difficult_words(text)/textstat.lexicon_count(text),
                                          textstat.difficult_words_list(text)) },
        ]
        word_info = {}
        for word in word_list:
            base = base_form(word)
            w = word_info.get(base)
            if w:
                w['count'] += 1
                if word != base and word not in w['alts']:
                    w['forms'].append(word)
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
        data['word_count'] = self.word_count
        data['words'] = self.words
        data['stats'] = self.stats
        return data



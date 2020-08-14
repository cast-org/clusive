import logging

from django.views.generic import FormView
import wordfreq as wf

from authoring.forms import TextInputForm

logger = logging.getLogger(__name__)


class LevelingView(FormView):
    template_name = 'authoring/level.html'
    form_class = TextInputForm
    lang = 'en'
    word_count = 0
    words = []

    def form_valid(self, form):
        text = form.cleaned_data['text']
        word_list = wf.tokenize(text, self.lang)
        self.word_count = len(word_list)
        word_info = {}
        for word in word_list:
            w = word_info.get(word)
            if w:
                w['count'] += 1
            else:
                w = {
                    'word' : word,
                    'count' : 1,
                    'freq' : wf.zipf_frequency(word, self.lang)
                }
                word_info[word] = w
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
        return data



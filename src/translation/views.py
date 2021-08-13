import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from eventlog.signals import translation_action

logger = logging.getLogger(__name__)


class TranslateTextView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        lang = request.POST.get('language')
        logger.debug("Received a translation request: %s" % text)

        translation_action.send(sender=TranslateTextView.__class__,
                                request=request,
                                language=lang,
                                text=text)
        if lang == 'default':
            result = 'What language do you want to translate to? Choose one in Settings under Reading Tools'
        else:
            # TODO
            result = '(This would be translated to %s)' % lang

        return JsonResponse({'result': result})

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from google.api_core.exceptions import Forbidden

from eventlog.signals import translation_action
from library.models import Book
from roster.models import TransformTool
from translation.util import TranslateApiManager

logger = logging.getLogger(__name__)


class TranslateTextView(LoginRequiredMixin, View):

    def post(self, request):
        text = request.POST.get('text')
        lang = request.POST.get('language')
        book_id = request.POST.get('book_id')
        book = Book.objects.get(pk=book_id) if book_id else None
        clusive_user = request.clusive_user
        error = None

        clusive_user.set_simplification_tool(TransformTool.TRANSLATE)

        translation_action.send(sender=TranslateTextView.__class__,
                                request=request,
                                language=lang,
                                text=text,
                                book=book)
        if not lang or lang == 'default':
            error = 'What language do you want to translate to? Choose one in Settings under Reading Tools'
        else:
            client = TranslateApiManager.get_google_translate_client()
            if client:
                try:
                    # TODO: set source language?  Currently lets Google auto-detect.
                    answer = client.translate(text, target_language=lang)
                    result = answer['translatedText']
                except Forbidden as e:
                    logger.warning('Translation failed, reason={}', e)
                    error = 'Translation failed'
            else:
                error = 'Sorry, translation feature is unavailable'

        if error:
            return JsonResponse({'result': error,
                                 'lang': 'en',
                                 'direction': 'ltr'})
        else:
            return JsonResponse({'result': result,
                                 'lang': lang,
                                 'direction': TranslateApiManager.direction_for_language(lang)})


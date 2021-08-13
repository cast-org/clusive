import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from google.api_core.exceptions import Forbidden
from google.cloud import translate_v2 as translate

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
            client = GoogleApiManager.get_google_translate_client()
            if client:
                try:
                    # TODO: set source language?  Currently lets Google auto-detect.
                    answer = client.translate(text, target_language=lang)
                    result = answer['translatedText']
                except Forbidden as e:
                    logger.warning('Translation failed, reason={}', e)
                    result = 'Translation failed'
            else:
                result = 'Sorry, translation feature is unavailable'

        return JsonResponse({'result': result})


class GoogleApiManager:
    translate_client = None

    @classmethod
    def get_google_translate_client(cls):
        """Create a client, and keep it around for later re-use."""
        if not cls.translate_client:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                cls.translate_client = translate.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
                logger.debug('Initialized new google translate client')
        return cls.translate_client

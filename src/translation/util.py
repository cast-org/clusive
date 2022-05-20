import logging

from django.conf import settings
from google.cloud import translate_v2 as translate

logger = logging.getLogger(__name__)


def translation_is_configured():
    return settings.GOOGLE_APPLICATION_CREDENTIALS is not None


class TranslateApiManager:
    translate_client = None
    translate_language_list = None

    # Top 30 languages among EL in US k-12 schools, according to
    # https://nces.ed.gov/programs/digest/d20/tables/dt20_204.27.asp
    # As of 2021 Google Translate does not support Karen languages (kar) or Marshallese (mh), but should find the rest.
    top_languages = ['es', 'ar', 'zh-CN', 'so', 'ru', 'pt', 'ht', 'hmn', 'ko', 'ur', 'fr', 'tg', 'sw', 'ja',
                     'bn', 'hi', 'pa', 'my', 'fa', 'ne', 'kar', 'am', 'te', 'gu', 'km', 'uk', 'pl', 'mh']

    # Languages that are written right-to-left, according to
    # https://lingohub.com/academy/best-practices/rtl-language-list
    rtl_languages = ['ar', 'arc', 'dv', 'fa', 'ha', 'iw', 'khw', 'ks', 'ku', 'ps', 'ur', 'yi']

    @classmethod
    def get_translate_language_list(cls):
        if not cls.translate_language_list:
            client = cls.get_google_translate_client()
            if client:
                cls.translate_language_list = []
                for lang in client.get_languages():
                    if lang['language'] in cls.top_languages:
                        cls.translate_language_list.append(lang)
                cls.translate_language_list.sort(key=lambda l: l['name'])
        return cls.translate_language_list

    @classmethod
    def get_google_translate_client(cls):
        """Create a client, and keep it around for later re-use."""
        if not cls.translate_client:
            if settings.GOOGLE_APPLICATION_CREDENTIALS:
                cls.translate_client = translate.Client.from_service_account_json(settings.GOOGLE_APPLICATION_CREDENTIALS)
                logger.debug('Initialized new google translate client')
        return cls.translate_client

    @classmethod
    def direction_for_language(cls, lang):
        if lang in cls.rtl_languages:
            return 'rtl'
        return 'ltr'

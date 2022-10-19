import logging
import math
from typing import Union

import nltk
from TheNounProjectAPI import API
from TheNounProjectAPI.exceptions import NotFound
from TheNounProjectAPI.models import UsageModel, EnterpriseModel
from django.conf import settings
from unidecode import unidecode

from glossary.util import base_form
from simplification.models import PictureUsage, PictureSource
from simplification.util import WordnetSimplifier

logger = logging.getLogger(__name__)


# The Noun Project api is documented here: http://api.thenounproject.com/

def nounproject_is_configured() -> bool:
    """
    Check whether an API key for The Noun Project has been provided.
    If not, 'show images' feature should not be shown.
    :return: true if we have an API key configured.
    """
    return settings.NOUNPROJECT_API_KEY is not None and settings.NOUNPROJECT_API_SECRET is not None


class NounProjectManager:

    api = API(key=settings.NOUNPROJECT_API_KEY, secret=settings.NOUNPROJECT_API_SECRET)
    pro_account = False
    words_without_icons = set()

    def check_usage(self):
        # Make sure we are under our allowed usage, so we don't incur overage fees.
        # Sets pro_account flag if the limits are in that range - means we can also get non-public-domain icons
        usage: UsageModel
        usage = self.api.get_usage()
        if usage.limits.monthly > 5000:
            self.pro_account = True
        logger.debug('Noun Project API usage. Hourly %s/%s, Daily %s/%s, Monthly %s/%s',
                     usage.usage.hourly, usage.limits.hourly,
                     usage.usage.daily, usage.limits.daily,
                     usage.usage.monthly, usage.limits.monthly)
        ok = True
        if usage.limits.hourly and usage.usage.hourly >= usage.limits.hourly:
            logger.warning('Noun Project API hourly usage is too high')
            ok = False
        if usage.limits.daily and usage.usage.daily >= usage.limits.daily:
            logger.warning('Noun Project API daily usage is too high')
            ok = False
        if usage.limits.monthly and usage.usage.monthly >= usage.limits.monthly:
            logger.warning('Noun Project API monthly usage is too high')
            ok = False
        return ok

    def report_usage(self, icons: Union[list, set, str, int]):
        result: EnterpriseModel
        result = self.api.report_usage(test=False, icons=icons)
        logger.debug('Report usage result: %s', result)
        return result.result == 'success'

    def get_icon(self, word: str):
        """
        Tries to get an icon from The Noun Project for the given word.
        :param word: word to look up
        :return: (icon_url, icon_description)  or (None, None) if one can't be found or an error occurs while trying.
        """

        if word in NounProjectManager.words_without_icons:
            logger.debug('Skipping lookup for word %s, it is known to not have an icon', word)
            PictureUsage.log_missing(source=PictureSource.NOUN_PROJECT, word=word)
            return (None, None)
        try:
            pub_domain_only = not self.pro_account
            icons = self.api.get_icons_by_term(word, public_domain_only=pub_domain_only, limit=1)
            if len(icons) > 0:
                icon = icons[0]
                logger.debug('Retrieved icon: %s -> %s', word, icon.term)
                PictureUsage.log_usage(source=PictureSource.NOUN_PROJECT, word=word, icon_id=icon.id)
                return (icon.icon_url, icon.term)
            else:
                logger.debug('No icons returned for word %s', word)
        except NotFound:
            logger.debug('No icon found for term %s', word)
            PictureUsage.log_missing(source=PictureSource.NOUN_PROJECT, word=word)
            NounProjectManager.words_without_icons.add(word)
        except Exception as e:
            logger.warning('API Error for %s: [%s] %s', word, e.__class__, e)
        return (None, None)

    def add_pictures(self, text, clusive_user=None, percent=15):
        if not nounproject_is_configured():
            return text

        if not self.check_usage():
            return text

        wns = WordnetSimplifier('en')
        clean_text = unidecode(text)
        spans = wns.span_tokenize(clean_text)
        tokens = [clean_text[span[0]:span[1]] for span in spans]
        tagged_list = nltk.pos_tag(tokens)
        word_info = wns.analyze_words(tagged_list, clusive_user=clusive_user)
        to_replace = math.ceil(len(word_info) * percent / 100)

        # Find some pictures to use
        pictures = {}
        for i in word_info:
            hw = i['hw']
            if not 'known' in i:
                url, desc = self.get_icon(hw)
                if url:
                    pictures[hw] = (url, desc)
                    to_replace -= 1
                    if to_replace <= 0:
                        break

        # Insert them into the text
        for i in range(len(spans)-1, -1, -1):
            tok = tokens[i]
            span = spans[i]
            tagged = tagged_list[i]
            base = base_form(tok, return_word_if_not_found=True)

            if base in pictures:
                url, desc = pictures[base]
                rep = '<span class="text-picture-pair"><span class="text-picture-term">%s</span> ' \
                      '<img src="%s" class="text-picture-img" alt="%s"></span>' \
                      % (tok, url, desc)
                clean_text = clean_text[:span[0]] + rep + clean_text[span[1]:]

        return clean_text

import logging
import math

import requests
from django.conf import settings

from glossary.util import base_form
from simplification.util import WordnetSimplifier

logger = logging.getLogger(__name__)


# The Flaticon api is documented here: https://api.flaticon.com

def flaticon_is_configured() -> bool:
    """
    Check whether an API key for flaticon has been provided.
    If not, 'show images' feature should not be shown.
    :return: true if we have an API key configured.
    """
    return settings.FLATICON_API_KEY is not None


class FlaticonManager:

    token = None
    api_base = 'https://api.flaticon.com/v3'
    api_key = settings.FLATICON_API_KEY

    def get_token(self, session: requests.Session):
        """
        Fetch a token from the API if we don't already have one.
        :return: existing or new token, or None if a token can't be obtained.
        """
        if self.api_key is None:
            return None
        if self.token is None:
            try:
                resp = session.post(url=self.api_base+'/app/authentication', timeout=3, params={
                    'apikey': self.api_key,
                })
                if resp.status_code == requests.codes.ok:
                    if resp.json():
                        self.token = 'Bearer ' + resp.json()['data']['token']
                else:
                    logger.warning('Error status from Flaticon: %s', resp.status_code)
            except (KeyError, ValueError) as error:
                logger.error('Error while requesting Flaticon token', error)
        return self.token

    def get_session(self):
        """
        Create and return a session object.
        Multiple icon requests should be done through one HTTP session, otherwise it's quite slow.
        """
        return requests.Session()

    def get_icon(self, session: requests.Session, word: str):
        """
        Tries to get an icon from Flaticons for the given word.
        :param session: a session is required; get one by calling get_session().
        :param word: word to look up
        :return: (icon_url, icon_description)  or (None, None) if one can't be found or an error occurs while trying.
        """
        token = self.get_token(session)
        if token is None:
            return (None, None)
        resp = None
        try:
            params = {
                'q': word,
                'styleShape': 'outline',
                'styleColor': 'black',
                'limit': '1',
            }
            headers = {
                'Authorization': token,
            }
            resp = session.get(url=self.api_base+'/search/icons/priority', timeout=3, headers=headers, params=params)
            if resp.status_code == requests.codes.ok:
                json = resp.json()
                icons = json.get('data', [])
                if icons is not None and len(icons) > 0:
                    url = icons[0].get('images', {}).get('64')
                    desc = icons[0].get('description')
                    if url is not None and desc is not None:
                        return (url, desc)
                    else:
                        logger.warning('Flaticon response did not include expected fields: %s', json)
                        return (None, None)
                else:
                    return (None, None)
        except ValueError:
            logger.warning('No icon for Flaticon returned', resp)
            return (None, None)

    def add_pictures(self, text, clusive_user=None, percent=15):
        if not flaticon_is_configured():
            return text
        session = self.get_session()
        wns = WordnetSimplifier('en')
        word_list = wns.tokenize_no_casefold(text)
        word_info = wns.analyze_words(word_list, clusive_user=clusive_user)
        to_replace = math.ceil(len(word_info) * percent / 100)

        # Find some pictures to use
        pictures = {}
        for i in word_info:
            hw = i['hw']
            if not 'known' in i:
                url, desc = self.get_icon(session, hw)
                if url:
                    logger.debug('Found icon for %s', hw)
                    pictures[hw] = (url, desc)
                    to_replace -= 1
                    if to_replace <= 0:
                        break
        logger.debug('Done looking for icons, to_replace=%d', to_replace)

        # Insert them into the text
        out = ''
        for tok in word_list:
            base = base_form(tok, return_word_if_not_found=True)
            if base in pictures:
                url, desc = pictures[base]
                logger.debug('Found picture for %s (%s)', tok, base)
                rep = '<span class="text-picture-pair"><span class="text-picture-term">%s</span> ' \
                      '<img src="%s" class="text-picture-img" alt="%s"></span>' \
                      % (tok, url, desc)
            else:
                logger.debug('No picture for %s (%s)', tok, base)
                rep = tok
            out += rep
        logger.debug('output: %s', out)
        return out

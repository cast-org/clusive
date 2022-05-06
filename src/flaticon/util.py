import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

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

    def get_token(self):
        """
        Fetch a token from the API if we don't already have one.
        :return: existing or new token, or None if a token can't be obtained.
        """
        if self.api_key is None:
            return None
        token_resp = None
        if self.token is None:
            try:
                token_resp = requests.post(url=self.api_base+'/app/authentication', params={
                    'apikey': self.api_key,
                })
                if token_resp.json():
                    self.token = 'Bearer ' + token_resp.json()['data']['token']
            except ValueError:
                logger.error('No token for Flaticon returned', token_resp)
        return self.token

    def get_icon(self, word: str):
        token = self.get_token()
        if token is None:
            return None
        resp = None
        try:
            params = {
                'q': word,
                'styleShape' : 'outline',
                'styleColor': 'black',
                'limit': '1',
            }
            headers = {
                'Authorization': token,
            }
            resp = requests.get(url=self.api_base+'/search/icons/priority', headers=headers, params=params).json()
            if  resp['data']:
                icon = resp['data'][0]
                logger.debug('icon for %s is %s', word, icon)
                return icon
            else:
                return None
        except ValueError:
            logger.warning('No icon for Flaticon returned', resp)
            return None

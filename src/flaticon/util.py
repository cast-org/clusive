import logging

import requests
from django.conf import settings

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

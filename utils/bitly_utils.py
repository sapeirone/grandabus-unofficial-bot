import logging

import aiohttp

logger = logging.getLogger(__name__)

BITLY_ENDPOINT = 'https://api-ssl.bitly.com/v4/shorten'


async def shorten(url: str, access_token: str, session: aiohttp.ClientSession):
    """
    Shorten url using bit.ly service
    :param url: url to be shortened
    :param access_token: Bit.ly access token
    :param session: (optional) aiohttp client session
    :return: shortened url if available, None otherwise
    """

    if not session:
        raise ValueError('aiohttp session missing')

    payload = {'long_url': url}
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    async with session.post(BITLY_ENDPOINT, json=payload, headers=headers) as response:
        if response.status in (200, 201):
            json = await response.json()
            return json['link']
        else:
            raise IOError(f'Cannot shorten {url}. Response from Bit.ly was {await response.text()}')

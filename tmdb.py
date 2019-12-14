import logging
import urllib

import requests

URL_CONTEXT = '/3/search/movie?api_key=API_KEY&include_adult=false&query=QUERY_STRING'
DNS_NAME = 'api.themoviedb.org'
PROTOCOL = 'https://'
BASE_URL = PROTOCOL + DNS_NAME + URL_CONTEXT


def is_movie(name, api_key):
    """Look up the name of the media in question in The Movie DB to determine if this media
       is a movie or not."""

    # Only send query if the media name and api key are provided
    if name and api_key:

        url = BASE_URL.replace('QUERY_STRING', urllib.parse.quote(name))

        logging.debug('Sending query to [%s] TMDB with URL: [%s]', DNS_NAME, url)

        url = url.replace('API_KEY', api_key)

        r = requests.get(url)

        logging.debug('TMDB GET status: [%s] with reason: [%s]',
                      r.status_code, r.reason)

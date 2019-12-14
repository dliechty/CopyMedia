import json
import logging
import urllib

import requests

import logger

URL_CONTEXT = '/3/search/movie?api_key=API_KEY&include_adult=false&query=QUERY_STRING'
DNS_NAME = 'api.themoviedb.org'
PROTOCOL = 'https://'
BASE_URL = PROTOCOL + DNS_NAME + URL_CONTEXT


def clean_name(name):
    """Used to clean up the name of the media so that it is suitable to send in an API query"""

    logging.log(logger.TRACE, 'Raw name: [%s]', name)

    # TODO: clean up name

    logging.log(logger.TRACE, 'Cleaned name: [%s]', name)
    return name


def is_movie(name, api_key):
    """Look up the name of the media in question in The Movie DB to determine if this media
       is a movie or not."""

    # Only send query if the media name and api key are provided
    if name and api_key:

        logging.debug('Performing query to the movie DB with media name [%s]', name)

        c_name = clean_name(name)
        enc_name = urllib.parse.quote(clean_name(c_name))
        logging.log(logger.TRACE, 'URL encoded name: [%s]', enc_name)
        url = BASE_URL.replace('QUERY_STRING', enc_name)

        logging.debug('Sending query to [%s] TMDB with URL: [%s]', DNS_NAME, url)

        url = url.replace('API_KEY', api_key)

        r = requests.get(url)

        logging.debug('TMDB GET status: [%s] with reason: [%s]',
                      r.status_code, r.reason)
        logging.log(logger.TRACE, 'Results: [%s]', r.text)

        if r.text:
            result = json.loads(r.text)
            num_results = result['total_results']
            logging.debug('Number of results found: [%d]', num_results)
            if result['total_results'] > 0:
                return True

        return False

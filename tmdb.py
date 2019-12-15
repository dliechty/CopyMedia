import json
import logging
import urllib
import PTN

import requests

import logger

URL_CONTEXT = '/3/search/movie?api_key=API_KEY&include_adult=false&query=QUERY_STRING'
YEAR_BASE = '&year='
DNS_NAME = 'api.themoviedb.org'
PROTOCOL = 'https://'
BASE_URL = PROTOCOL + DNS_NAME + URL_CONTEXT


def clean_name(name):
    """Used to parse the name of the media so that the title and year can be sent in an API query"""

    logging.log(logger.TRACE, 'Raw name: [%s]', name)

    meta = PTN.parse(name)
    logging.log(logger.TRACE, 'Parsed meta-data: [%s]', meta)

    logging.debug('Parsed title: [%s]', meta['title'])
    return meta


def is_movie(name, api_key):
    """Look up the name of the media in question in The Movie DB to determine if this media
       is a movie or not."""

    if api_key is None:
        logging.warning("Can't query tmdb because no api key was specified.")
        return False

    if name is None:
        logging.warning("Can't query because file name was not provided.")

    # Only send query if the media name and api key are provided
    if name:

        logging.debug('Performing query to the movie DB with media name [%s]', name)

        meta = clean_name(name)
        enc_name = urllib.parse.quote(meta['title'])
        logging.log(logger.TRACE, 'URL encoded name: [%s]', enc_name)
        url = BASE_URL.replace('QUERY_STRING', enc_name)

        if 'year' in meta:
            url = url + YEAR_BASE + str(meta['year'])
        else:
            logging.debug('No year found in file name. Skipping search.')
            return False

        if 'season' in meta and 'episode' in meta:
            logging.debug('meta-data indicates season [%s] and episode [%s] in name. '
                          'Movies can\'t have seasons and episodes, so skipping search',
                          meta['season'], meta['episode'])
            return False

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

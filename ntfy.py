import logging
import requests


def send_notification(url, token, message):
    """POST a plain-text message to an ntfy channel with Bearer auth.

    Returns the Response on success, None if an exception occurs (logged, not raised)."""
    try:
        r = requests.post(url, data=message, headers={'Authorization': 'Bearer ' + token})
        return r
    except Exception:
        logging.exception('Failed to send ntfy notification to [%s]', url)

import requests
import logging


def send_notification(matches, trigger_url):
    """Send IFTTT notification to phone whenever the script fires with the names
        of the new episodes"""

    # Only send notification if there is at least one matching file.
    if matches and trigger_url:
        # Get series name for each matching file and concatenate
        # into a string separated by ' and '
        names = [config['name'] for file, config in matches]
        name_string = ' and '.join(names)

        logging.debug('Sending notification with name string: [%s] to IFTTT',
                      name_string)

        r = requests.post(trigger_url, data={'value1': name_string})
        logging.debug('IFTTT POST status: [%s] with reason: [%s]',
                      r.status_code, r.reason)
        return r

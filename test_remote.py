#!/usr/bin/python3
import os
import unittest
from unittest.mock import MagicMock, patch

import logger
import ntfy

logger.config()

NTFY_CONTEXT_VAR = 'NTFY_CONTEXT'


class TestNtfy(unittest.TestCase):

    def test_send_notification(self):
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = ntfy.send_notification('https://ntfy.sh/topic', 'mytoken', 'test message')

            mock_post.assert_called_once_with(
                'https://ntfy.sh/topic',
                data='test message',
                headers={'Authorization': 'Bearer mytoken'}
            )
            self.assertEqual(result.status_code, 200)

    def test_send_notification_live(self):
        """Live test — set NTFY_CONTEXT=https://ntfy.sh/<topic>|<token> to run."""
        ntfy_context = os.getenv(NTFY_CONTEXT_VAR)
        if ntfy_context is None:
            self.skipTest('Set NTFY_CONTEXT=https://ntfy.sh/<topic>|<token> to run this test')
        url, token = ntfy_context.split('|', 1)
        r = ntfy.send_notification(url, token, 'CopyMedia test notification')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()

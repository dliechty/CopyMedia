#!/usr/bin/python3
import os
import unittest
from unittest.mock import MagicMock, patch

import logger
import ntfy
import shutil
import tempfile
from remote import is_remote, rsync

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


class TestRemote(unittest.TestCase):

    def test_is_remote_true(self):
        self.assertTrue(is_remote('david@nas:/volume1/plex'))
        self.assertTrue(is_remote('user@192.168.1.1:/path/to/dir'))
        self.assertTrue(is_remote('user@host:relative/path'))

    def test_is_remote_false(self):
        self.assertFalse(is_remote('/absolute/local/path'))
        self.assertFalse(is_remote('relative/path'))
        self.assertFalse(is_remote('path/with@symbol/in/dir/filename.mkv'))

    def test_rsync_success_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'episode.mkv')
            open(src, 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = rsync(src, 'user@nas:/series/ShowName/episode.mkv')

            self.assertTrue(result)
            self.assertFalse(os.path.exists(src))

    def test_rsync_failure_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'episode.mkv')
            open(src, 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=11)
                result = rsync(src, 'user@nas:/series/ShowName/episode.mkv')

            self.assertFalse(result)
            self.assertTrue(os.path.exists(src))

    def test_rsync_success_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'Toy_Story_4.2019')
            os.makedirs(src)
            open(os.path.join(src, 'movie.mkv'), 'w').close()

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = rsync(src, 'user@nas:/movies/Toy_Story_4.2019')
                cmd = mock_run.call_args[0][0]

            self.assertTrue(result)
            self.assertFalse(os.path.exists(src))
            # Trailing slash must be added to both src and dest for directory rsync
            self.assertTrue(cmd[3].endswith('/'))
            self.assertTrue(cmd[4].endswith('/'))

    def test_rsync_failure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, 'Toy_Story_4.2019')
            os.makedirs(src)

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=11)
                result = rsync(src, 'user@nas:/movies/Toy_Story_4.2019')

            self.assertFalse(result)
            self.assertTrue(os.path.exists(src))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/python3

import os
import unittest

from copy_files import CopyMedia
from copy_files import IFTTT_URL_BASE
from exceptions import ConfigurationError

TEST_CONFIG = r'./test_CopyMedia.json'
IFTTT_CONTEXT_VAR = 'IFTTT_CONTEXT'


class TestCopyMedia(unittest.TestCase):

    @unittest.skip("Don't need to send notification every time.")
    def test_notifications(self):

        ifttt_context = os.getenv(IFTTT_CONTEXT_VAR)
        if ifttt_context is None:
            self.skipTest("Can't find IFTTT trigger context and API key. Add"
                          "property to environment variables: " + IFTTT_CONTEXT_VAR)

        c = CopyMedia(None, None, None, None, None, None)
        r = c.send_notification([('notafile', {'name': 'test series'})], IFTTT_URL_BASE + ifttt_context)

        self.assertEqual(r.status_code, 200)

    def test_process_configs(self):
        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, None, None, None)

        blah_path = '/home/test/blah'
        blarg_path = '/remote/test/blarg'
        test_file = '/home/test/dir/file'

        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, blah_path, None, None)

        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, None, blarg_path, None)

        c = CopyMedia(None, TEST_CONFIG, None, None, blarg_path, test_file)

        self.assertEqual(3, len(c.configs['series']))
        self.assertEqual(blarg_path, c.destdir)

        self.assertIsNone(c.scandir)

        c = CopyMedia(None, TEST_CONFIG, None, blah_path, blarg_path, None)

        self.assertEqual(blah_path, c.scandir)

    def test_match_files(self):
        c = CopyMedia(None, None, None, None, None, None)

        files = ['testFile1', 'testFile2']

        matches = c.match_files(files, c.series)
        # should be empty
        self.assertFalse(matches)

        files = ['[HorribleSubs] GATE - 24 [1080p].mkv', '[HorribleSubs] Kimetsu no Yaiba - 26 [1080p].mkv']
        matches = c.match_files(files, c.series)
        self.assertEqual(len(matches), 2)

    def test_validate_series(self):

        # Needs to have a name- regex by itself isn't enough
        series = [{'regex': '(.*)(Test Series)( - )(\\d{1,})(.*)'}]
        with self.assertRaises(KeyError):
            CopyMedia.validate_series(series)

        # Needs to have a regex- name by itself isn't enough
        series = [{'name': 'Test Series'}]
        with self.assertRaises(KeyError):
            CopyMedia.validate_series(series)

        # Once we add a regex to a name, then it should work.
        series[0]['regex'] = '(.*)(Test Series)( - )(\\d{1,})(.*)'
        self.assertTrue(CopyMedia.validate_series(series))

        # Add another entry. Should still be valid
        series.append({'name': 'Test Series S2', 'regex': '(.*)(Test Series S2)( - )(\\d{1,})(.*)'})
        self.assertTrue(CopyMedia.validate_series(series))


if __name__ == '__main__':
    unittest.main()

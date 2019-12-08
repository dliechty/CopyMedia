#!/usr/bin/python3

import unittest
import configparser
from copy_files import CopyMedia
from copy_files import IFTTT_URL_BASE

CONFIG_PATH = r'./test_config.txt'
NOTIFICATION_SECTION = 'notification-config'


class TestCopyMedia(unittest.TestCase):

    @unittest.skip("Don't need to send notification every time.")
    def test_notifications(self):

        cparser = configparser.RawConfigParser()
        try:
            cparser.read(CONFIG_PATH)
            ifttt_context = cparser.get(NOTIFICATION_SECTION, 'ifttt_context')
        except configparser.NoSectionError as err:
            self.skipTest("Can't find section "
                          + NOTIFICATION_SECTION
                          + " in config file. Add to config file: "
                          + CONFIG_PATH)
        except configparser.NoOptionError as err:
            self.skipTest("Can't find IFTTT trigger context and API key. Add"
                          "to config file: " + CONFIG_PATH)

        c = CopyMedia(None, None, None, None, None, None)
        r = c.send_notification([('notafile', {'name': 'test series'})], IFTTT_URL_BASE + ifttt_context)

        self.assertEqual(r.status_code, 200)

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

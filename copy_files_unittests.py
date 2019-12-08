#!/usr/bin/python3

import unittest
import configparser
from copy_files import CopyMedia
from copy_files import IFTTT_URL_BASE

CONFIG_PATH = r'./test_config.txt'
NOTIFICATION_SECTION = 'notification-config'


class TestCopyMedia(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()

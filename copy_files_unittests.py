#!/usr/bin/python3

import unittest
import configparser
from copy_files import CopyMedia
from copy_files import IFTTT_URL_BASE

CONFIG_PATH = r'./test_config.txt'


class TestCopyMedia(unittest.TestCase):

    def test_notifications(self):

        cparser = configparser.RawConfigParser()
        cparser.read(CONFIG_PATH)

        ifttt_context = cparser.get('notification-config', 'ifttt_context')

        c = CopyMedia(None, None, None, None, None, None)
        c.send_notification([('notafile', {'name': 'test series'})], IFTTT_URL_BASE + ifttt_context)


if __name__ == '__main__':
    unittest.main()

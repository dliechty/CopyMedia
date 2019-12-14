#!/usr/bin/python3

import os
import unittest

import ifttt
import logger
import tmdb
from copy_files import CopyMedia
from copy_files import IFTTT_URL_BASE
from exceptions import ConfigurationError

TEST_CONFIG = r'./test_CopyMedia.json'
IFTTT_CONTEXT_VAR = 'IFTTT_CONTEXT'
TMDB_CONTEXT_VAR = 'TMDB_CONTEXT'

logger.config()


class TestCopyMedia(unittest.TestCase):

    def test_notifications(self):

        ifttt_context = os.getenv(IFTTT_CONTEXT_VAR)
        if ifttt_context is None:
            self.skipTest("Can't find IFTTT trigger context and API key. Add"
                          "property to environment variables: " + IFTTT_CONTEXT_VAR)

        r = ifttt.send_notification([('notafile', {'name': 'test series'})], IFTTT_URL_BASE + ifttt_context)

        self.assertEqual(r.status_code, 200)

    def test_is_movie(self):

        tmdb_key = os.getenv(TMDB_CONTEXT_VAR)
        if tmdb_key is None:
            self.skipTest("Can't find TMDB API key. Add"
                          "property to environment variables: " + TMDB_CONTEXT_VAR)

        # these are movies
        self.assertTrue(tmdb.is_movie('22 Jump Street 2014 1080p BluRay x265 HEVC 10bit AAC 5.1-LordVako',
                                      tmdb_key))
        self.assertTrue(tmdb.is_movie('Batman.vs.Superman.Dawn.of.Justice.2016', tmdb_key))
        self.assertTrue(tmdb.is_movie('Brave.2012.1080p.BluRay.x264.AC3-HDChina', tmdb_key))

        # these aren't
        # obviously captain america is... but the search is only reliable with a year included.
        self.assertFalse(tmdb.is_movie('captain_america-720p', tmdb_key))
        self.assertFalse(tmdb.is_movie('Planet.Earth.II.S01E06', tmdb_key))
        self.assertFalse(tmdb.is_movie('The.Marvelous.Mrs.Maisel.S02E02.Mid-way.to.'
                                       'Mid-town.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTb', tmdb_key))
        self.assertFalse(tmdb.is_movie('sherlock.3x02.the_sign_of_three.720p_hdtv_x264-fov', tmdb_key))

    def test_clean_name(self):

        meta = tmdb.clean_name('22 Jump Street 2014 1080p BluRay x265 HEVC 10bit AAC 5.1-LordVako')
        self.assertEqual('22 Jump Street', meta['title'])
        self.assertEqual(2014, meta['year'])
        meta = tmdb.clean_name('Batman.vs.Superman.Dawn.of.Justice.2016')
        self.assertEqual('Batman vs Superman Dawn of Justice', meta['title'])
        self.assertEqual(2016, meta['year'])
        meta = tmdb.clean_name('Brave.2012.1080p.BluRay.x264.AC3-HDChina')
        self.assertEqual('Brave', meta['title'])
        self.assertEqual(2012, meta['year'])
        meta = tmdb.clean_name('captain_america-720p')
        self.assertEqual('captain america', meta['title'])
        self.assertFalse('year' in meta)

        # these aren't
        meta = tmdb.clean_name('Planet.Earth.II.S01E06')
        self.assertEqual('Planet Earth II', meta['title'])
        self.assertFalse('year' in meta)
        self.assertEqual(1, meta['season'])
        self.assertEqual(6, meta['episode'])
        meta = tmdb.clean_name('The.Marvelous.Mrs.Maisel.S02E02.Mid-way.to.Mid-town.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTb')
        self.assertEqual('The Marvelous Mrs Maisel', meta['title'])
        self.assertFalse('year' in meta)
        self.assertEqual(2, meta['season'])
        self.assertEqual(2, meta['episode'])
        meta = tmdb.clean_name('sherlock.3x02.the_sign_of_three.720p_hdtv_x264-fov')
        self.assertEqual('sherlock', meta['title'])
        self.assertFalse('year' in meta)
        self.assertEqual(3, meta['season'])
        self.assertEqual(2, meta['episode'])

    def test_process_configs(self):
        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, None, None, None, None)

        blah_path = '/home/test/blah'
        blarg_path = '/remote/test/blarg'
        test_file = '/home/test/dir/file'

        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, blah_path, None, None, None)

        with self.assertRaises(ConfigurationError):
            CopyMedia(None, TEST_CONFIG, None, None, blarg_path, None, None)

        c = CopyMedia(None, TEST_CONFIG, None, None, blarg_path, test_file, None)

        self.assertEqual(3, len(c.configs['series']))
        self.assertEqual(blarg_path, c.destdir)

        self.assertIsNone(c.scandir)

        c = CopyMedia(None, TEST_CONFIG, None, blah_path, blarg_path, None, None)

        self.assertEqual(blah_path, c.scandir)

    def test_match_files(self):
        c = CopyMedia(None, None, None, None, None, None, None)

        files = ['testFile1', 'testFile2']

        matches = CopyMedia.match_files(files, c.series)
        # should be empty
        self.assertFalse(matches)

        files = ['[HorribleSubs] GATE - 24 [1080p]', '[HorribleSubs] Kimetsu no Yaiba - 26 [1080p]']
        matches = CopyMedia.match_files(files, c.series)
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

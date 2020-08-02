#!/usr/bin/python3

import os
import unittest

import ifttt
import logger
import tmdb
from copy_files import CopyMedia
from exceptions import ConfigurationError

TEST_CONFIG = r'./test_resources/test_CopyMedia.json'
TEST_RESOURCES = r'./test_resources'
IFTTT_CONTEXT_VAR = 'IFTTT_CONTEXT'
TMDB_CONTEXT_VAR = 'TMDB_CONTEXT'

logger.config()


class TestCopyMedia(unittest.TestCase):

    def test_notifications(self):

        ifttt_context = os.getenv(IFTTT_CONTEXT_VAR)
        if ifttt_context is None:
            self.skipTest("Can't find IFTTT trigger context and API key. Add"
                          "property to environment variables: " + IFTTT_CONTEXT_VAR)

        r = ifttt.send_notification([('notafile', {'name': 'test series'})], ifttt.IFTTT_URL_BASE + ifttt_context)

        self.assertEqual(r.status_code, 200)

    def test_find_largest_file(self):
        largest = CopyMedia.find_largest_file(TEST_RESOURCES)
        self.assertEqual(os.path.basename(largest), 'big_file.mp4')

    def test_rename_movie(self):
        starting_dir_name = 'Toy.Story.4.2019.1080p.BluRay.H264.AAC-RARBG'
        new_dir_name = 'Toy_Story_4.2019'
        starting_file_name = 'Toy.Story.4.2019.1080p.BluRay.H264.AAC-RARBG.mp4'
        new_file_name = 'Toy_Story_4.2019.mp4'

        starting_movie_dir = os.path.join(TEST_RESOURCES, starting_dir_name)
        new_movie_dir = os.path.join(TEST_RESOURCES, new_dir_name)

        CopyMedia.rename_movie(os.path.join(starting_movie_dir, starting_file_name))
        self.assertTrue(os.path.isfile(os.path.join(new_movie_dir, new_file_name)))

        os.rename(new_movie_dir, starting_movie_dir)
        os.rename(os.path.join(starting_movie_dir, new_file_name), os.path.join(starting_movie_dir, starting_file_name))

    def test_process_subtitles(self):

        starting_dir_name = 'Toy.Story.4.2019.1080p.BluRay.H264.AAC-RARBG'

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
            CopyMedia(config_file=TEST_CONFIG)

        scan_path = '/home/test/blah'
        series_path = '/remote/test/series'
        movie_path = '/remote/test/movies'
        test_file = '/home/test/dir/file'

        with self.assertRaises(ConfigurationError):
            CopyMedia(config_file=TEST_CONFIG, scandir=scan_path)

        with self.assertRaises(ConfigurationError):
            CopyMedia(config_file=TEST_CONFIG, seriesdir=series_path)

        c = CopyMedia(config_file=TEST_CONFIG, seriesdir=series_path, file=test_file, moviedir=movie_path)

        self.assertEqual(3, len(c.configs['series']))
        self.assertEqual(series_path, c.seriesdir)

        self.assertIsNone(c.scandir)

        c = CopyMedia(config_file=TEST_CONFIG, scandir=scan_path, seriesdir=series_path, moviedir=movie_path)

        self.assertEqual(scan_path, c.scandir)

    def test_match_files(self):
        c = CopyMedia()

        files = ['testFile1', 'testFile2']

        matches, nonmatches = CopyMedia.match_files(files, c.series)
        # should be empty
        self.assertFalse(matches)
        self.assertTrue(nonmatches)

        files = ['[HorribleSubs] GATE - 24 [1080p]', '[HorribleSubs] Kimetsu no Yaiba - 26 [1080p]']
        matches, nonmatches = CopyMedia.match_files(files, c.series)
        self.assertEqual(len(matches), 2)
        self.assertEqual(len(nonmatches), 0)

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

#!/usr/bin/python3

import argparse
import json
import logging
import re
import shutil
from os import listdir, path, makedirs, rename
from os.path import isdir, isfile, join, split

import ifttt
import logger
import tmdb
from exceptions import ConfigurationError

# Set up default file locations for configs and logs
CONFIG_FILE = './CopyMedia.json'

# Set up command line arguments
argParser = argparse.ArgumentParser(description='Copy/transform large files.')

argParser.add_argument('-f', '--file', help='File to process. '
                                            'If not specified, then all files within'
                                            ' the scan directory are checked.')
argParser.add_argument('-d', '--dest', help='Destination directory for series')
argParser.add_argument('-m', '--moviedest', help='Destination directory for movies')
argParser.add_argument('-s', '--scan', help='Directory to scan')
argParser.add_argument('-i', '--ifttt', help='IFTTT trigger URL context and API key')
argParser.add_argument('-c', '--config', help='Configuration file',
                       default=CONFIG_FILE)
argParser.add_argument('-t', '--tmdb', help='The Movie DB API key')
argParser.add_argument('-l', '--log', help='Log file')
argParser.add_argument('delugeArgs', default=[], nargs='*',
                       help='If deluge is used, there will be three args,'
                            ' in this order: Torrent Id, Torrent Name, and Torrent Path')


class CopyMedia:
    file = None
    logfile = None
    configs = None
    config_file = None
    ifttt_url = None
    scandir = None
    seriesdir = None
    moviedir = None
    tmdb = None

    series = None

    def __init__(self, logfile=None, config_file=None, ifttt_url=None, scandir=None,
                 seriesdir=None, file=None, tmdb=None, moviedir=None):
        self.file = file
        self.logfile = logfile
        self.config_file = config_file
        self.ifttt_url = ifttt_url
        self.scandir = scandir
        self.seriesdir = seriesdir
        self.moviedir = moviedir
        self.tmdb = tmdb

        # initialize logging
        if self.logfile:
            logger.config(self.logfile)
        else:
            logger.config()

        logging.debug('Initializing...')

        # initialize configs
        if self.config_file is None:
            self.config_file = CONFIG_FILE

        self.configs = self.process_config_file(self.config_file)

        logging.debug('File arg: [%s]', self.file)
        logging.debug('Log File arg: [%s]', self.logfile)
        logging.debug('Config File arg: [%s]', self.config_file)
        logging.debug('IFTTT URL: [%s]', self.ifttt_url)
        logging.debug('Scan directory: [%s]', self.scandir)
        logging.debug('Series directory: [%s]', self.seriesdir)
        logging.debug('Movie directory: [%s]', self.moviedir)
        logging.debug('TMDB key: [%s]', self.tmdb)

    def execute(self):
        """Initiate the scanning, matching, transformation, and movement of media."""

        logging.debug('Begin processing execution...')

        # Build list of files based on whether a single file has been
        # specified or whether we need to scan a directory
        files = []
        dirs = []
        if self.file:
            self.scandir, file_name = split(self.file)
            files.append(file_name)
        else:
            logging.debug('Scanning [%s] for files to process.', self.scandir)
            files = [f for f in listdir(self.scandir) if isfile(join(self.scandir, f))]
            dirs = [d for d in listdir(self.scandir) if isdir(join(self.scandir, d)) and d != 'tmp']

        if files or dirs:
            if files:
                logging.info('Files found: [%s]', files)
                self.process_files(files)

            if dirs:
                logging.info('Directories found: [%s]', dirs)
                self.process_dirs(dirs)
        else:
            logging.info('No files or directories found. Stopping.')

        logging.debug('Processing complete.')

    def process_dirs(self, dirs):
        """Process all directories provided.

        Directories are treated as potential movies only. First, a query is performed against tmdb to determine
        if there is a matching movie. If so, then process the directory as a movie."""

        logging.debug('Checking directories to see if they are movies...')
        movies = [d for d in dirs if tmdb.is_movie(d, self.tmdb)]
        logging.debug('Found movies: [%s]', movies)

        if self.moviedir is not None:
            for movie in movies:
                self.process_movie(movie)

    def process_movie(self, movie_dir_name):
        """Process a given movie directory.
        
        The following activities are performed:
        1) Identify the actual movie file. This is the single largest file in the directory.
        2) Rename the file and the parent folder to be in the form: <title>.<year>.<extension>
        3) Look for english sub-title files with the srt extension. If found, ensure file is in the same directory as
        the movie file and rename to be in the form: <title>.<year>.en.srt
        4) Remove all other files and sub-directories
        5) Use ffmpeg to strip all meta-data from the movie file
        6) Move the directory to the configured Movie directory."""

        dir = join(self.scandir, movie_dir_name)

        if self.moviedir is not None:
            movie = self.find_largest_file(dir)

            try:
                base_name, movie, dir = self.rename_movie(movie)
            except RuntimeError:
                logging.exception('Could not re-name movie file.')
                return

            subtitle_files = self.process_subtitles(dir, base_name)

            self.clean_dir(dir, movie, subtitle_files)

            self.strip_metadata(movie)

            self.move_movies([dir], self.moviedir, self.scandir)

    @staticmethod
    def find_largest_file(dir):
        """Identify the actual movie file. This is the single largest file in the directory."""

        logging.debug('Looking for largest file in directory: [%s]', dir)
        full_names = [path.join(dir, fname) for fname in listdir(dir)]
        logging.debug('Found file list: [%s]', full_names)
        largest = sorted((path.getsize(s), s) for s in full_names)[-1][1]

        logging.debug('Largest file: [%s]', largest)
        return largest

    @staticmethod
    def rename_movie(movie):
        """Rename the movie file and the parent directory to be in the form: <title>.<year>.<extension>"""

        movie_name = path.basename(movie)
        dir = path.dirname(movie)

        logging.debug('Parsing movie name into meta-data: [%s]', movie_name)

        split_name = path.splitext(movie_name)

        meta = tmdb.clean_name(split_name[0])
        logging.debug('Parsed meta-data: [%s]', meta)
        ext = split_name[1]
        title = meta['title']
        year = str(meta['year'])

        if title and year:
            new_base_name = title + '.' + year
            new_base_name = new_base_name.replace(" ", "_")
            logging.debug('Base name: [%s]', new_base_name)
        else:
            raise RuntimeError('One of movie title or year was not found.')

        parent = path.dirname(dir)
        new_dir_name = join(parent, new_base_name)
        logging.debug('Renaming directory [%s] to [%s]', dir, new_dir_name)
        rename(dir, join(parent, new_base_name))

        current_path = join(new_dir_name, movie_name)
        new_movie_name = join(new_dir_name, new_base_name + ext)
        logging.debug('Renaming file [%s] to [%s]', current_path, new_movie_name)
        rename(current_path, new_movie_name)

        return new_base_name, new_movie_name, new_dir_name

    @staticmethod
    def process_subtitles(dir, base_name):
        """Look for usable english sub-title files.

        If english subtitles found with the srt extension, ensure file is in the same directory as
        the movie file and rename to be in the form: <title>.<year>.en.srt"""

        # TODO
        logging.warning('process_subtitles not implemented yet.')
        return []

    @staticmethod
    def clean_dir(dir, movie, subtitle_files):
        """Remove all other files and sub-directories except the movie file and any sub-titles."""

        # TODO
        logging.warning('clean_dir not implemented yet.')

    @staticmethod
    def strip_metadata(movie):
        """Use ffmpeg to strip all meta-data from the movie file"""

        # TODO
        logging.warning('strip_metadata not implemented yet.')

    def process_files(self, files):
        """Process all individual files provided.

        Files are generally assumed to be tv show episodes although if no matching TV shows are found then
        a check will be performed to determine if the file is a stand-alone movie."""

        # Find matching files
        matches, nonmatches = self.match_files(files, self.series)

        if matches and self.seriesdir is not None:
            # Move matching series files to their respective destination directories
            logging.debug('Found series matches to move: [%s]', matches)
            self.move_series(matches, self.seriesdir, self.scandir)

            if self.ifttt_url is not None:
                ifttt.send_notification(matches, self.ifttt_url)

        if nonmatches and self.moviedir is not None:
            # If there are files that didn't match a configured series and the destination directory
            # for movies has been specified, then check if the remaining files are movies, and if so move
            # to the designated movie directory.
            logging.debug('Some files did not have matches. Checking if they are movies...')
            movie_files = [file for file in files if tmdb.is_movie(file, self.tmdb)]
            logging.debug('Found movies: [%s]', movie_files)
            self.move_movies(movie_files, self.moviedir, self.scandir)

    def process_config_file(self, config_file):
        """Open configuration file, parse json, and pass to processing method."""

        logging.debug('Using configuration file: [%s]', config_file)

        # parse config file as json and process settings found inside
        with open(config_file) as configfile:
            config = json.load(configfile)
            return self.process_configs(config)

    def process_configs(self, config):
        """Used to process the configuration from the configuration file
           and set global settings that will dictate how the rest of the
           execution will proceed. Primarily, this will control whether a
           single file is processed or if an entire directory is scanned for
           new media. It also determines the destination root level directory
           and executes a validation step against all the configured series."""

        # if an individual file is specified either by
        # deluge or via the command line, then just use that.
        # Otherwise, look for a directory to scan and scan the
        # entire folder for matching files.

        if self.file:
            logging.info('File provided for processing: [%s]', self.file)
        else:
            # Only use value from configs if command line argument is not
            # provided.
            if self.scandir is None and 'scanDir' in config:
                self.scandir = config['scanDir']
            logging.info('File not provided, but found directory to scan: [%s]', self.scandir)

        if not self.file and not self.scandir:
            logging.error('Must either specify a file or '
                          'a directory to scan.')
            raise ConfigurationError('Missing directory to scan.')

        # Only use value from configs if command line argument is not
        # provided.
        if self.seriesdir is None and 'seriesDir' in config:
            self.seriesdir = config['seriesDir']

        # Only use value from configs if command line argument is not
        # provided.
        if self.moviedir is None and 'movieDir' in config:
            self.moviedir = config['movieDir']

        if self.seriesdir:
            logging.debug('Destination series directory: [%s]', self.seriesdir)
        else:
            logging.error('Destination series directory must be specified, '
                          'either on the command line or in the '
                          'configuration file.')
            raise ConfigurationError('Missing destination series directory')

        if self.moviedir:
            logging.debug('Destination movie directory: [%s]', self.moviedir)
        else:
            logging.error('Destination movie directory must be specified, '
                          'either on the command line or in the '
                          'configuration file.')
            raise ConfigurationError('Missing destination movie directory')

        if self.ifttt_url:
            logging.debug('IFTTT URL: [%s]', self.ifttt_url)
        else:
            logging.debug('IFTTT notification url not provided.')

        if self.tmdb:
            logging.debug('TMDB API Key: [%s]', self.tmdb)
        else:
            logging.debug('TMDB API key not provided.')

        if 'series' in config:
            self.series = config['series']
            self.validate_series(self.series)
        else:
            logging.warning('No series configured.')

        return config

    @staticmethod
    def validate_series(series):
        """Used to validate the series entries in the configuration.
           A series must have at least a name and a regex pattern to
           match file names against."""

        for show in series:
            logging.log(logger.TRACE, 'Validate show [%s]', show)
            if 'name' not in show:
                logging.error('[%s] has no name defined.',
                              str(show))
                raise KeyError('name')
            else:
                logging.log(logger.TRACE, 'Found name [%s] for show [%s]', show['name'], show)
            if 'regex' not in show:
                logging.error('[%s] has no regex pattern defined.',
                              show['name'])
                raise KeyError('regex')
            else:
                logging.log(logger.TRACE, 'Found regex [%s] for show name [%s]', show['regex'], show['name'])
        return True

    @staticmethod
    def move_movies(movie_files, move_dir, start_dir):
        """Move movie files to the specified destination directory"""

        for file_name in movie_files:

            # Move file to destination folder, renaming on the way
            logging.debug('Moving [%s] to [%s]...',
                          join(start_dir, file_name), join(move_dir, file_name))
            shutil.move(join(start_dir, file_name), join(move_dir, file_name))
            logging.info('Successfully moved [%s] to [%s]',
                         join(start_dir, file_name), join(move_dir, file_name))

    @staticmethod
    def move_series(matches, move_dir, start_dir):
        """Move matching series files to their respective destination directory"""

        destinations = set()

        for file_name, config_entry in matches:

            # Determine destination file_name if a replace attribute
            # was specified
            dest_file_name = file_name
            if 'replace' in config_entry:
                dest_file_name = re.sub(config_entry['regex'],
                                        config_entry['replace'],
                                        file_name)
                logging.debug('New name for [%s] will be [%s]',
                              file_name, dest_file_name)

            # Build destination directory path
            if 'destination' in config_entry:
                dest = join(move_dir, config_entry['destination'])
            else:
                dest = join(move_dir, config_entry['name'])

            logging.debug('Destination directory: [%s]', dest)

            # Create destination directory if it doesn't already exist
            if not path.exists(dest):
                logging.info('Destination does not exist; creating [%s]', dest)
                makedirs(dest)

            # Move file to destination folder, renaming on the way
            logging.debug('Moving [%s] to [%s]...',
                          join(start_dir, file_name), join(dest, dest_file_name))
            shutil.move(join(start_dir, file_name), join(dest, dest_file_name))
            logging.info('Successfully moved [%s] to [%s]',
                         join(start_dir, file_name), join(dest, dest_file_name))

            destinations.add(dest)

        return destinations

    @staticmethod
    def match_files(files, series):
        """Find matching files given a list of files and a list of series."""

        matches = []
        nonmatches = []
        for f in files:
            matched = False
            for show in series:
                logging.log(logger.TRACE, 'Checking [%s] against [%s] using pattern [%s]',
                            f, show['name'], show['regex'])
                if re.match(show['regex'], f):
                    matches.append((f, show))
                    matched = True
                    logging.info('File [%s] matches series [%s]',
                                 f, show['name'])
                    break
            if not matched:
                logging.debug('Adding [%s] to list of non-matches', f)
                nonmatches.append(f)

        return matches, nonmatches


def main():
    """Parsing command line argument and then begin the copying execution."""

    args = argParser.parse_args()

    file = None
    torrent_name = None
    torrent_path = None
    trigger_url = None
    num_args = len(args.delugeArgs)
    if args.delugeArgs and num_args >= 3:
        torrent_name = args.delugeArgs[1]
        torrent_path = args.delugeArgs[2]
        if num_args == 4:
            trigger_url = ifttt.IFTTT_URL_BASE + '/' + args.delugeArgs[3]

    if args.ifttt and trigger_url is None:
        trigger_url = ifttt.IFTTT_URL_BASE + '/' + args.ifttt

    # set base file path based on deluge args if they exist
    if torrent_name and torrent_path:
        file = join(torrent_path, torrent_name)
    # over-ride with explicit filepath from cmd if available
    if args.file:
        file = args.file

    # Now execute file transforms/copy
    try:
        c = CopyMedia(logfile=args.log, config_file=args.config, ifttt_url=trigger_url,
                      scandir=args.scan, seriesdir=args.dest, file=file, tmdb=args.tmdb,
                      moviedir=args.moviedest)
        c.execute()
    except Exception:
        logging.exception('Error on execution.')
        raise


if __name__ == '__main__':
    main()

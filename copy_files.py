#!/usr/bin/python3

import argparse
import json
import logging
import platform
import re
import shutil
import subprocess
from os import listdir, path, makedirs
from os.path import isfile, join, split

import requests

from exceptions import ConfigurationError

# Set up default file locations for configs and logs
CONFIG_FILE = './CopyMedia.json'
LOG_FILE = './copy-files.log'
IFTTT_URL_BASE = 'https://maker.ifttt.com/trigger'
FORMAT = '%(asctime)-15s %(levelname)s %(message)s'

# Set up command line arguments
argParser = argparse.ArgumentParser(description='Copy/transform large files.')

argParser.add_argument('-f', '--file', help='File to process. '
                                            'If not specified, then all files within'
                                            ' the scan directory are checked.')
argParser.add_argument('-d', '--dest',
                       help='Destination parent directory')
argParser.add_argument('-s', '--scan', help='Directory to scan')
argParser.add_argument('-i', '--ifttt', help='IFTTT trigger URL context and API key')
argParser.add_argument('-c', '--config', help='Configuration file',
                       default=CONFIG_FILE)
argParser.add_argument('-l', '--log', help='Log file', default=LOG_FILE)
argParser.add_argument('delugeArgs', default=[], nargs='*',
                       help='If deluge is used, there will be four args,'
                            ' in this order: Torrent Id, Torrent Name,'
                            ' Torrent Path, and IFTTT URL context with API key.')

TRACE = 8
logging.addLevelName(TRACE, 'TRACE')


def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(TRACE, message, args, **kws)


logging.trace = trace
logging.Logger.trace = trace

logLevel = TRACE


class CopyMedia:
    file = None
    logfile = None
    configs = None
    config_file = None
    ifttt_url = None
    scandir = None
    destdir = None

    series = None

    def __init__(self, logfile, config_file, ifttt_url, scandir, destdir, file):
        self.file = file
        self.logfile = logfile
        self.config_file = config_file
        self.ifttt_url = ifttt_url
        self.scandir = scandir
        self.destdir = destdir

        # initialize logging
        if self.logfile is None:
            self.logfile = LOG_FILE

        logging.basicConfig(filename=self.get_path(self.logfile),
                            level=logLevel, format=FORMAT, filemode='a')

        # initialize configs
        if self.config_file is None:
            self.config_file = CONFIG_FILE

        self.configs = self.process_config_file(self.config_file)

    def execute(self):
        """Initiate the scanning, matching, transformation, and movement of media."""

        # Build list of files based on whether a single file has been
        # specified or whether we need to scan a directory
        files = []
        if self.file:
            scan_dir, file_name = split(self.file)
            files.append(file_name)
        else:
            files = [f for f in listdir(self.scandir) if isfile(join(self.scandir, f))]

        # Find matching files
        matches = self.match_files(files, self.series)

        if matches:
            # Move matching files to their respective destination directories
            self.move_files(matches, self.destdir, self.scandir)

            # Send notification to phone
            self.send_notification(matches, self.ifttt_url)

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
            logging.debug('Found file to match [%s]', self.file)
        else:
            # Only use value from configs if command line argument is not
            # provided.
            if self.scandir is None and 'scanDir' in config:
                self.scandir = config['scanDir']
            logging.debug('Found directory to scan: [%s]', self.scandir)

        if not self.file and not self.scandir:
            logging.error('Must either specify a file or '
                          'a directory to scan.')
            raise ConfigurationError('Missing directory to scan.')

        # Only use value from configs if command line argument is not
        # provided.
        if self.destdir is None and 'moveDir' in config:
            self.destdir = config['moveDir']

        if self.destdir:
            logging.debug('Destination Parent Directory: [%s]', self.destdir)
        else:
            logging.error('Destination directory must be specified, '
                          'either on the command line or in the '
                          'configuration file.')
            raise ConfigurationError('Missing destination directory')

        if self.ifttt_url:
            logging.debug('IFTTT URL: [%s]', self.ifttt_url)
        else:
            logging.warning('IFTTT notification url not provided.')

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
            logging.log(TRACE, 'Validate show [%s]', show)
            if 'name' not in show:
                logging.error('[%s] has no name defined.',
                              str(show))
                raise KeyError('name')
            else:
                logging.log(TRACE, 'Found name [%s] for show [%s]', show['name'], show)
            if 'regex' not in show:
                logging.error('[%s] has no regex pattern defined.',
                              show['name'])
                raise KeyError('regex')
            else:
                logging.log(TRACE, 'Found regex [%s] for show name [%s]', show['regex'], show['name'])
        return True

    @staticmethod
    def send_notification(matches, trigger_url):
        """Send IFTTT notification to phone whenever the script fires with the names
            of the new episodes"""

        # Only send notification if there is at least one matching file.
        if matches:
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

    @staticmethod
    def move_files(matches, move_dir, scan_dir):
        """Move matching files to their respective destination directory"""

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

            # Create destination directory if it doesn't already exist
            if not path.exists(dest):
                logging.info('Destination does not exist; creating [%s]', dest)
                makedirs(dest)

            # Move file to destination folder, renaming on the way
            logging.debug('Moving [%s] to [%s]...',
                          join(scan_dir, file_name), join(dest, dest_file_name))
            shutil.move(join(scan_dir, file_name), join(dest, dest_file_name))
            logging.info('Successfully moved [%s] to [%s]',
                         join(scan_dir, file_name), join(dest, dest_file_name))

            destinations.add(dest)

        return destinations

    @staticmethod
    def match_files(files, series):
        """Find matching files given a list of files and a list of series."""

        matches = []
        for f in files:
            for show in series:
                logging.log(TRACE, 'Checking [%s] against [%s] using pattern [%s]',
                            f, show['name'], show['regex'])
                if re.match(show['regex'], f):
                    matches.append((f, show))
                    logging.info('File [%s] matches series [%s]',
                                 f, show['name'])
                    break

        return matches

    @staticmethod
    def get_path(argpath):
        """Convert path to cygwin format if running on a cygwin platform"""

        if 'CYGWIN' in platform.system():
            argpath = subprocess.getoutput('cygpath ' + argpath)
        return argpath


def main():
    """Parsing command line argument and then begin the copying execution."""

    args = argParser.parse_args()
    print('All command line arguments: ' + str(args))

    file = None
    torrent_name = None
    torrent_path = None
    trigger_url = None
    if args.delugeArgs and len(args.delugeArgs) == 4:
        torrent_name = args.delugeArgs[1]
        torrent_path = args.delugeArgs[2]
        trigger_url = IFTTT_URL_BASE + '/' + args.delugeArgs[3]

    if args.ifttt and trigger_url is None:
        trigger_url = IFTTT_URL_BASE + '/' + args.ifttt

    # set base file path based on deluge args if they exist
    if torrent_name and torrent_path:
        file = join(torrent_path, torrent_name)
    # over-ride with explicit filepath from cmd if available
    if args.file:
        file = args.file

    # Now execute file transforms/copy
    c = CopyMedia(args.log, args.config, trigger_url, args.scan, args.dest, file)
    c.execute()


if __name__ == '__main__':
    main()

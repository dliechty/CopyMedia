#!/usr/bin/python3

import argparse
import logging
import subprocess
import platform
import json
import re
import requests
from os import listdir, path, makedirs
from os.path import isfile, join, split
import shutil

# Set up default file locations for configs and logs
CONFIG_FILE = '/home/david/CopyAnime/CopyAnime.json'
LOG_FILE = '/home/david/copy-files.log'
PLEX_LIBRARY = {'Anime': 3, 'Movies': 1, 'TV Shows': 2}
PLEX_SCANNER = ('/usr/lib/plexmediaserver/Plex Media Scanner')
PROP_FILE = '/etc/default/plexmediaserver'
BIN_FOLDER = '/usr/lib/plexmediaserver'

IFTTT_URL = 'https://maker.ifttt.com/trigger/PLEX_NEW/with/key/dFHLoSLaYm8b1VsTyjan1I'

# Set up command line arguments
argParser = argparse.ArgumentParser(description='Copy/transform large files,'
                                    ' then trigger plex media server to scan'
                                    ' destination folder.')

argParser.add_argument('-f', '--file', help='File to process. '
                       'If not specified, then all files within'
                       ' the scan directory are checked.')
argParser.add_argument('-d', '--dest',
                       help='Destination parent directory')
argParser.add_argument('-s', '--scan', help='Directory to scan')
argParser.add_argument('-c', '--config', help='Configuration file',
                       default=CONFIG_FILE)
argParser.add_argument('-l', '--log', help='Log file', default=LOG_FILE)
argParser.add_argument('-p', '--plexlibrary',
                       help='Plex library name to scan based on new files.',
                       default='Anime')
argParser.add_argument('delugeArgs', default=[], nargs='*',
                       help='If deluge is used, there will be three args,'
                            ' in this order: Torrent Id, Torrent Name,'
                            ' Torrent Path')

logLevel = logging.DEBUG
FORMAT = '%(asctime)-15s %(levelname)s %(message)s'


def main():
    args = argParser.parse_args()

    logging.basicConfig(filename=getPath(args.log),
                        level=logLevel, format=FORMAT, filemode='a')

    logging.debug('Using configuration file: [%s]', args.config)

    logging.debug('All command line arguments: [%s]', args)

    with open(args.config) as configFile:
        config = json.load(configFile)

        # if an individual file is specified either by
        # deluge or via the command line, then just use that.
        # Otherwise, look for a directory to scan and scan the
        # entire folder for matching files.

        file = None
        torrentName = None
        torrentPath = None
        if args.delugeArgs and len(args.delugeArgs) == 3:
            torrentName = args.delugeArgs[1]
            torrentPath = args.delugeArgs[2]

        # set base file path based on deluge args if they exist
        if torrentName and torrentPath:
            file = join(torrentPath, torrentName)
        # over-ride with explicit filepath from cmd if available
        if args.file:
            file = args.file

        if file:
            logging.debug('Scanning file [%s]', file)
        else:
            # Check config for scanDir first
            if 'scanDir' in config:
                scanDir = config['scanDir']
            # Override if specified as command line arg
            if args.scan:
                scanDir = args.scan
            logging.debug('Scanning Directory: [%s]', scanDir)

        if not file and not scanDir:
            logging.exception('Must either specify a file or '
                              'a directory to scan.')

        # get destination directory from configs first
        if 'moveDir' in config:
            moveDir = config['moveDir']
        # over-ride from cmd if available
        if args.dest:
            moveDir = args.dest

        if moveDir:
            logging.debug('Destination Parent Directory: [%s]', moveDir)
        else:
            logging.exception('Destination directory must be specified, '
                              'either on the command line or in the '
                              'configuration file.')

        # Build list of files based on whether a single file has been
        # specified or whether we need to scan a directory
        files = []
        if file:
            scanDir, fileName = split(file)
            files.append(fileName)
        else:
            files = [f for f in listdir(scanDir) if isfile(join(scanDir, f))]

        # Find matching files
        matches = matchFiles(files, config['series'])

        # Move matching files to their respective destination directories
        moveFiles(matches, moveDir, scanDir)

        # Send notification to phone
        sendNotification(matches)


def sendNotification(matches):
    '''Send IFTTT notification to phone whenever the script fires with the names
        of the new episodes'''

    # Only send notification if there is at least one matching file.
    if matches:
        # Get series name for each matching file and concatenate
        # into a string separated by ' and '
        names = [config['name'] for file, config in matches]
        nameString = ' and '.join(names)

        logging.debug('Sending notification with name string: [%s] to IFTTT',
                      nameString)

        r = requests.post(IFTTT_URL, data={'value1': nameString})
        logging.debug('IFTTT POST status: [%s] with reason: [%s]',
                      r.status_code, r.reason)


def moveFiles(matches, moveDir, scanDir):
    '''Move matching files to their respective destination directory'''

    destinations = set()

    for fileName, configEntry in matches:

        # Determine destination fileName if a replace attribute
        # was specified
        destFileName = fileName
        if 'replace' in configEntry:
            destFileName = re.sub(configEntry['regex'],
                                  configEntry['replace'], fileName)
            logging.debug('New name for [%s] will be [%s]',
                          fileName, destFileName)

        # Build destination directory path
        if 'destination' in configEntry:
            dest = join(moveDir, configEntry['destination'])
        else:
            dest = join(moveDir, configEntry['name'])

        # Create destination directory if it doesn't already exist
        if not path.exists(dest):
            logging.info('Destination does not exist; creating [%s]', dest)
            makedirs(dest)

        # Move file to destination folder, renaming on the way
        logging.debug('Moving [%s] to [%s]...',
                      join(scanDir, fileName), join(dest, destFileName))
        shutil.move(join(scanDir, fileName), join(dest, destFileName))
        logging.info('Successfully moved [%s] to [%s]',
                     join(scanDir, fileName), join(dest, destFileName))

        destinations.add(dest)

    return destinations


def scanPlex(plexLibrary, destinations):
    '''DEPRECATED. Now use direct flexget integration

        Trigger plex scan on either an entire library if more than one match
        was found or on the specific directory associated with a single match.
    '''

    # Establish command template. For each destination, replace the last
    # entry in the list with the destination path. No need to clone list.
    command = [PLEX_SCANNER, '--scan', '--refresh', '--section',
               str(PLEX_LIBRARY[plexLibrary]), '--directory', '']

    for destination in destinations:
        command[-1] = destination
        logging.debug('Initiating Plex Scan on [%s]...', destination)
        process = subprocess.Popen(command,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b''):
            logging.debug(line.decode('ascii').strip())

        logging.info('Plex Scan on [%s] complete.', destination)


def matchFiles(files, series):
    '''Find matching files given a list of files and a list of series.'''

    matches = []
    for f in files:
        for show in series:
            logging.debug('Checking [%s] against [%s] using pattern [%s]',
                          f, show['name'], show['regex'])
            if show['regex']:
                if re.match(show['regex'], f):
                    matches.append((f, show))
                    logging.info('File [%s] matches series [%s]',
                                 f, show['name'])
            else:
                logging.error('[%s] has no regex pattern defined.',
                              show['name'])
    return matches


def getPath(path):
    '''Convert path to cygwin format if running on a cygwin platform'''

    if 'CYGWIN' in platform.system():
        path = subprocess.getoutput('cygpath ' + path)
    return path


if __name__ == '__main__':
    main()

#!/usr/bin/python3

import argparse
import logging
import subprocess
import platform
import json
import re
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
argParser.add_argument('torrentid', help='Torrent Id')
argParser.add_argument('torrentname', help='Torrent Name')
argParser.add_argument('torrentpath', help='Torrent Path')

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

        # if hasFile is true, then only check that one file
        # against the configs. If file is not set, then scan
        # the entire directory for files
        file = None
        if args.torrentpath:
            file = join(args.torrentpath, args.torrentname)
        if args.file:
            file = args.file

        if file:
            logging.debug('Scanning file [%s]', file)
        else:
            scanDir = args.scan
            if 'scanDir' in config:
                scanDir = config['scanDir']
            logging.debug('Scanning Directory: [%s]', scanDir)

        # Retrieve destination parent directory
        moveDir = args.dest
        if 'moveDir' in config:
            moveDir = config['moveDir']
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
        destinations = moveFiles(matches, moveDir, scanDir)

        # Trigger plex scan in either the entire library or the specific
        # folder associated with the specified file
        scanPlex(args.plexlibrary, destinations)


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
    '''Trigger plex scan on either an entire library if more than one match
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

#!/usr/bin/python3

import argparse
import logging
import subprocess
import platform
import json
import re
from os import listdir
from os.path import isfile, join
import shutil

# Set up default file locations for configs and logs
CONFIG_FILE = 'D:/Downloads/CopyAnime.json'
LOG_FILE = 'D:/Downloads/fileCopy.log'
PLEX_LIBRARY = 'Anime'

# Set up command line arguments
argParser = argparse.ArgumentParser(description='Copy/transform large files,'
                                    ' then trigger plex media server to scan'
                                    ' destination folder.')

argParser.add_argument('-f', '--file', help='File to process')
argParser.add_argument('-d', '--dest',
                       help='Destination parent directory')
argParser.add_argument('-s', '--scan', help='Directory to scan')
argParser.add_argument('-c', '--config', help='Configuration file',
                       default=CONFIG_FILE)
argParser.add_argument('-l', '--log', help='Log file', default=LOG_FILE)
argParser.add_argument('-p', '--plex',
                       help='Plex library to scan based on new files.',
                       default=PLEX_LIBRARY)

logLevel = logging.DEBUG
FORMAT = '%(asctime)-15s %(levelname)s %(message)s'


def main():
    args = argParser.parse_args()

    logging.basicConfig(filename=getPath(args.log),
                        level=logLevel, format=FORMAT, filemode='a')

    logging.debug('Using configuration file: [%s]', args.config)

    with open(args.config) as configFile:
        config = json.load(configFile)

        # if hasFile is true, then only check that one file
        # against the configs. If file is not set, then scan
        # the entire directory for files
        hasFile = False
        if args.file:
            hasFile = True

        if hasFile:
            logging.debug('Scanning file [%s]', args.file)
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
        if hasFile:
            files.append(args.file)
        else:
            files = [f for f in listdir(scanDir) if isfile(join(scanDir, f))]

        # Find matching files
        matches = matchFiles(files, config['series'])

        # Move matching files to their respective destination directories
        moveFiles(matches, moveDir, scanDir)

        # Trigger plex scan in either the entire library or the specific
        # folder associated with the specified file
        scanPlex(hasFile)


def moveFiles(matches, moveDir, scanDir):
    '''Move matching files to their respective destination directory'''

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

        # Move file to destination folder, renaming on the way
        logging.debug('Moving [%s] to [%s]...',
                      join(scanDir, fileName), join(dest, destFileName))
        shutil.move(join(scanDir, fileName), join(dest, destFileName))
        logging.info('Successfully moved [%s] to [%s]',
                     join(scanDir, fileName), join(dest, destFileName))


def scanPlex(matches):
    '''Trigger plex scan on either an entire library if more than one match
        was found or on the specific directory associated with a single match.
    '''

    # TODO


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
                    logging.info('++++++ File [%s] matches entry [%s]',
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

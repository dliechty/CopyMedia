#!/usr/bin/python3

import argparse
import logging
import subprocess
import platform
import json
import re
from os import listdir
from os.path import isfile, join

# Set up default file locations for configs and logs
CONFIG_FILE = 'D:/Downloads/CopyAnime.json'
LOG_FILE = 'D:/Downloads/fileCopy.log'

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

logLevel = logging.DEBUG
FORMAT = '%(asctime)-15s %(levelname)s %(message)s'


def main():
    global configFile
    global logFile
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
            if config['scanDir']:
                scanDir = config['scanDir']
            logging.debug('Scanning Directory: [%s]', scanDir)

        # Retrieve destination parent directory
        moveDir = args.dest
        if config['moveDir']:
            moveDir = config['moveDir']
        logging.debug('Destination Parent Directory: [%s]', moveDir)

        files = []
        if hasFile:
            files.append(args.file)
        else:
            files = [f for f in listdir(scanDir) if isfile(join(scanDir, f))]

        for f in files:
            for show in config['series']:
                logging.debug('Checking [%s] against [%s] using pattern [%s]',
                              f, show['name'], show['regex'])
                if show['regex']:
                    if re.match(show['regex'], f):
                        logging.info('++++++ File [%s] matches entry [%s]',
                                     f, show['name'])
                else:
                    logging.error('[%s] has no regex pattern defined.',
                                  show['name'])


def getPath(path):
    '''Convert path to cygwin format if running on a cygwin platform'''

    if 'CYGWIN' in platform.system():
        path = subprocess.getoutput('cygpath ' + path)
    return path

if __name__ == '__main__':
    main()

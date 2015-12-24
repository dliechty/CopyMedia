#!/usr/bin/python3

import argparse
import logging

# Set up command line arguments
argParser = argparse.ArgumentParser(description='Copy/transform large files,'
                                    ' then trigger plex media server to scan'
                                    ' destination folder.')

argParser.add_argument('-f', '--file', help='File to process')
argParser.add_argument('-d', '--dest',
                       help='Destination parent directory')
argParser.add_argument('-s', '--scan', help='Directory to scan')
argParser.add_argument('-c', '--config', help='Configuration file')
argParser.add_argument('-l', '--log', help='Log file')

# Set up default file locations for configs and logs
configFile = 'D:\\Downloads\\CopyAnime.json'
logFile = 'D:\\Downloads\\fileCopy.log'

logLevel = logging.DEBUG
FORMAT = '%(asctime)-15s:%(levelname)s:%(message)s'


def main():
    global configFile
    global logFile
    args = argParser.parse_args()
    if args.config:
        configFile = args.config

    if args.log:
        logFile = args.log

    logging.basicConfig(filename=logFile,
                        level=logLevel, format=FORMAT, filemode='a')

    logging.debug('Using configuration file: %s', str(configFile))

if __name__ == '__main__':
    main()

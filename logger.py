import logging
import platform
import subprocess

LOG_FILE = './copy-files.log'
FORMAT = '[%(asctime)-15s %(filename)s:%(lineno)s - %(funcName)20s() %(levelname)s] %(message)s'

TRACE = 8
logging.addLevelName(TRACE, 'TRACE')


def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE):
        # Yes, logger takes its '*args' as 'args'.
        self._log(TRACE, message, args, **kws)


logging.trace = trace
logging.Logger.trace = trace

logLevel = logging.DEBUG


def config(logfile=LOG_FILE):
    logging.basicConfig(filename=get_path(logfile),
                        level=logLevel, format=FORMAT, filemode='a')


def get_path(argpath):
    """Convert path to cygwin format if running on a cygwin platform"""

    if 'CYGWIN' in platform.system():
        argpath = subprocess.getoutput('cygpath ' + argpath)
    return argpath
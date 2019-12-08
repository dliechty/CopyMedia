import logging

# Set up TRACE log level, which is slightly more verbose than DEBUG
logging.TRACE = logging.DEBUG - 2
logging.addLevelName(logging.DEBUG - 2, 'TRACE')


class MyLogger(logging.getLoggerClass()):
    def trace(self, msg, *args, **kwargs):
        self.log(logging.TRACE, msg, *args, **kwargs)
#!/usr/bin/python3
'''
common data structures needed by various parts of kybyz
'''
import os, logging, logging.handlers  # pylint: disable=multiple-imports
from collections import defaultdict, deque

CACHED = defaultdict(str, {'uptime': None})
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz')
KYBYZ_HOME = os.path.join(CACHE, 'home')
BASE_LOG_FORMAT = '%(levelname)-8s %(message)s'
EXTENDED_LOG_FORMAT = '%(asctime)s %(threadName)-8s ' + BASE_LOG_FORMAT
LOG_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
LOGFILE = os.path.join(os.path.join(HOME, 'log', 'kybyz.log'))
LOGFILE_HANDLER = logging.FileHandler(LOGFILE)
LOGFILE_HANDLER.setFormatter(logging.Formatter(EXTENDED_LOG_FORMAT))
MESSAGE_QUEUE = deque(maxlen=1024)

logging.basicConfig(
    level=logging.DEBUG if __debug__ else logging.INFO,
    format=BASE_LOG_FORMAT
)
logging.getLogger('').addHandler(LOGFILE_HANDLER)

class DequeHandler(logging.NullHandler):
    '''
    simple handler to append log record to queue
    '''
    def handle(self, record):
        if hasattr(record, 'to_page'):
            MESSAGE_QUEUE.append(':'.join([
                record.name,
                record.levelname,
                record.msg % record.args
            ]))

logging.getLogger('').addHandler(DequeHandler())

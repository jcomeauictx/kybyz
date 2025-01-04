#!/usr/bin/python3
'''
common data structures needed by various parts of kybyz
'''
import sys, os, logging, re  # pylint: disable=multiple-imports
from collections import defaultdict, deque, namedtuple
from datetime import datetime, timezone

COMMAND = os.path.splitext(os.path.basename(sys.argv[0]))[0]
ARGS = sys.argv[1:]
EXAMPLE = 'example.kybyz'  # subdirectory with sample posts
CACHED = defaultdict(str, {'uptime': None})
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz')
KYBYZ_HOME = os.path.join(CACHE, 'home')
BASE_LOG_FORMAT = '%(levelname)s:%(name)s:%(message)s'
EXTENDED_LOG_FORMAT = '%(asctime)s:%(threadName)s:' + BASE_LOG_FORMAT
LOG_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
LOGDIR = os.getenv('KB_LOGDIR', os.path.join(HOME, 'log'))
os.makedirs(LOGDIR, exist_ok=True)
LOGFILE = os.path.join(os.path.join(LOGDIR, 'kybyz.log'))
LOGSTREAM_HANDLER = logging.StreamHandler()
# limit logging to screen when using kbz> commandline
LOGLEVEL = logging.DEBUG if ARGS or os.getenv('KB_DEBUG') else logging.INFO
if not os.path.split(sys.argv[0])[1].endswith(('doctest', 'doctest.py')):
    LOGSTREAM_HANDLER.setLevel(LOGLEVEL)
LOGFILE_HANDLER = logging.FileHandler(LOGFILE)
LOGFILE_HANDLER.setLevel(logging.DEBUG)
LOGFILE_HANDLER.setFormatter(logging.Formatter(EXTENDED_LOG_FORMAT))
MESSAGE_QUEUE = deque(maxlen=1024)
POSTS_QUEUE = deque(maxlen=1024)
TO_PAGE = {'extra': {'to_page': True}}
REGISTRATION = namedtuple('registration', ('username', 'email', 'gpgkey'))
CHANNEL = '#kybyz'
JSON = re.compile(r'^\{.*\}$')

class DequeHandler(logging.NullHandler):
    '''
    simple handler to append log record to queue

    >>> logging.debug('test')
    >>> logging.debug('test to page', **TO_PAGE)
    '''
    def handle(self, record):
        if hasattr(record, 'to_page') and record.to_page:
            #logging.debug('adding to MESSAGE_QUEUE: %s', record)
            MESSAGE_QUEUE.append(':'.join([
                record.name,
                record.levelname,
                record.msg % record.args
            ]))

LOGQUEUE_HANDLER = DequeHandler()
LOGQUEUE_HANDLER.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.DEBUG if __debug__ else logging.INFO,
    format=BASE_LOG_FORMAT,
    handlers=[LOGSTREAM_HANDLER, LOGFILE_HANDLER, LOGQUEUE_HANDLER]
)
logging.info('COMMAND: %s, ARGS: %s', COMMAND, ARGS)

def read(filename):
    '''
    read and return file contents
    '''
    with open(filename, 'rb') as infile:
        return infile.read()

def make_timestamp():
    '''
    untrusted timestamp.

    will need blockchain for a trusted timestamp
    '''
    return datetime.now(timezone.utc).isoformat()

def tuplify(versionstring):
    '''
    convert version string to tuple of integers

    >>> tuplify('0.0.1')
    (0, 0, 1)
    >>> max(['0.0.100', '0.0.11'])
    '0.0.11'
    >>> max(['0.0.100', '0.0.11'], key=tuplify)
    '0.0.100'
    '''
    return tuple(int(s) for s in versionstring.split('.'))

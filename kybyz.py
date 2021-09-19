#!/usr/bin/python3
'''
Version 0.1 of Kybyz, a peer to peer (p2p) social media platform
'''
import sys, os, time, threading  # pylint: disable=multiple-imports
from urllib.request import urlopen
from ircbot import IRCBot
from kbutils import read, logging
from post import BasePost

COMMAND = sys.argv[0]
ARGS = sys.argv[1:]
logging.info('COMMAND: %s, ARGS: %s', COMMAND, ARGS)
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz')
CACHED = {'uptime': None}
KYBYZ_HOME = os.path.join(CACHE, 'home')
EXAMPLE = 'example.kybyz'  # subdirectory with sample posts
KNOWN = ['post', 'netmeme', 'kybyz']  # known post types
COMMANDS = ['post', 'register']

def init():
    '''
    initialize application
    '''
    os.makedirs(CACHE, 0o700, exist_ok=True)
    CACHED['uptime'] = 0
    kybyz = threading.Thread(target=background, name='kybyz')
    kybyz.daemon = True
    kybyz.start()

def serve(env=None, start_response=None):
    '''
    handle web requests
    '''
    page = b'(Something went wrong)'
    env = env or {}
    requested = env.get('REQUEST_URI', None).lstrip('/')
    logging.debug('requested: "%s"', requested)
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    if requested is not None and start_response:
        if requested == '':
            page = read('timeline.html').decode()
            posts = ['<div>kybyz active %s seconds</div>' % CACHED['uptime']]
            posts.extend(['<div>%s</div>' % post for post in loadposts()])
            page = page.format(posts=''.join(posts)).encode()
        elif os.path.exists(requested):
            page = read(requested)
            headers = [('Content-type', guess_mimetype(requested, page))]
        elif requested.startswith('ipfs/'):
            with urlopen('https://ipfs.io/' + requested) as request:
                page = request.read()
                headers = [('Content-type', guess_mimetype(requested, page))]
        else:
            logging.warning('%s not found', requested)
            status = '404 Not Found'
            page = b'<div>not yet implemented</div>'
        start_response(status, headers)
        return [page]
    logging.warning('serve: failing with env=%s and start_response=%s',
                    env, start_response)
    return None

def register(username=None, email=None):
    '''
    register kybyz account
    '''
    check_username = check_email = None
    if username is None or email is None:
        logging.error('Usage: %s %s USERNAME EMAIL_ADDRESS',
                      COMMAND, ARGS[0])
        raise ValueError('Must specify desired username and email address')
    try:
        check_username = os.readlink(KYBYZ_HOME)
        check_email = os.readlink(check_username)
        if (os.path.split(check_username)[1] != username or
                os.path.split(check_email)[1] != email):
            raise ValueError('Previously registered as %s' %
                             os.path.split(check_username)[1])
        logging.warning('Already registered as %s', username)
    except FileNotFoundError:
        logging.debug('Not already registered (no such directory)')
        os.makedirs(os.path.join(CACHE, email))
        os.symlink(os.path.join(CACHE, email), os.path.join(CACHE, username))
        os.symlink(os.path.join(CACHE, username), KYBYZ_HOME)
    except OSError as not_a_link:  # one of the two was not a symlink
        if check_username is not None:
            # see if it's the same username already registered
            if os.path.split(check_username)[1] == username:
                os.rename(check_username, os.path.join(CACHE, email))
                os.symlink(os.path.join(CACHE, email), check_username)
                os.symlink(check_username, KYBYZ_HOME)
            else:
                raise ValueError(
                    'Already registered as %s' %
                    os.path.split(check_username)[1]) from not_a_link
        else:
            logging.debug('Not already registered (directory not a link)')
            os.rename(KYBYZ_HOME, os.path.join(CACHE, email))
            os.symlink(os.path.join(CACHE, email),
                       os.path.join(CACHE, username))
            os.symlink(os.path.join(CACHE, username), KYBYZ_HOME)

def guess_mimetype(filename, contents):
    '''
    guess and return mimetype based on name and/or contents
    '''
    logging.debug('filename: %s, contents: %r', filename, contents[:32])
    extension = os.path.splitext(filename)[1]
    mimetypes = {
        '.jpg': 'image/jpeg',
        '.css': 'text/css',
    }
    return mimetypes.get(extension, 'text/html')

def loadposts(to_html=True):
    '''
    fetch and return all posts from KYBYZ_HOME or, if empty, from EXAMPLE

    setting to_html to True forces conversion from JSON format to HTML
    '''
    if os.path.exists(KYBYZ_HOME) and os.listdir(KYBYZ_HOME):
        directory = KYBYZ_HOME
    else:
        directory = EXAMPLE
    post = BasePost if to_html else read
    posts = [post(os.path.join(directory, filename))
             for filename in os.listdir(directory)]
    return list(filter(None, posts))

def background():
    '''
    load and maintain cache

    communicate with other kybyz servers
    '''
    delay = 10  # seconds
    ircbot = IRCBot()
    logging.info('ircbot: %s', ircbot)
    while True:
        time.sleep(delay)  # releases the GIL for `serve`
        CACHED['uptime'] += delay
        logging.debug('uptime: %s seconds, threads: %s',
                      CACHED['uptime'], threading.enumerate())

if __name__ == '__main__':
    if ARGS and ARGS[0] in COMMANDS:
        eval(ARGS[0])(*ARGS[1:])  # pylint: disable=eval-used
    else:
        logging.error('Must specify one of: %s', COMMANDS)
elif COMMAND == 'uwsgi':
    init()
    logging.warning('main process exiting, leaving daemon thread running')

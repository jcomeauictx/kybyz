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
CACHE = os.path.join(HOME, '.kybyz1')
CACHED = {'uptime': None}
KYBYZ_HOME = os.path.join(CACHE, 'home')
EXAMPLE = 'example.kybyz1'  # subdirectory with sample posts
KNOWN = ['post', 'netmeme', 'kybyz']  # known post types

def init():
    '''
    initialize application
    '''
    os.makedirs(KYBYZ_HOME, 0o700, exist_ok=True)
    CACHED['uptime'] = 0
    kybyz1 = threading.Thread(target=background, name='kybyz1')
    kybyz1.daemon = True
    kybyz1.start()

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
            posts = ['<div>kybyz1 active %s seconds</div>' % CACHED['uptime']]
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
    if os.listdir(KYBYZ_HOME):
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

if __name__ == '__main__' or COMMAND == 'uwsgi':
    init()
    logging.warning('main process exiting, leaving daemon thread running')

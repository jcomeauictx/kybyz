#!/usr/bin/python3
'''
Version 0.1 of Kybyz, a peer to peer (p2p) social media platform
'''
import sys, os, time, threading, logging  # pylint: disable=multiple-imports
from ircbot import IRCBot

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

COMMAND = sys.argv[0]
ARGS = sys.argv[1:]
logging.info('COMMAND: %s, ARGS: %s', COMMAND, ARGS)
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz1')
CACHED = {'uptime': None}
KYBYZ_HOME = os.path.join(CACHE, 'home')

def init():
    '''
    initialize application
    '''
    os.makedirs(CACHE, 0o700, exist_ok=True)
    CACHED['uptime'] = 0
    kybyz1 = threading.Thread(target=background, name='kybyz1')
    kybyz1.daemon = True
    kybyz1.start()

def serve(env=None, start_response=None):
    '''
    handle web requests
    '''
    page = None
    logging.debug('requested: %s', env.get('REQUEST_URI'))
    if env and start_response:
        if env['REQUEST_URI'] == '/':
            status = '200 OK'
            headers = [('Content-type', 'text/html')]
            page = '<div>kybyz1 active %s seconds</div>' % CACHED['uptime']
        else:
            status = '404 Not Found'
            headers = [('Content-type', 'text/html')]
            page = '<div>not yet implemented</div>'
        start_response(status, headers)
        return [page.encode()]
    logging.warning('serve: failing with env=%s and start_response=%s',
                    env, start_response)
    return None

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

#!/usr/bin/python3
'''
Version 0.1 of Kybyz, a peer to peer (p2p) social media platform
'''
import sys, os, time, threading  # pylint: disable=multiple-imports
from urllib.request import urlopen
from collections import namedtuple
from gnupg import GPG
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
COMMANDS = ['post', 'register', 'privmsg']

def init():
    '''
    initialize application
    '''
    os.makedirs(CACHE, 0o700, exist_ok=True)
    CACHED.update(registration()._asdict())
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

def registration():
    '''
    get and return information on user, if any

    assume only one key for user's email address, for now.
    we should probably pick the one with the latest expiration date.
    '''
    username = email = gpgkey = None
    if os.path.exists(KYBYZ_HOME):
        try:
            symlink = os.readlink(KYBYZ_HOME)
            username = os.path.split(symlink)[1]
            symlink = os.readlink(symlink)
            email = os.path.split(symlink)[1]
        except OSError:
            logging.exception('Bad registration')
        gpgkey = verify_key(email)
    return namedtuple('registration', ('username', 'email', 'gpgkey'))(
                      username, email, gpgkey)

def verify_key(email):
    '''
    fetch user's GPG key and make sure it matches given email address
    '''
    gpgkey = None
    if email:
        gpg = GPG()
        # pylint: disable=no-member
        verified = gpg.verify(gpg.sign('').data)
        if not verified.username.endswith('<' + email + '>'):
            raise ValueError('%s no match for GPG certificate %s' %
                             (email, verified.username))
        gpgkey = verified.key_id
    return gpgkey

def register(username=None, email=None):
    '''
    register kybyz account
    '''
    current = registration()  # see what we already have, if anything
    if username is None or email is None:
        logging.error('Usage: %s %s USERNAME EMAIL_ADDRESS',
                      COMMAND, ARGS[0])
        raise ValueError('Must specify desired username and email address')
    if any(current):
        if (username, email) != current[:2]:
            raise ValueError('Previously registered as %s %s' % current[:2])
        logging.warning('Already registered as %s %s', *current[:2])
    else:
        verify_key(email)
        os.makedirs(os.path.join(CACHE, email))
        os.symlink(os.path.join(CACHE, email), os.path.join(CACHE, username))
        os.symlink(os.path.join(CACHE, username), KYBYZ_HOME)
        logging.info('Now registered as %s %s', username, email)

def post(post_type, *args, **kwargs):
    '''
    make a new post from the command line or from another subroutine
    '''
    post_types = [subclass.classname for subclass in BasePost.__subclasses__()]
    if not post_type in post_types:
        raise ValueError('Unknown post type %s' % post_type)
    kwargs.update({'type': post_type})
    for arg in args:
        logging.debug('parsing %s', arg)
        kwargs.update(dict((arg.split('=', 1),)))
    return BasePost(None, **kwargs)

def privmsg(recipient, email, message):
    '''
    sign, encrypt, and send a private message to recipient

    `recipient` is the 'nick' (nickname) of the user to whom you wish to send
    the message. `email` is not necessarily an email address, but it used to
    find the GPG key of the recipient.
    '''
    gpg = GPG()
    signed = gpg.sign(message)
    encrypted = gpg.encrypt(signed.data, [email])  # pylint: disable=no-member
    CACHED['ircbot'].privmsg(recipient, encrypted.data)

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
    get_post = BasePost if to_html else read
    posts = [get_post(os.path.join(directory, filename))
             for filename in os.listdir(directory)]
    return list(filter(None, posts))

def background():
    '''
    load and maintain cache

    communicate with other kybyz servers
    '''
    delay = 600  # seconds
    CACHED['ircbot'] = IRCBot()
    while True:
        time.sleep(delay)  # releases the GIL for `serve`
        CACHED['uptime'] += delay
        logging.debug('CACHED: %s, threads: %s',
                      CACHED, threading.enumerate())

if __name__ == '__main__':
    if ARGS and ARGS[0] in COMMANDS:
        print(eval(ARGS[0])(*ARGS[1:]))  # pylint: disable=eval-used
    else:
        logging.error('Must specify one of: %s', COMMANDS)
elif COMMAND == 'uwsgi':
    init()
    logging.warning('main process exiting, leaving daemon thread running')

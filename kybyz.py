#!/usr/bin/python3
'''
Version 0.1 of Kybyz, a peer to peer (p2p) social media platform
'''
import sys, os, time, threading, cgi  # pylint: disable=multiple-imports
from socket import fromfd, AF_INET, SOCK_STREAM
from urllib.request import urlopen
from collections import namedtuple
from hashlib import md5
from ircbot import IRCBot
from kbutils import read, verify_key
from kbutils import send  # pylint: disable=unused-import
from kbcommon import CACHE, CACHED, KYBYZ_HOME, logging, MESSAGE_QUEUE, TO_PAGE
from post import BasePost

COMMAND = sys.argv[0]
ARGS = sys.argv[1:]
logging.info('COMMAND: %s, ARGS: %s', COMMAND, ARGS)
EXAMPLE = 'example.kybyz'  # subdirectory with sample posts
COMMANDS = ['post', 'register', 'send']
NAVIGATION = '<div class="column" id="kbz-navigation">{navigation}</div>'
POSTS = '''<div class="column" id="kbz-posts" data-version="{posts_hash}">
  {posts}
</div>'''
MESSAGES = '''<div class="column" id="kbz-messages"
  data-version="{messages_hash}">
    {messages}
  <div id="kbz-js-warning">
    webpage:ERROR:javascript disabled or incompatible
  </div>
</div>'''

def init():
    '''
    initialize application
    '''
    logging.debug('beginning kybyz initialization')
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
    # pylint: disable=too-many-locals, too-many-statements
    fields = cgi.FieldStorage(fp=env.get('wsgi.input'), environ=env)
    args = {k: fields[k].value for k in fields}
    logging.debug('args: %s', args)
    #sections = ['posts', 'messages']
    page = b'(Something went wrong)'
    env = env or {}
    requested = env.get('REQUEST_URI', None).lstrip('/')
    logging.debug('requested: "%s"', requested)
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    template = read('timeline.html').decode()
    messages = ''.join(['<div>%s</div>' % message for message in
                        reversed(MESSAGE_QUEUE)])
    messages_hash = md5(messages.encode()).hexdigest()
    messages = MESSAGES.format(messages=messages, messages_hash=messages_hash)
    posts = ''.join(['<div>%s</div>' % post for post in loadposts()])
    posts_hash = md5(posts.encode()).hexdigest()
    posts = POSTS.format(posts=posts, posts_hash=posts_hash)
    navigation = NAVIGATION.format(navigation=''.join(['&nbsp;']))

    # make helper functions for dispatcher
    def update():
        '''
        process xhr request for update to posts or messages
        '''
        name, hashed = args.get('name', None), args.get('hash', None)
        update_status = status  # default from outer variable
        if name in ('messages', 'posts'):
            # pylint: disable=eval-used
            # check outer variables
            # must be done before eval or it will fail
            logging.debug('messages: %s...', messages[:128])
            logging.debug('messages_hash: %s', messages_hash)
            logging.debug('posts: %s...', posts[:128])
            logging.debug('posts_hash: %s', posts_hash)
            if hashed and hashed != eval(name + '_hash'):
                update_page = eval(name).encode()
            elif hashed:
                logging.debug('%s unchanged', args['name'])
                update_page = b''
                update_status = '304 Not Modified'
            else:
                logging.error('no hash passed to /update/')
                update_page = b''
                update_status = '406 Not Acceptable'
        else:
            update_page = (
                            '<div>no updates for %s</div>' % args['name']
                          ).encode()
            update_status = '404 Not Found'
        return update_status, update_page

    if requested is not None and start_response:
        if requested == '':
            page = template.format(
                posts=posts,
                messages=messages,
                navigation=navigation,
                posts_hash=posts_hash,
                messages_hash=messages_hash,
            ).encode()
        elif os.path.exists(requested):
            page = read(requested)
            headers = [('Content-type', guess_mimetype(requested, page))]
        elif requested.startswith('update/'):
            status, page = update()
        elif requested.startswith('ipfs/'):
            with urlopen('https://ipfs.io/' + requested) as request:
                page = request.read()
                headers = [('Content-type', guess_mimetype(requested, page))]
        else:
            logging.warning('%s not found', requested)
            status = '404 Not Found'
            page = b'<div>not yet implemented</div>'
        # NOTE: page must be a bytestring at this point!
        logging.info('starting response with status %s and page %s...',
                     status, page[:128])
        start_response(status, headers)
        return [page] if page else None
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
        if CACHED.get('ircbot', None):
            CACHED['ircbot'].nick(username)
            CACHED['ircbot'].leave()  # rejoin to freshen CACHED['irc_id']
            CACHED['ircbot'].join()
        else:
            logging.info('registering outside of running application')

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
    delay = int(os.getenv('KB_DELAY') or 600)  # seconds
    CACHED['ircbot'] = IRCBot(nickname=CACHED.get('username', None))
    while True:
        logging.info('kybyz active %s seconds', CACHED['uptime'], **TO_PAGE)
        time.sleep(delay)  # releases the GIL for `serve`
        CACHED['uptime'] += delay
        logging.debug('CACHED: %s, threads: %s',
                      CACHED, threading.enumerate())

def process(args):
    '''
    process a kybyz command
    '''
    if args and args[0] in COMMANDS:
        print(eval(args[0])(*args[1:]))  # pylint: disable=eval-used
    elif args:
        logging.error('must specify one of: %s', COMMANDS)
    else:
        logging.info('no command received to process')

def uwsgi_init():
    '''
    initialize uwsgi application
    '''
    # pylint: disable=import-error, bad-option-value, import-outside-toplevel
    logging.debug('beginning kybyz uwsgi initialization')
    import uwsgi
    import webbrowser
    port = host = None
    try:
        port = fromfd(uwsgi.sockets[0], AF_INET, SOCK_STREAM).getsockname()[1]
        host = 'localhost:%s' % port
    except AttributeError:
        logging.exception('cannot determine port')
    init()
    if host is not None:  # if host is not None, port must also be set
        logging.debug('opening browser window to localhost port %s', port)
        webbrowser.open('http://%s' % host)
    else:
        logging.exception('cannot open browser on port %s', port)
    repl = threading.Thread(target=commandloop, name='repl')
    repl.daemon = True
    repl.start()
    logging.debug('uwsgi initialization complete')

def commandloop():
    '''
    simple repl (read-evaluate-process-loop) for command-line testing
    '''
    time.sleep(10)  # give page a chance to load before starting repl
    args = []
    logging.info('Ready to accept commands; `quit` to terminate input loop')
    while args[0:1] != ['quit']:
        try:
            print(process(args))
        except (RuntimeError, KeyError, ValueError, TypeError) as problem:
            logging.exception(problem)
        args = input('kbz> ').split()
    logging.warning('input loop terminated')

if __name__ == '__main__':
    process(args=ARGS)
elif COMMAND == 'uwsgi':
    uwsgi_init()

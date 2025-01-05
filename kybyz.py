#!/usr/bin/python3
'''
Version 0.1 of Kybyz, a peer to peer (p2p) social media platform
'''
# pylint: disable=bad-option-value, consider-using-f-string
import sys, os, math, time, threading  # pylint: disable=multiple-imports
import shlex, re, subprocess  # pylint: disable=multiple-imports
from socket import fromfd, AF_INET, SOCK_STREAM
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import parse_qsl
from hashlib import md5
from ircbot import IRCBot
from kbutils import loadposts, registration, cache, guess_mimetype
from kbutils import send, publish, post  # pylint: disable=unused-import
from kbutils import register  # pylint: disable=unused-import
from kbcommon import CACHE, CACHED, logging, MESSAGE_QUEUE, TO_PAGE
from kbcommon import COMMAND, ARGS, read

RUNNING = threading.Event()
CURDIR = os.path.abspath(os.curdir)
REQUEST_COUNT = 0
LOGTIME = int(os.getenv('KB_DELAY', '600'))  # seconds
COMMANDS = ['post', 'register', 'send', 'publish']
NAVIGATION = '<div class="column" id="kbz-navigation">{navigation}</div>'
POSTS = '''<div class="column" id="kbz-posts" data-version="{posts_hash}">
  {posts}
</div>'''
MESSAGES = '''<div class="column" id="kbz-messages"
  data-version="{messages_hash}">
    {messages}
  <div id="kbz-js-warning">webpage:{javascript}</div>
</div>'''
EXPECTED_ERRORS = (  # for repl loop
    RuntimeError,
    KeyError,
    ValueError,
    TypeError,
    AttributeError
)
USER_AGENT = os.getenv(
    'USER_AGENT',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0'
)
REMOTE_PORT = int(os.getenv('EXTERNAL_PORT', '-1'))  # request via nginx/tor

def init():
    '''
    initialize application
    '''
    logging.debug('beginning kybyz initialization')
    os.makedirs(CACHE, 0o700, exist_ok=True)
    CACHED.update(registration()._asdict())
    if not CACHED['gpgkey']:
        username = os.getenv('KB_USERNAME', None)
        email = os.getenv('KB_EMAIL', None)
        if username and email:
            register(username, email)
            CACHED.update(registration()._asdict())
        else:
            logging.error('need to set envvars KB_USERNAME and KB_EMAIL')
    CACHED['uptime'] = 0
    CACHED['javascript'] = 'ERROR:javascript disabled or incompatible'
    logging.debug('CACHED: %s', CACHED)
    RUNNING.set()
    kybyz = threading.Thread(target=background, name='kybyz', daemon=True)
    kybyz.start()
    external_server = threading.Thread(target=nginx, name='nginx', daemon=True)
    external_server.start()
    punchthrough = threading.Thread(target=tor, name='tor', daemon=True)
    punchthrough.start()

def serve(env=None, start_response=None):
    '''
    handle web requests
    '''
    # pylint: disable=too-many-locals, too-many-statements
    global REQUEST_COUNT  # pylint: disable=global-statement
    REQUEST_COUNT += 1
    env = env or {}
    if REQUEST_COUNT < 1000000:
        logging.debug('env: %s', env)
    # wsgi.input now (as of 2024-12-30 or before) returns bytes object
    wsgi_input = env.get('wsgi.input', BytesIO(b'')).read().decode()
    logging.debug('wsgi.input: %s', wsgi_input)
    args = dict(parse_qsl(wsgi_input))
    logging.debug('args: %s', args)
    page = b'(Something went wrong)'
    requested = env.get('REQUEST_URI', None).lstrip('/')
    server_port = int(env.get('SERVER_PORT', '0'))
    logging.debug('requested: "%s"', requested)
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    template = read('timeline.html').decode()
    messages = ''.join(['<div>%s</div>' % message for message in
                        reversed(MESSAGE_QUEUE)])
    messages_hash = md5(messages.encode()).hexdigest()
    messages = MESSAGES.format(
        messages=messages,
        messages_hash=messages_hash,
        javascript=CACHED['javascript'])
    posts = ''.join(['<div>%s</div>' % post for post in loadposts()])
    posts_hash = md5(posts.encode()).hexdigest()
    posts = POSTS.format(posts=posts, posts_hash=posts_hash)
    navigation = NAVIGATION.format(navigation=''.join(['<h3>Navigation</h3>']))

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
            logging.debug('messages: ...%s', messages[-128:])
            logging.debug('messages_hash: %s', messages_hash)
            logging.debug('posts: %s...', posts[:128])
            logging.debug('posts_hash: %s', posts_hash)
            if hashed and hashed != eval(name + '_hash'):
                update_page = eval(name).encode()
            elif hashed:
                logging.debug('%s unchanged', name)
                update_page = b''
                update_status = '304 Not Modified'
            else:
                logging.error('no hash passed to /update/')
                update_page = b''
                update_status = '406 Not Acceptable'
        else:
            update_page = (
                '<div>no updates for %s</div>' % name
            ).encode()
            update_status = '404 Not Found'
        return update_status, update_page

    if requested is not None and start_response:
        if server_port == REMOTE_PORT:
            logging.warning('remote request received, env: %s', env)
            status = '501 Not Implemented'
            page = b'<div>Not yet serving remote requests</div>'
        elif requested == '':
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
            # assume called by javascript, and thus that it's working
            CACHED['javascript'] = 'INFO:found compatible javascript engine'
            status, page = update()
        elif requested.startswith('ipfs/'):
            url = 'https://ipfs.io/' + requested
            urlrequest = Request(url)
            urlrequest.add_header('user-agent', USER_AGENT)
            logging.debug('fetching uncached ipfs URL %s', url)
            try:
                with urlopen(urlrequest) as request:
                    page = request.read()
                    headers = [
                        ('Content-type', guess_mimetype(requested, page))
                    ]
                cache(requested, page)
            except HTTPError as failed:
                headers = failed.headers.items()
                status = ' '.join([str(failed.code), failed.msg])
                logging.warning('failed fetching %s: %s, %r',
                                url, status, headers)
                page = b'<div>%s</div>' % status.encode()
        else:
            logging.warning('%s not found', requested)
            status = '404 Not Found'
            page = b'<div>not yet implemented</div>'
        # NOTE: page must be a bytestring at this point!
        logging.debug('starting response with status %s and page %s...',
                      status, page[:128])
        start_response(status, headers)
        return [page]
    logging.warning('serve: failing with env=%s and start_response=%s',
                    env, start_response)
    return [b'']

def get_posts(directory, pattern=None, convert=None):
    '''
    get list of posts

    we use only those symlinked to by unadorned hashes
    '''
    pattern = re.compile(pattern or '^kbz[0-9A-Za-z]*$')
    filenames = [os.path.join(directory, filename)
                 for filename in os.listdir(directory)]
    convert = convert or str  # or specify convert=os.path.realpath
    return [convert(filename)
            for filename in filenames
            if os.path.islink(filename) and pattern.match(filename)]

def background():
    '''
    load and maintain cache

    communicate with other kybyz servers
    '''
    CACHED['ircbot'] = IRCBot(nickname=CACHED.get('username', None))
    # delay must be less than nginx's, and more than 1s
    # (otherwise the `kybyz active %s seconds` display will be doubled)
    delay = 1.1
    while RUNNING.is_set():
        if math.floor(CACHED['uptime']) % LOGTIME == 0:
            logging.info('kybyz active %s seconds',
                         math.floor(CACHED['uptime']), **TO_PAGE)
            logging.debug('CACHED: %s, threads: %s',
                          CACHED, threading.enumerate())
        time.sleep(delay)  # releases the GIL for `serve`
        CACHED['uptime'] += delay
    logging.warning('program stopped, cleaning up...')

def nginx():
    '''
    start nginx to handle external requests via tor
    '''
    # pylint: disable=consider-using-with
    configuration = os.path.join(CURDIR, 'kybyz.conf')
    subprocess.Popen([
        'nginx',
        '-c', configuration,
        '-e', 'stderr',
        '-g', 'daemon off;'
    ])
    while RUNNING.is_set():
        time.sleep(1.3)  # must be less than tor's
    logging.warning('program stopped, nginx terminating...')

def tor():
    '''
    start tor for receiving external requests
    '''
    # pylint: disable=consider-using-with
    subprocess.Popen(['tor', '-f', 'kybyz.torrc'])
    while RUNNING.is_set():
        time.sleep(1.5)
    logging.warning('program stopped, tor terminating...')

def process(args):
    '''
    process a kybyz command
    '''
    if args and args[0] in COMMANDS:
        print(
            ('result of %s%s:' % (args[0], str(tuple(args[1:])))),
            eval(args[0])(*args[1:]) # pylint: disable=eval-used
    )
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
    if os.getenv('ANDROID_ROOT') is None:
        import webbrowser
    else:
        webbrowser = type(
            '',
            (),
            {'open': lambda url: subprocess.call(['am', 'start', url])}
        )
    port = host = None
    try:
        port = fromfd(uwsgi.sockets[0], AF_INET, SOCK_STREAM).getsockname()[1]
        host = 'kybyz:%s' % port
    except AttributeError:
        logging.exception('cannot determine port')
    init()
    if not sys.stdin.isatty():
        logging.info('running as background process, will not launch browser')
    else:
        if host is not None and not os.getenv('WSL'):
            logging.debug('opening browser window to %s', host)
            webbrowser.open('http://%s' % host)
        else:
            logging.exception('cannot open browser to %s', host)
            logging.info("if you're running under WSL (Windows Subsystem for"
                         " Linux), just open Windows browser to %s", host)
    repl = threading.Thread(target=commandloop, name='repl', daemon=True)
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
            print(('process%s:' % str(tuple(args))), process(args))
            args = shlex.split(input('kbz> '))
        except EXPECTED_ERRORS:
            logging.exception('command failed, please try again')
            args[:] = []
        except EOFError:
            break
    logging.warning('input loop terminated')

if __name__ == '__main__':
    init()
    process(args=ARGS)
elif COMMAND == 'uwsgi':
    uwsgi_init()
elif COMMAND not in ('pydoc3', 'doctest'):
    logging.info('initalizing on command %s', COMMAND)
    init()

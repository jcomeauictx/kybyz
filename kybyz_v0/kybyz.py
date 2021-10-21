#!/usr/bin/python3
'''
implement local website http://kybyz/

Copyright 2015-2016 John Otis Comeau <jc@unternet.net>
distributed under the terms of the GNU General Public License Version 3
(see COPYING)

automatically uploads to and downloads from kybyz.com to populate the
local website.

must first mate a local IP address with the name `kybyz` in /etc/hosts, e.g.:

127.0.1.125 kybyz
'''
from __future__ import print_function
import sys, os, logging, pwd, subprocess, site, cgi, html
site.main()
logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logging.debug('os.getuid(): %s', os.getuid())
logging.debug('os.geteuid(): %s', os.geteuid())
logging.debug('site.ENABLE_USER_SITE: %s', site.ENABLE_USER_SITE)
logging.debug('site.USER_SITE: %s', site.USER_SITE)
logging.debug('sys.path: %s', sys.path)
import rsa
from markdown import markdown
try:  # command-line testing won't have module available
    import uwsgi
except ImportError:
    uwsgi = type('uwsgi', (), {'opt': {}})  # object with empty opt attribute
logging.debug('uwsgi.opt: %s' % repr(uwsgi.opt))
MAXLENGTH = 1024 * 1024  # maximum size in bytes of markdown source of post
HOMEDIR = pwd.getpwuid(os.getuid()).pw_dir
DATADIR = uwsgi.opt.get('check_static', os.path.join(HOMEDIR, '.kybyz_v0'))
THISDIR = os.path.dirname(sys.argv[0]) or os.path.abspath('.')
EXAMPLE = uwsgi.opt.get('check_static', os.path.join(THISDIR, 'example.kybyz'))
logging.debug('HOMEDIR: %s' % HOMEDIR)
logging.debug('USER_SITE: %s' % site.USER_SITE)
USER_CONFIG = os.path.join(HOMEDIR, 'etc', 'kybyz')
PRIVATE_KEY = os.path.join(USER_CONFIG, 'kybyz.private.pem')
PUBLIC_KEY = os.path.join(USER_CONFIG, 'kybyz.public.pem')
MIMETYPES = {'png': 'image/png', 'ico': 'image/x-icon', 'jpg': 'image/jpeg',
             'jpeg': 'image/jpeg', 'pdf': 'application/pdf'}
FILETYPES = [
    'directory',
    'md',
    'url',
    'txt',
    'html',
    'css',
] + list(MIMETYPES.keys())

class Node(str):
    '''
    a Node is either a category or an action item (goal, task, etc.)

    nodes must be named as follows:

    if a directory, it can be a singleton, e.g. '.kybyz' or 'goals'
    it can also be a word followed by an attribute, e.g. 'jogging.accomplished'

    if a file, it can be in two or 3 parts.
    the final part should always be a filetype, e.g. 'jogging.html'
    a middle part can be added as an attribute, e.g. 'house.accomplished.md'
    '''
    # class attributes
    root = None  # filled in during __init__()

    def __new__(cls, parent_node, filename):
        '''
        create a new Node object
        '''
        parts = os.path.basename(filename).split('.')
        name = parts[0]  # .kybyz will be ''
        # obviously there can be only one .hidden name in a directory
        try:
            siblings = parent_node.attributes['children']
        except (KeyError, AttributeError):
            siblings = []
        if name in siblings:
            logging.info('Returning pre-existing node %s', name)
            node = siblings[siblings.index(name)]
        else:
            node = super(Node, cls).__new__(cls, name)
        return node

    def __init__(self, parent_node, filename):
        '''
        initialize the current node, which may have already been initialized

        so we can't just assume, e.g., that we can set self.children = []

        names must be in 2 or 3 parts, e.g.:

        mygoal.md: a markdown file for "mygoal"
        mygoal.accomplished: a directory for accomplishments of mygoal
        mygoal.related.md: a file for other nodes related to "mygoal"
        '''
        logging.debug('Node.__init__(%s, %s)', parent_node, filename)
        parts = os.path.basename(filename).split('.')
        self.filename = filename
        self.attributes = {}
        self.name = parts[0]
        attribute = parts[1] if len(parts) > 1 else None
        filetype = 'directory' if os.path.isdir(filename) else parts[-1]
        if parent_node is None:
            attribute = None
            if not os.path.isdir(filename):
                raise(AttributeError('root filename must be directory'))
            filetype = 'directory'
            Node.root = self  # set class attribute
            self.parent = self
            self.attributes['children'] = self.attributes.get('children', [])
            logging.debug('initialized root node')
        elif os.path.isdir(filename):
            self.parent = parent_node
            if not self in parent_node.attributes['children']:
                parent_node.attributes['children'].append(self)
            self.attributes['children'] = self.attributes.get('children', [])
        else:
            self.parent = parent_node
            if not self in parent_node.attributes['children']:
                parent_node.attributes['children'].append(self)
        if filetype not in FILETYPES:
            if attribute != filetype:
                raise(ValueError('Unknown filetype: "%s"' % filetype))
            elif not os.path.isdir(filename):
                logging.error('%s does not have filetype extension', filename)
                raise(TypeError('Path without extension must be directory'))
            else:
                attribute = None  # e.g. running.md or mygoal.html
        if attribute and filetype == 'directory':
            files = listdir(filename)
            header, trailer = None, None
            if 'header.html' in files:
                header = files.pop(files.index('header.html'))
            if 'trailer.html' in files:
                trailer = files.pop(files.index('trailer.html'))
            self.attributes[attribute] = []
            if header:
                self.attributes[attribute].append(render(header))
            self.attributes[attribute].extend([render(f)[0] for f in files])
            if trailer:
                self.attributes[attribute].append(render(trailer))
        elif attribute:
            self.attributes[attribute] = [render(filename)[0]]
        if parent_node is None:
            self.root = self  # class attribute
            self.parent = self

def kybyz_client(env = None, start_response = None):
    '''
    primary client process, shows contents of $HOME/.kybyz_v0
    '''
    logging.debug('env: %s' % repr(env))
    start = DATADIR
    logging.debug('start: %s' % start)
    private, public = load_keys()
    path = (env.get('HTTP_PATH', env.get('REQUEST_URI', '/'))).lstrip('/')
    if not path:
        mimetype = 'text/html'
        page = makepage(start, [], [])
    else:
        page, mimetype = render(path)
        logging.debug('mimetype: %s', mimetype)
    start_response('200 groovy', [('Content-type', mimetype)])
    return page

def example_client(env = None, start_response = None):
    '''
    testing client process, shows contents of $PWD/example.kybyz/
    '''
    logging.debug('env: %s', repr(env))
    start = EXAMPLE
    logging.debug('start: %s', start)
    private, public = load_keys()
    path = (env.get('HTTP_PATH', env.get('REQUEST_URI', '/'))).lstrip('/')
    if not path:
        mimetype = 'text/html'
        page = buildpage(start)
    else:
        page, mimetype = render(path)
    start_response('200 groovy', [('Content-type', mimetype)])
    return [page]

def listdir(directory):
    '''
    os.listdir() but returns full path of each file
    '''
    return [os.path.join(directory, f) for f in os.listdir(directory)]

def pushdir(stack, directory):
    '''
    implementation of MSDOS `pushd`
    '''
    stack.append(directory)
    logging.debug('stack after `pushdir` now: %s' % stack)
    os.chdir(directory)

def popdir(stack):
    '''
    implementation of MSDOS `popd`
    '''
    stack.pop(-1)
    logging.debug('stack after `popdir` now: %s'% stack)
    os.chdir('..')

def render(pagename):
    '''
    Return content with Content-type header

    If it's markdown, we assume it's a post and will wrap it with
    <div class="post">, but if it's HTML we can't assume anything as
    it could be the header or footer or something else. So if you're using
    HTML for a post, wrap it yourself.
    '''
    if pagename.endswith('.md'):
        logging.debug('running markdown on %s', pagename)
        return postwrap(markdown(read(pagename),
                        extensions=['fenced_code']).encode()), 'text/html'
    elif pagename.endswith('.html'):
        logging.debug('rendering %s as html', pagename)
        return read(pagename, raw=True), 'text/html'
    elif not pagename.endswith(('.pdf', '.png', '.ico', '.jpg', '.jpeg')):
        logging.debug('rendering %s as plain text', pagename)
        return ('<div class="post">%s</div>' % html.escape(
            read(pagename)), 'text/plain').encode()
    else:
        logging.debug('rendering %s using its mimetype', pagename)
        return (read(pagename, raw=True),
                MIMETYPES[os.path.splitext(pagename)[1][1:]])

def buildpage(directory=DATADIR):
    '''
    Rewrite of `makepage` using Node
    
    Note that this constructs Nodes out of the same path more than once,
    which is why Node.__new__ has to return an existing node when found.
    '''
    parent = None
    page = ''
    for dirpath, dirnames, filenames in os.walk(directory):
        node = Node(parent, dirpath)
        parent = node
        for entry in dirnames + filenames:
            subnode = Node(parent, os.path.join(dirpath, entry))
    for node in walk(Node.root):
        logging.debug('node: %r', node[:50])
        page += str(node)
    return page

def walk(node):
    '''
    Like os.walk, but for Node objects

    http://stackoverflow.com/a/3010038/493161
    '''
    yield node
    for attribute in getattr(node, 'attributes', {}):
        for child in node.attributes[attribute]:
            for entry in walk(child):
                yield entry

def makepage(directory=DATADIR, output=None, level=None):
    '''
    Scan folders and files to build the Kybyz page
    '''
    logging.debug('running `makepage` on %s' % directory)
    output, level = output if output else [], level if level else []
    pushdir(level, directory)
    posts = specialsort(os.listdir('.'))
    logging.debug('posts: %s' % posts)
    for post in posts:
        page = []
        if post.startswith('.'):
            '''
            files and directories with a special meaning
            '''
            if post.startswith('.accomplished'):
                '''
                an '.accomplished' *directory* means it contains steps to
                accomplishment; an '.accomplished' *file* means it is *done*.
                '''
                if os.path.isdir(post):
                    logging.debug('task %s has accomplishment activity',
                                  level[-1])
                else:
                    logging.debug('goal %s has been accomplished', level[-1])
                page.append('&#x2713;')
        elif not os.path.isdir(post):
            page.append(render(post)[0])
        else:
            headerlevel = len(level) + 1 # <h2> and higher
            page.append(postwrap(True))
            page.append('<h%d>%s</h%d>' % (headerlevel, post, headerlevel))
            page += makepage(post, [], level)
            page.append(postwrap(False))
        logging.debug('page: "%s"', page) 
        output += page
    logging.debug('output: "%r"', output)
    popdir(level)
    return output

def postwrap(something):
    '''
    Encapsulate post in DIV tags.

    Works one-shot with a string, or in 2 steps by passing in True (open)
    or False (close)
    '''
    if isinstance(something, int):  # expecting True (1) or False (0)
        return [b'</div>', b'<div class="post">'][something]
    else:
        return b'<div class="post">%s</div>' % something

def specialsort(listing):
    '''
    sort files first, then subdirectories

    (and/or any other method that makes sense as we progress
    note that symlinks will also be identified properly as files or dirs
    '''
    subdirs = list(filter(os.path.isdir, listing))
    files = list(filter(os.path.isfile, listing))
    if set(listing) != set(subdirs + files):
        raise ValueError('%s != %s' % (listing, subdirs + files))
    return sorted(files) + sorted(subdirs)

def read(filename, maxread = MAXLENGTH, raw=False):
    '''
    return contents of a file, closing it properly
    '''
    decoded = None
    try:
        infile = open(filename, 'rb')
        data = infile.read(MAXLENGTH)
        infile.close()
        if not raw:
            try:
                decoded = data.decode('utf8')
            except UnicodeDecodeError:
                decoded = data.decode('latin1')
    except IOError:
        message = ('File %s was not found relative to %s' %
                   (filename, os.path.abspath(os.curdir)))
        logging.error(message)
        decoded = message
    return decoded or data

def load_keys():
    '''
    load client keys, aborting if not already created

    note: key creation takes *forever* (or overnight anyway) on a slow
    computer. if you have openssl installed, use the Makefile to
    `make keys`
    '''
    try:
        private = rsa.PrivateKey.load_pkcs1(read(PRIVATE_KEY))
    except IOError:
        raise Exception('First create keys using `make kybyz.public.key`')
    try:
        public = rsa.PublicKey.load_pkcs1(read(PUBLIC_KEY))
    except ValueError:
        public = rsa.PublicKey.load_pkcs1_openssl_pem(read(PUBLIC_KEY))
    return private, public

if __name__ == '__main__':
    print('\n'.join(example_client(os.environ, lambda *args: None)))

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

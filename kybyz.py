#!/usr/bin/python
'''
implement local website http://kybyz/

Copyright 2015 John Otis Comeau <jc@unternet.net>
distributed under the terms of the GNU General Public License Version 3
(see COPYING)

automatically uploads to and downloads from kybyz.com to populate the
local website.

must first mate a local IP address with the name `kybyz` in /etc/hosts, e.g.:

127.0.1.125 kybyz
'''
import sys, os, urllib2, logging, pwd, subprocess, site
from markdown import markdown
if not sys.stdin.isatty():  # command-line testing won't have module available
    import uwsgi
else:
    uwsgi = type('', (), dict(opt = {}))  # object with empty opt attribute
logging.basicConfig(level = logging.DEBUG)
MAXLENGTH = 4096  # maximum size in bytes of markdown source of post
HOMEDIR = pwd.getpwuid(os.getuid()).pw_dir
logging.debug('HOMEDIR: %s' % HOMEDIR)
logging.debug('USER_SITE: %s' % site.USER_SITE)
USER_CONFIG = os.path.join(HOMEDIR, 'etc', 'kybyz')
PRIVATE_KEY = os.path.join(USER_CONFIG, 'kybyz.private.pem')
PUBLIC_KEY = os.path.join(USER_CONFIG, 'kybyz.public.pem')
try:
    import rsa
except ImportError:
    subprocess.check_call(['pip', 'install', '--user', 'rsa'])
    import rsa

def kybyz_client(env = None, start_response = None):
    '''
    primary client process, shows contents of $HOME/.kybyz
    '''
    debug('env: %s' % repr(env))
    debug('uwsgi.opt: %s' % repr(uwsgi.opt))
    start = uwsgi.opt.get('check_static', os.path.join(HOMEDIR, '.kybyz'))
    debug('start: %s' % start)
    start_response('200 groovy', [('Content-type', 'text/html')])
    private, public = load_keys()
    return makepage(start, [], [])

def example_client(env = None, start_response = None):
    '''
    testing client process, shows contents of $PWD
    '''
    debug('env: %s' % repr(env))
    debug('uwsgi.opt: %s' % repr(uwsgi.opt))
    cwd = os.path.dirname(sys.argv[0]) or os.path.abspath('.')
    start = uwsgi.opt.get('check_static', os.path.join(cwd, 'example.kybyz'))
    debug('cwd: %s, start: %s' % (cwd, start))
    start_response('200 groovy', [('Content-type', 'text/html')])
    return makepage(start, [], [])

def pushdir(stack, directory):
    '''
    implementation of MSDOS `PUSHD`
    '''
    stack.append(directory)
    debug('stack after `pushdir` now: %s' % stack)
    os.chdir(directory)

def popdir(stack):
    '''
    implementation of MSDOS `popd`
    '''
    stack.pop(-1)
    debug('stack after `popdir` now: %s'% stack)
    os.chdir('..')

def makepage(directory, output, level):
    debug('running `makepage` on %s' % directory)
    pushdir(level, directory)
    posts = specialsort(os.listdir('.'))
    debug('posts: %s' % posts)
    for post in posts:
        page = []
        if post.endswith('.md'):
            debug('running markdown on %s' % post)
            page.append(postwrap(markdown(read(post)).encode('utf8')))
        elif post.endswith('.html'):
            '''
            cannot use postwrap here, this could be header or trailer
            must use markdown for proper post wrapping, or add your own
            <div class="post"> tags to HTML'''
            page.append(read(post))
        elif os.path.isdir(post):
            headerlevel = len(level) + 1 # <h2> and higher
            page.append(postwrap(True))
            page.append('<h%d>%s</h%d>' % (headerlevel, post, headerlevel))
            page += makepage(post, [], level)
            page.append(postwrap(False))
        debug('page: "%s"' % page) 
        output += page
    debug('output: "%s"' % (' '.join(output)).replace('\n', ' '))
    popdir(level)
    return output

def postwrap(something):
    if isinstance(something, int):  # expecting True (1) or False (0)
        return ['</div>', '<div class="post">'][something]
    else:
        return '<div class="post">%s</div>' % something

def specialsort(listing):
    '''
    sort files first, then subdirectories

    (and/or any other method that makes sense as we progress
    note that symlinks will also be identified properly as files or dirs
    '''
    subdirs = filter(os.path.isdir, listing)
    files = filter(os.path.isfile, listing)
    if set(listing) != set(subdirs + files):
        raise ValueError('%s != %s' % (listing, subdirs + files))
    return sorted(files) + sorted(subdirs)

def read(filename, maxread = MAXLENGTH):
    '''
    return contents of a file, closing it properly
    '''
    infile = open(filename)
    data = infile.read(MAXLENGTH)
    infile.close()
    return data

def write(filename, data):
    '''
    write data to a file, closing it properly
    '''
    outfile = open(filename, 'w')
    outfile.write(data)
    outfile.close()

def debug(message = None):
    if __debug__:
        if message:
            logging.debug(message)
        return True

def load_keys():
    '''
    load client keys, creating them if necessary

    note: key creation takes *forever* (or overnight anyway) on a slow
    computer. if you have openssl installed, use the Makefile to
    `make kybyz.public.key'
    '''
    try:
        private = rsa.PrivateKey.load_pkcs1(read(PRIVATE_KEY))
    except IOError:
        public, private = rsa.newkeys(MAXLENGTH)
        write(PRIVATE_KEY, private.save_pkcs1())
        write(PUBLIC_KEY, public.save_pkcs1())
    try:
        public = rsa.PublicKey.load_pkcs1(read(PUBLIC_KEY))
    except ValueError:
        public = rsa.PublicKey.load_pkcs1_openssl_pem(read(PUBLIC_KEY))
    return private, public

if __name__ == '__main__':
    print '\n'.join(example_client(os.environ, lambda *args: None))

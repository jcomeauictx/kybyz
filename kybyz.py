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
import sys, os, urllib2, logging, pwd, subprocess
from markdown import markdown
try:
    import rsa
except ImportError:
    subprocess.check_call(['pip', 'install', '--user', 'rsa'])
    import rsa
logging.basicConfig(level = logging.DEBUG)
MAXLENGTH = 4096  # maximum size in bytes of markdown source of post
HOMEDIR = pwd.getpwuid(os.geteuid()).pw_dir
USER_CONFIG = os.path.join(HOMEDIR, 'etc', 'kybyz')
PRIVATE_KEY = os.path.join(USER_CONFIG, 'kybyz.private.pem')
PUBLIC_KEY = os.path.join(USER_CONFIG, 'kybyz.public.pem')

def kybyz_client():
    output = []
    os.chdir(os.path.join(HOMEDIR, '.kybyz'))
    posts = sorted(os.listdir('.'))
    debug('posts: %s' % posts)
    for post in posts:
        if post.endswith('.md'):
            debug('running markdown on %s' % post)
            page = markdown(read(post)).encode('utf8')
        elif post.endswith(('.htm', '.html')):
            page = read(post)
        debug('page: "%s"' % (' '.join(page.split())))
        output.append(page)
    debug('output: "%s"' % (' '.join(output).replace('\n', ' ')))
    return output

def read(filename, maxread = MAXLENGTH):
    '''
    return contents of a file, closing it properly
    '''
    infile = open(filename)
    data = infile.read(MAXLENGTH)
    infile.close()
    return data

def client(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return kybyz_client()

def debug(message = None):
    if __debug__:
        if message:
            logging.debug(message)
        return True

def load_keys():
    '''
    load client keys, creating them if necessary
    '''
    private = rsa.PrivateKey.load_pkcs1(read(PRIVATE_KEY), 'PEM')
    public = rsa.PublicKey.load_pkcs1(read(PUBLIC_KEY), 'PEM')

if __name__ == '__main__':
    print '\n'.join(kybyz_client())

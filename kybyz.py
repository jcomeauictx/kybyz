#!/usr/bin/python
'''
implement local website http://kybyz/

automatically uploads to and downloads from kybyz.com to populate the
local website.

must first mate a local IP address with the name `kybyz` in /etc/hosts, e.g.:

127.0.1.125 kybyz
'''
import sys, os, urllib2, logging, pwd
from markdown import markdown
MAXLENGTH = 4096  # maximum size in bytes of markdown source of post
logging.basicConfig(level = logging.DEBUG)

def kybyz():
    output = []
    os.chdir(os.path.join(pwd.getpwuid(os.geteuid()).pw_dir, '.kybyz'))
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

def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return kybyz()

def debug(message = None):
    if __debug__:
        if message:
            logging.debug(message)
        return True

if __name__ == '__main__':
    print '\n'.join(kybyz())

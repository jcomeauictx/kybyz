#!/usr/bin/python3
'''
Kybyz utilities
'''
import os, re, subprocess, json  # pylint: disable=multiple-imports
from hashlib import sha256
from base58 import b58encode, b58decode
from canonical_json import canonicalize
from kbcommon import CACHE, CACHED, EXAMPLE, KYBYZ_HOME, COMMAND, ARGS, logging
from kbcommon import REGISTRATION, read, CHANNEL, POSTS_QUEUE, JSON
from post import BasePost

try:
    from gnupg import GPG
except ImportError:
    from kbgpg import GPG

def kbhash(message):
    '''
    return base58 of sha256 hash of message, with prefix 'kbz'

    >>> kbhash({'test': 0})
    'kbz6cd8vvJh7zja18Nju1GTuCNKqhDdFo7RCWvVbjHyqEuv'
    '''
    prefix = b'\x07\x88\xcc'  # when added to 32-byte string produces 'kbz'
    canonical = canonicalize(message).encode()
    hashed = sha256(canonical).digest()
    return b58encode(prefix + hashed).decode()

def verify_key(email):
    '''
    fetch user's GPG key and make sure it matches given email address
    '''
    gpgkey = None
    gpg = GPG()
    # pylint: disable=no-member
    verified = gpg.verify(gpg.sign('', keyid=email).data)
    logging.debug('verified: %s', verified)
    if not verified.username.endswith('<' + email + '>'):
        raise ValueError('%s no match for GPG certificate %s' %
                         (email, verified.username))
    gpgkey = verified.key_id
    return gpgkey

def publish(post_id, publish_to='all'):
    '''
    send post out to network

    unencrypted if to='all', otherwise encrypted to each recipient with
    their own keys
    '''
    posts = find_posts(KYBYZ_HOME, post_id)
    post_count = len(posts)
    if post_count != 1:
        raise ValueError('No posts matching %r' % post_id if post_count == 0
                         else 'Ambiguous suffix %r matches %s' % (
                             posts))
    recipients = publish_to.split(',')
    for recipient in recipients:
        logging.debug('recipient: %s', recipient)
        if recipient == 'all':
            send(CHANNEL, '-', read(posts[0]))
        else:
            send(recipient, recipient, read(posts[0]))

def send(recipient, email, *words):
    '''
    encrypt, sign, and send a private message to recipient

    `recipient` is the 'nick' (nickname) of the user to whom you wish to send
    the message. `email` is not necessarily an email address, but is used to
    find the GPG key of the recipient.

    use `-` instead of email to send plain text
    '''
    if len(words) > 1 or isinstance(words[0], str):
        text = ' '.join(words).encode()
    else:
        text = words[0]  # as when called by `publish`
    logging.debug('words: %s', words)
    encoded = None
    if email != '-':
        gpg = GPG()
        logging.debug('message before encrypting: %s', text)
        encrypted = gpg.encrypt(
            text,  # pylint: disable=no-member
            [email],
            sign=True,
            armor=False)
        logging.debug('encrypted: %r...', encrypted.data[:64])
        encoded = b58encode(encrypted.data).decode()
        logging.debug('encoded: %s', encoded)
    if text and not encoded:
        if email == '-' or os.getenv('KB_SEND_PLAINTEXT_OK'):
            logging.warning('encryption %s, sending plaintext',
                            'bypassed' if email == '-' else 'failed')
            encoded = text.decode()
        else:
            logging.warning('encryption failed, run with '
                            'KB_SEND_PLAINTEXT_OK=1 to send anyway')
            logging.warning('setting message to "(encryption failed)"')
            encoded = '(encryption failed)'
    CACHED['ircbot'].privmsg(recipient, encoded)

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
    return REGISTRATION(username, email, gpgkey)

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

def post(post_type, *args, returned='hashed', **kwargs):
    '''
    make a new post from the command line or from another subroutine
    '''
    if post_type:
        kwargs.update({'type': post_type})
    if len(args) == 1 and JSON.match(args[0]):
        try:
            kwargs.update(json.loads(args[0]))
        except json.decoder.JSONDecodeError:
            logging.error('Post not valid JSON format: %s' % args[0])
    else:
        logging.debug('args %s not valid JSON, using as key-value pairs', args)
        for arg in args:
            logging.debug('parsing %s', arg)
            kwargs.update(dict((arg.split('=', 1),)))
    try:
        newpost = BasePost(None, **kwargs)
        jsonified = newpost.to_json()
        post_type = newpost.type
        hashed = kbhash(jsonified)
        cached = cache('.'.join((hashed, post_type)), jsonified)
        jsonified = newpost.to_json(for_hashing=True)
        hashed = kbhash(jsonified)
        hashcached = cache('.'.join((hashed, post_type)), jsonified)
        unadorned = os.path.splitext(hashcached)[0]
        try:
            os.symlink(cached, unadorned)
        except FileExistsError:
            existing = os.readlink(unadorned)
            if existing != cached:
                logging.warning('updating post %s to %s', unadorned, cached)
                os.unlink(unadorned)
                os.symlink(cached, unadorned)
            else:
                logging.debug('%s already symlinked to %s', unadorned, cached)
        return hashed if returned == 'hashed' else newpost
    except AttributeError:
        logging.exception('Post failed')
        return None

def cache(path, data):
    '''
    store data in cache for later retrieval
    '''
    fullpath = os.path.realpath(os.path.join(KYBYZ_HOME, path))
    if not fullpath.startswith(os.path.realpath(KYBYZ_HOME) + os.sep):
        raise ValueError('Attempt to write %s outside of app bounds' % fullpath)
    os.makedirs(os.path.dirname(fullpath), exist_ok=True)
    binary = 'b' if isinstance(data, bytes) else ''
    try:
        with open(fullpath, 'x' + binary) as outfile:
            outfile.write(data)
    except FileExistsError:
        existing = read(fullpath)
        if data != existing:
            logging.error('Failed to update %s from %r to %r', fullpath,
                          existing, data)
        else:
            logging.debug('% already cached', fullpath)
    return fullpath

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

def get_posts(directory, pattern=None, convert=None):
    '''
    get list of posts

    we use only those symlinked to by unadorned hashes
    '''
    pattern = re.compile(pattern or '^kbz[0-9A-Za-z]*$')
    filenames = [os.path.join(directory, filename)
                 for filename in os.listdir(directory)
                 if pattern.match(filename)]
    convert = convert or str  # or specify convert=os.path.realpath
    return [convert(filename) for filename in filenames
            if os.path.islink(filename)]

def find_posts(directory, suffix):
    '''
    get list of posts matching suffix
    '''
    posts = get_posts(directory, '^kbz[0-9A-Za-z]*%s$' % suffix)
    return posts

def loadposts(to_html=True, tries=0):
    '''
    fetch and return all posts from KYBYZ_HOME or, if empty, from EXAMPLE

    setting to_html to True forces conversion from JSON format to HTML
    '''
    logging.debug('running loadposts(%s)', to_html)
    if not get_posts(KYBYZ_HOME):
        if tries > 1:
            raise ValueError('No posts found after example posts cached')
        # populate KYBYZ_HOME from EXAMPLE
        for example in get_posts(EXAMPLE):
            post(None, read(example).decode())
        return loadposts(to_html, tries=tries + 1)
    # now cache any that came in over the wire
    for index in range(len(POSTS_QUEUE)):  # pylint: disable=unused-variable
        post(None, POSTS_QUEUE.popleft())
    get_post = BasePost if to_html else read
    posts = [get_post(p) for p in get_posts(KYBYZ_HOME)]
    return sorted(filter(None, posts), key=lambda p: p.timestamp, reverse=True)

def decrypt(message):
    '''
    decrypt a message sent to me, and verify sender email
    '''
    gpg = GPG()
    verified = decoded = b''
    logging.debug('decoding %s...', message[:64])
    try:
        decoded = b58decode(message)
        logging.debug('decrypting %r...', decoded[:64])
        decrypted = gpg.decrypt(decoded)
        # pylint: disable=no-member
        verified = 'trust level %s' % decrypted.trust_text
    except ValueError:
        logging.warning('%r... not base58 encoded', message[:32])
        decrypted = type('', (), {'data': message})
        verified = 'unencoded'
    except subprocess.CalledProcessError as problem:
        logging.exception(problem)
        decrypted = type('', (), {'data': b''})
    return decrypted.data, verified

def check_username(identifier):
    '''
    identifier is :bleah!bleah@bleah.com' and CACHED['username'] == 'bleah'

    >>> CACHED['username'] = 'bleah'
    >>> check_username(':bleah!bleah@bleah.com')
    ('bleah', True)
    >>> check_username(':blah!bleah@bleah.com')
    ('blah', False)
    >>> check_username(':irc.lfnet.org')
    (None, None)
    '''
    try:
        start = identifier.index(':') + 1
        end = identifier.index('!')
        nickname = identifier[start:end]
        logging.debug('identifier: %s, start: %s, end: %s, check: %s',
                      identifier, start, end, nickname)
        matched = CACHED.get('username', None) == nickname
    except ValueError:
        # ignore failure, because PINGs don't have username anyway
        #logging.error('cannot find nickname in %s', identifier)
        nickname = matched = None
    return nickname, matched
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

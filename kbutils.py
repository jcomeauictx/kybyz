#!/usr/bin/python3
'''
Kybyz utilities
'''
import os, re, subprocess  # pylint: disable=multiple-imports
from hashlib import sha256
from base58 import b58encode, b58decode
from canonical_json import canonicalize
from kbcommon import CACHE, CACHED, EXAMPLE, KYBYZ_HOME, COMMAND, ARGS, logging
from kbcommon import REGISTRATION, read, CHANNEL
from post import BasePost

def run_process(command, **kwargs):
    '''
    implementation of subprocess.run for older Python3

    https://pymotw.com/3/subprocess/
    '''
    text_input = kwargs.get('input', None)
    capture_output = kwargs.get('capture_output', False)
    logging.debug('capture_output %s ignored', capture_output)
    timeout = kwargs.get('timeout', None)
    check = kwargs.get('check', None)
    if timeout:
        raise NotImplementedError('"timeout" not supported')
    process = subprocess.Popen(
        command,
        stdin=kwargs.get('stdin', subprocess.PIPE),
        stdout=kwargs.get('stdout', subprocess.PIPE),
        stderr=kwargs.get('stderr', subprocess.PIPE),
        **{k: kwargs[k] for k in kwargs if k not in
           ['input', 'capture_output', 'timeout', 'check']}
    )
    stdout, stderr = process.communicate(text_input)
    if check and process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command,
                                            output=(stdout, stderr))
    return type('', (), {
        'stdout': stdout,
        'stderr': stderr,
    })

try:
    from gnupg import GPG
except ImportError:
    logging.warning('Using primitive GPG functionality')

    class GPG():
        '''
        drop-in replacement for python3-gnupg class

        limited to the few calls that kybyz makes,
        and only for English language, among other limitations.
        '''
        # pylint: disable=no-self-use
        def __init__(self, options=None):
            '''
            add subprocess.run replacement if it doesn't exist
            '''
            if not hasattr(subprocess, 'run'):
                subprocess.run = run_process
            else:
                try:
                    subprocess.run(['ls'], capture_output=True, check=True)
                except TypeError:  # Python3.5
                    subprocess.run = run_process
            options = options or []
            self.defaultkey = None
            for option in options:
                parts = option.split()
                if parts[0] == '--default-key':
                    # python-gnupg requires hexadecimal
                    # however, the binary isn't as picky and accepts
                    # email address, or any part of the name
                    self.defaultkey = parts[1]

        def sign(self, data):
            '''
            gpg sign given data

            unlike python-gnupg, return as binary data
            '''
            command = ['gpg', '--sign']
            if self.defaultkey:
                command.extend(['--default-key', self.defaultkey])
            run = subprocess.run(
                command,
                input=data,
                capture_output=True,
                check=True)
            run.data = run.stdout
            return run

        def encrypt(self, data, recipients, sign=True, armor=True):
            '''
            gpg encrypt data for recipients
            '''
            command = ['gpg', '--encrypt']
            if self.defaultkey:
                command.extend(['--defaultkey', self.defaultkey])
            for recipient in recipients:
                command.extend(['-r', recipient])
            if sign:
                command.append('--sign')
            if armor:
                command.append('--armor')
            run = subprocess.run(command, input=data,
                                 capture_output=True, check=False)
            run.data = run.stdout
            return run

        def decrypt(self, data):
            '''
            gpg decrypt data
            '''
            command = ['gpg', '--decrypt']
            if self.defaultkey:
                command.extend(['--default-key', self.defaultkey])
            run = subprocess.run(
                command,
                input=data,
                capture_output=True,
                check=False)
            run.data = run.stdout
            logging.debug('decrypt stderr: %s', run.stderr)
            output = list(filter(None, run.stderr.decode().split('\n')))
            logging.debug('looking for username and trust_text in %s',
                          output[-1])
            try:
                run.username, run.trust_text = re.compile(
                    r'^gpg: Good signature from "([^"]+)" \[([^]]+)\]$').match(
                        output[-1]).groups()
            except AttributeError:
                run.username = run.trust_text = None
            return run

        def verify(self, signed):
            '''
            verify signature on given signed data
            '''
            run = subprocess.run(['gpg', '--verify'], input=signed,
                                 capture_output=True, check=False)
            output = run.stderr.decode().split('\n')
            combined = ' '.join(output)
            try:
                run.timestamp = re.compile(
                    r'^gpg: Signature made (.*?)(?: using .*)?$').match(
                        output[0]).groups()[0]
                logging.debug('run.timestamp: %s', run.timestamp)
                run.key_id = re.compile(
                    r' using RSA key (?:ID )?([0-9A-F]{8,40})\s').search(
                        combined).groups()[0]
                logging.debug('run.key_id: %s', run.key_id)
                pattern = re.compile(
                    r' Good signature from "([^"]+)"(?: \[([^]]+)\])?')
                logging.debug('pattern: %s', pattern)
                run.username, run.trust_text = pattern.search(combined).groups()
                logging.debug('run.username: %s, run.trust_text: %s',
                              run.username, run.trust_text)
            except (AttributeError, IndexError) as problem:
                logging.exception('did not find needed data in %r', combined)
                raise problem
            return run

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
    verified = gpg.verify(gpg.sign('').data)
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
    posts = find_post(KYBYZ_HOME, post_id)
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

def post(post_type, *args, **kwargs):
    '''
    make a new post from the command line or from another subroutine
    '''
    kwargs.update({'type': post_type})
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
            logging.warning('updating post')
            os.unlink(unadorned)
            os.symlink(cached, unadorned)
        return hashed
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
    with open(fullpath, 'w' + binary) as outfile:
        outfile.write(data)
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

def find_post(directory, suffix):
    '''
    get list of posts matching suffix
    '''
    posts = get_posts(directory, '^kbz[0-9A-Za-z]*%s$' % suffix)
    return posts

def loadposts(to_html=True):
    '''
    fetch and return all posts from KYBYZ_HOME or, if empty, from EXAMPLE

    setting to_html to True forces conversion from JSON format to HTML
    '''
    if os.path.exists(KYBYZ_HOME) and get_posts(KYBYZ_HOME):
        directory = KYBYZ_HOME
    else:
        directory = EXAMPLE
    get_post = BasePost if to_html else read
    posts = [get_post(postfile) for postfile in get_posts(directory)]
    logging.debug('running loadposts(%s)', to_html)
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

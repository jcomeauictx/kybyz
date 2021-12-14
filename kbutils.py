#!/usr/bin/python3
'''
Kybyz utilities
'''
import os, re, subprocess  # pylint: disable=multiple-imports
from datetime import datetime, timezone
from hashlib import sha256
from base58 import b58encode, b58decode
from canonical_json import canonicalize
from kbcommon import CACHED, logging

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

class GPG():
    '''
    drop-in replacement for python3-gnupg class

    limited to the few calls that kybyz makes
    '''
    # pylint: disable=no-self-use
    def __init__(self):
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

    def sign(self, data):
        '''
        gpg sign given data

        unlike python-gnupg, return as binary data
        '''
        run = subprocess.run(['gpg', '--sign'], input=data,
                             capture_output=True, check=True)
        run.data = run.stdout
        return run

    def encrypt(self, data, recipients, sign=True, armor=True):
        '''
        gpg encrypt data for recipients
        '''
        command = ['gpg', '--encrypt']
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
        run = subprocess.run(
            ['gpg', '--decrypt'], input=data, capture_output=True, check=False)
        run.data = run.stdout
        logging.debug('decrypt stderr: %s', run.stderr)
        output = list(filter(None, run.stderr.decode().split('\n')))
        logging.debug('looking for username and trust_text in %s', output[-1])
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

def read(filename):
    '''
    read and return file contents
    '''
    with open(filename, 'rb') as infile:
        return infile.read()

def make_timestamp():
    '''
    untrusted timestamp.

    will need blockchain for a trusted timestamp
    '''
    return datetime.now(timezone.utc).isoformat()

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

def send(recipient, email, *words):
    '''
    encrypt, sign, and send a private message to recipient

    `recipient` is the 'nick' (nickname) of the user to whom you wish to send
    the message. `email` is not necessarily an email address, but is used to
    find the GPG key of the recipient.

    use `-` instead of email to send plain text
    '''
    text = ' '.join(words).encode()
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

def tuplify(versionstring):
    '''
    convert version string to tuple of integers

    >>> tuplify('0.0.1')
    (0, 0, 1)
    >>> max(['0.0.100', '0.0.11'])
    '0.0.11'
    >>> max(['0.0.100', '0.0.11'], key=tuplify)
    '0.0.100'
    '''
    return tuple(int(s) for s in versionstring.split('.'))

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

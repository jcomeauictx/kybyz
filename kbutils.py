#!/usr/bin/python3
'''
Kybyz utilities
'''
import logging, re, subprocess  # pylint: disable=multiple-imports
from datetime import datetime, timezone
from hashlib import sha256
from base58 import b58encode, b58decode
from canonical_json import canonicalize
from kbcommon import CACHED

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

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
    if timeout or check:
        raise NotImplementedError('"timeout" and "check" not supported')
    process = subprocess.Popen(
        command,
        stdin=kwargs.get('stdin', subprocess.PIPE),
        stdout=kwargs.get('stdout', subprocess.PIPE),
        stderr=kwargs.get('stderr', subprocess.PIPE),
        **{k: kwargs[k] for k in kwargs if k not in
           ['input', 'capture_output', 'timeout', 'check']}
    )
    stdout, stderr = process.communicate(text_input)
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

    def sign(self, data):
        '''
        gpg sign given data

        unlike python-gnupg, return as binary data
        '''
        run = subprocess.run(['gpg', '--sign'], input=data,
                             capture_output=True, check=False)
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
        try:
            run.timestamp = re.compile(r'^gpg: Signature made (.*)$').match(
                output[0]).groups()[0]
            run.key_id = re.compile(
                r'^gpg: \s*using RSA key ([0-9A-F]{40}$)').match(
                output[1]).groups()[0]
            run.username, run.trust_text = re.compile(
                r'^gpg: Good signature from "([^"]+)" \[([^]]+)\]$').match(
                output[2]).groups()
        except (AttributeError, IndexError) as problem:
            logging.exception('did not find needed data in %s', vars(run))
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
    b'kbz6cd8vvJh7zja18Nju1GTuCNKqhDdFo7RCWvVbjHyqEuv'
    '''
    prefix = b'\x07\x88\xcc'  # when added to 32-byte string produces 'kbz'
    canonical = canonicalize(message).encode()
    hashed = sha256(canonical).digest()
    return b58encode(prefix + hashed)

def verify_key(email):
    '''
    fetch user's GPG key and make sure it matches given email address
    '''
    gpgkey = None
    gpg = GPG()
    # pylint: disable=no-member
    verified = gpg.verify(gpg.sign('').data)
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
    '''
    gpg = GPG()
    text = ' '.join(words).encode()
    logging.debug('message before encrypting: %s', text)
    encrypted = gpg.encrypt(
        text,  # pylint: disable=no-member
        [email],
        sign=True,
        armor=False)
    logging.debug('encrypted: %r...', encrypted.data[:64])
    encoded = b58encode(encrypted.data).decode()
    logging.debug('encoded: %s', encoded)
    CACHED['ircbot'].privmsg(recipient, encoded)

def decrypt(message):
    '''
    decrypt a message sent to me, and verify sender email
    '''
    gpg = GPG()
    logging.debug('decoding %s...', message[:64])
    decoded = b58decode(message)
    logging.debug('decrypting %r...', decoded[:64])
    try:
        decrypted = gpg.decrypt(decoded)
        verified = decrypted.trust_text  # pylint: disable=no-member
    except subprocess.CalledProcessError:
        decrypted = type('', (), {'data': b''})
        verified = False
    return decrypted.data, verified

#!/usr/bin/python3
'''
Kybyz utilities
'''
import logging
from datetime import datetime, timezone
from hashlib import sha256
from gnupg import GPG
from base58 import b58encode, b58decode
from canonical_json import canonicalize
from kbcommon import CACHED

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

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
    if email:
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
    text = ' '.join(words)
    logging.debug('message before encrypting: %s', text)
    encrypted = gpg.encrypt(
        text,  # pylint: disable=no-member
        [email],
        sign=True,
        armor=False)
    logging.debug('encrypted: %r...', encrypted.data[:64])
    CACHED['ircbot'].privmsg(recipient, b58encode(encrypted.data).decode())

def decrypt(message):
    '''
    decrypt a message sent to me, and verify sender email
    '''
    gpg = GPG()
    logging.debug('decoding %s...', message[:64])
    decoded = b58decode(message)
    logging.debug('decrypting %r...', decoded[:64])
    decrypted = gpg.decrypt(decoded)
    verified = decrypted.trust_text
    return decrypted.data, verified

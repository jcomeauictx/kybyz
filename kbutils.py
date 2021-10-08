#!/usr/bin/python3
'''
Kybyz utilities
'''
import logging
from datetime import datetime, timezone
from hashlib import sha256
from gnupg import GPG
from base58 import b58encode
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

def kbhash(json_message):
    '''
    return base58 of sha256 hash of json_message, with prefix 'kbz'

    >>> kbhash({'test': 0})
    b'kbz6cd8vvJh7zja18Nju1GTuCNKqhDdFo7RCWvVbjHyqEuv'
    '''
    prefix = b'\x07\x88\xcc'  # when added to 32-byte string produces 'kbz'
    canonical = canonicalize(json_message).encode()
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

def message(recipient, email, *words):
    '''
    sign, encrypt, and send a private message to recipient

    `recipient` is the 'nick' (nickname) of the user to whom you wish to send
    the message. `email` is not necessarily an email address, but it used to
    find the GPG key of the recipient.
    '''
    gpg = GPG()
    text = ' '.join(words)
    logging.debug('message before encrypting: %s', text)
    signed = gpg.sign(text)
    encrypted = gpg.encrypt(
        signed.data,  # pylint: disable=no-member
        [email],
        armor=False)
    CACHED['ircbot'].privmsg(recipient, b58encode(encrypted.data).decode())

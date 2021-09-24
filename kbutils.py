#!/usr/bin/python3
'''
Kybyz utilities
'''
import logging
from datetime import datetime, timezone
from hashlib import sha256
from base58 import b58encode
from canonical_json import canonicalize

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
    '''
    prefix = ''  # when added to 32-byte string produces 'kbz'
    canonical = canonicalize(message)
    hashed = sha256(canonical).digest()
    return b58encode(prefix + hashed)

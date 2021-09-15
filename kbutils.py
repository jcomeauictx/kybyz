#!/usr/bin/python3
'''
Kybyz utilities
'''
import logging
from datetime import datetime, timezone

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

#!/usr/bin/python3
'''
kybyz1 post
'''
from datetime import datetime, timezone

class Post():
    '''
    encapsulation of kybyz post
    '''
    def __init__(self, **kwargs):
        '''
        initialize instantiation from **dict
        '''
        for key in kwargs:
            setattr(self, key, kwargs[key])
        if not getattr(self, 'timestamp'):
            self.timestamp = make_timestamp()

def make_timestamp():
    '''
    untrusted timestamp.

    will need blockchain for a trusted timestamp
    '''
    return datetime.now(timezone.utc).isoformat()

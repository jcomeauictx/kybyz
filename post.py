#!/usr/bin/python3
'''
kybyz1 post
'''
from datetime import datetime, timezone

class Post():
    '''
    encapsulation of kybyz post
    '''
    @property
    def timestamp(self):
        '''
        untrusted timestamp.

        will need blockchain for a trusted timestamp
        '''
        return datetime.now(timezone.utc).isoformat()

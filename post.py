#!/usr/bin/python3
'''
kybyz1 post
'''
from datetime import datetime, timezone

class Post():
    '''
    encapsulation of kybyz post
    '''
    def __init__(self, filename=None, **kwargs):
        '''
        initialize instantiation from **dict
        '''
        self.filename = filename
        for key in kwargs:
            setattr(self, key, kwargs[key])
        if not getattr(self, 'timestamp', None):
            self.timestamp = make_timestamp()

    def validate(self):
        '''
        make sure post contents fit the version given
        '''
        if not self.__doc__:
            raise RuntimeError('Must not run with optimization')
        classname = type(self).__name__.lower()
        assert (getattr(self, 'type', None) == classname or
                self.filename.endswith('.' + classname))

def make_timestamp():
    '''
    untrusted timestamp.

    will need blockchain for a trusted timestamp
    '''
    return datetime.now(timezone.utc).isoformat()

if __name__ == '__main__':
    Post('testmeme.json').validate()

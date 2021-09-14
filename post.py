#!/usr/bin/python3
'''
kybyz1 post
'''
from datetime import datetime, timezone
from canonical_json import literal_eval
from kbutils import read

class Post():
    '''
    encapsulation of kybyz post
    '''
    def __init__(self, filename=None, **kwargs):
        '''
        initialize instantiation from **dict
        '''
        self.classname = self.__class__.__name__
        self.filename = filename
        if not kwargs:
            kwargs = literal_eval(read(filename).decode().strip())
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
        assert (getattr(self, 'type', None) == self.classname or
                getattr(self, 'filename', '').endswith('.' + self.classname))

    def to_html(self):
        '''
        output contents as HTML
        '''
        template = read(self.classname + '.html')
        return template.format(posting=self)

def make_timestamp():
    '''
    untrusted timestamp.

    will need blockchain for a trusted timestamp
    '''
    return datetime.now(timezone.utc).isoformat()

if __name__ == '__main__':
    Post('exampe.kybyz1/testmeme.json').validate()

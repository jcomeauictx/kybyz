#!/usr/bin/python3
'''
kybyz1 post
'''
import os
from canonical_json import literal_eval
from kbutils import read, make_timestamp

class Post():
    '''
    encapsulation of kybyz post
    '''
    def __new__(cls, filename, **kwargs):
        mapping = {subclass.classname: subclass
                   for subclass in [cls] + cls.__subclasses__}
        if not kwargs:
            kwargs = literal_eval(read(filename).decode().strip())
        if not kwargs.get('type'):
            post_type = os.path.splitext(filename)[1].lstrip('.')
        else:
            post_type = kwargs['type']
        subclass = mapping[post_type]
        instance = super(Post, subclass).__new__(subclass)
        return instance

    def __init__(self, filename, **kwargs):
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
        return template.format(post=self)

class Netmeme(Post):
    '''
    encapsulation of kybyz Internet meme (netmeme is my abbreviation)
    '''

class Kybyz(Post):
    '''
    encapsulation of a "kybyz": a "thumbs-up" or other icon with optional text
    '''

if __name__ == '__main__':
    Post('exampe.kybyz1/testmeme.json').validate()

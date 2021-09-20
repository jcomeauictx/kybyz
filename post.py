#!/usr/bin/python3
'''
kybyz post
'''
import os, json  # pylint: disable=multiple-imports
from kbutils import read, make_timestamp, logging

class BasePost():
    '''
    base class for kybyz posts
    '''
    classname = 'basepost'

    def __new__(cls, filename=None, **kwargs):
        mapping = {subclass.classname: subclass
                   for subclass in cls.__subclasses__()}
        if not kwargs:
            try:
                kwargs = json.loads(read(filename))
            except TypeError:
                kwargs = {}
        if filename and not kwargs.get('type'):
            post_type = os.path.splitext(filename)[1].lstrip('.')
        else:
            post_type = kwargs['type']
        subclass = mapping.get(post_type, None)
        try:
            instance = super(BasePost, subclass).__new__(subclass)
        except TypeError:
            instance = None
        return instance

    def __init__(self, filename=None, **kwargs):
        '''
        initialize instantiation from **dict
        '''
        self.filename = filename
        if not kwargs:
            kwargs = json.loads(read(filename))
        for key in kwargs:
            setattr(self, key, kwargs[key])
        if not getattr(self, 'timestamp', None):
            self.timestamp = make_timestamp()

    def __str__(self):
        '''
        return string representation
        '''
        return self.to_html()

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
        template = read(self.classname + '.html').decode()
        return template.format(post=self)

class Post(BasePost):
    '''
    encapsulation of kybyz post
    '''
    classname = 'post'

class Netmeme(BasePost):
    '''
    encapsulation of kybyz Internet meme (netmeme is my abbreviation)
    '''
    classname = 'netmeme'

class Kybyz(BasePost):
    '''
    encapsulation of a "kybyz": a "thumbs-up" or other icon with optional text
    '''
    classname = 'kybyz'

if __name__ == '__main__':
    logging.debug('testing post')
    print(BasePost('example.kybyz/testmeme.json'))

#!/usr/bin/python3
'''
kybyz post
'''
import os, json, re  # pylint: disable=multiple-imports
from kbutils import read, make_timestamp
from kbcommon import logging

class PostAttribute():  # pylint: disable=too-few-public-methods
    '''
    base class for kybyz post attributes
    '''
    def __init__(self, name, required=True, hashed=True, values=None):
        '''
        post attribute have unique names

        required can be True or False

        hashed can be:
            True,
            False (both key and value removed before hashing,
            None (set to None (null) before hashing),
            or a particular value (such as [] to empty a list before hashing)

        values can be a tuple of allowed values, None to allow any value,
        a re.Pattern to specify a match pattern (implying str object), or
        a lambda expression that must return True for the value to be valid.
        '''
        self.name = name
        self.required = required
        self.hashed = hashed
        self.values = values

class BasePost():
    '''
    base class for kybyz posts
    '''
    classname = 'basepost'
    versions = {
        '0.0.1': {
            'type': PostAttribute('type', values=('post', 'netmeme', 'kybyz')),
            'version': PostAttribute('version', values=('0.0.1',)),
            'author': PostAttribute('author'),
            'fingerprint': PostAttribute(
                'fingerprint',
                values=re.compile(r'^[0-9A-F]{16}')),
            'image': PostAttribute('image'),
            'mimetype': PostAttribute('mimetype'),
            'toptext': PostAttribute('toptext'),
            'bottomtext': PostAttribute('bottomtext'),
            'signed': PostAttribute('signed', required=False),
            'in-reply-to': PostAttribute('in-reply-to',
                                         required=False,
                                         hashed=[],
                                         values=lambda v: isinstance(v, list)),
            'replies': PostAttribute('replies',
                                     required=False,
                                     hashed=[],
                                     values=lambda v: isinstance(v, list)),
        }
    }
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

    def to_json(self):
        '''
        output contents as JSON
        '''

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

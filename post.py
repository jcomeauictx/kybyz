#!/usr/bin/python3
'''
kybyz post
'''
# pylint: disable=bad-option-value, consider-using-f-string
import os, json, re  # pylint: disable=multiple-imports
from copy import deepcopy
from kbcommon import read, make_timestamp, tuplify, logging, CACHED, \
 doctestdebug
from canonical_json import canonicalize
LIKE = '\N{THUMBS UP SIGN}'
LOVE = '\N{BLACK HEART SUIT}'

class PostValidationError(ValueError):  # pylint: disable=too-few-public-methods
    '''
    distinguish validation errors from other ValueErrors
    '''

class NoDefault():  # pylint: disable=too-few-public-methods
    '''
    distinguish attributes with no defaults from None
    '''

class PostAttribute():
    '''
    base class for kybyz post attributes
    '''
    def __init__(self, name, required=True, hashed=True, values=None):
        '''
        post attributes have unique names

        required can be:
            True,
            False,
            a tuple evaluated as names of other post attributes that must be
            present and evaluate to True; for example, mimetype is dependent on
            there being an image, so mimetype's `required` value would be
            ('image',),
            or any other object which fits `values`, which will be used as
            the default, and required therefore presumed to be True.

        hashed can be:
            True,
            False (both key and value removed before hashing),
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

    def validate(self, post):
        '''
        make sure this attribute fits requirement

        NOTE: sets attribute in post if not present and has default value
        '''
        def validate_tuple(value):
            '''
            helper function for values tuple
            '''
            doctestdebug('validating that value %r in %s', value, self.values)
            return value in self.values

        def validate_pattern(value):
            '''
            helper function for values as compiled regex
            '''
            doctestdebug('validating pattern %s matches value %r',
                          self.values, value)
            try:
                return self.values.match(value)
            except TypeError as error:
                raise PostValidationError(
                    '%r is wrong type for pattern match %s' % (value, self)
                ) from error

        def validate_none(value):  # pylint: disable=unused-argument
            '''
            helper function for value that can be anything
            '''
            doctestdebug('validating %r regardless of what it is', value)
            return True

        def validate_lambda(value):
            '''
            helper function for values as lambda expression
            '''
            doctestdebug('validating lambda expression %s(%r)',
                          self.values, value)
            return self.values(value)

        validation_dispatcher = {
            type(None): validate_none,
            type(re.compile(r'^$')): validate_pattern,
            type(lambda: None): validate_lambda,
            type(()): validate_tuple,
        }

        required = self.required
        default = NoDefault
        if isinstance(required, tuple):
            evaluated = all((getattr(post, attribute, None)
                             for attribute in required))
            doctestdebug('tuple %s evaluated to required=%s',
                          required, evaluated)
            required = evaluated
        elif required not in [True, False]:
            doctestdebug('setting default for %s to %r', self.name, required)
            default = required
            required = True
        value = getattr(post, self.name, default)
        doctestdebug('checking that %s value %r in %s',
                      self.name, value, self.values)
        validation_dispatcher[type(self.values)](value)
        if value == NoDefault and required:
            raise PostValidationError('Post %r lacks valid %s attribute' %
                                      (post, self.name))
        if value != NoDefault:
            doctestdebug('setting attribute %s in post to %s',
                          self.name, value)
            setattr(post, self.name, value)  # default if nothing else
        else:
            doctestdebug('attribute %s has value %r and no default value',
                          self.name, value)

    def hashvalue(self, post):
        '''
        return key and value for hashing

        if post lacks attribute at this point, return invalid (None, None)
        '''
        try:
            value = getattr(post, self.name)
            if self.hashed is False:
                raise AttributeError(
                    '%s not part of post hashvalue' % self.name
                )
        except AttributeError:
            return (None, None)
        if self.hashed is True:
            return (self.name, value)
        # None or any other explicit value
        return (self.name, self.hashed)

    def __str__(self):
        return '<PostAttribute name=%r required=%r hashed=%r values=%r>' % (
            self.name, self.required, self.hashed, self.values)
    __repr__ = __str__

class BasePost():
    '''
    base class for kybyz posts
    '''
    classname = 'basepost'
    versions = {
        '0.0.1': {
            'basepost': {
                'type': PostAttribute('type', values=(
                    'post', 'netmeme', 'kybyz')
                ),
                'version': PostAttribute('version', values=('0.0.1',)),
                'author': PostAttribute(
                    'author',
                    values=re.compile(r'^\w+[\w\s]*\w$')
                ),
                'fingerprint': PostAttribute(
                    'fingerprint',
                    values=re.compile(r'^[0-9A-F]{16}$')),
                'image': PostAttribute('image', required=''),
                'mimetype': PostAttribute('mimetype', required=('image',)),
                'toptext': PostAttribute('toptext', required=''),
                'bottomtext': PostAttribute('bottomtext', required=''),
                'signed': PostAttribute('signed', required=False),
                'timestamp': PostAttribute('timestamp', hashed=False),
                'in-reply-to': PostAttribute('in-reply-to',
                                             required=False,
                                             hashed=[],
                                             values=lambda v: isinstance(
                                                 v, list)
                                             ),
                'replies': PostAttribute('replies',
                                         required=False,
                                         hashed=[],
                                         values=lambda v: isinstance(v, list)),
            }
        }
    }
    versions['0.0.1']['kybyz'] = dict(versions['0.0.1']['basepost'].items())
    versions['0.0.1']['kybyz']['text'] = PostAttribute('text', required=LIKE)
    del versions['0.0.1']['kybyz']['toptext']
    del versions['0.0.1']['kybyz']['bottomtext']
    versions['0.0.1']['post'] = dict(versions['0.0.1']['basepost'].items())
    versions['0.0.1']['netmeme'] = dict(versions['0.0.1']['basepost'].items())
    def __new__(cls, filename='', **kwargs):
        '''
        previous approach was failing, since changes made to kwargs in __new__
        don't make it into __init__.

        the *only reason* for __new__ is to be able to instantiate the
        right subclass of BasePost without having to duplicate code into
        each subclass. but to do that, it may need to fill in kwargs from
        a file or from other sources. at the very least, it needs the
        post_type, which points to the subclass, and the version number.

        the idea behind version numbers is that, as the code grows and
        semantics change, old posts can still be recognized and rendered.
        '''
        mapping = {subclass.classname: subclass
                   for subclass in cls.__subclasses__()}
        doctestdebug('mapping: %s, kwargs: %s', mapping, kwargs)
        if not kwargs:
            try:
                kwargs.update(json.loads(read(filename)))
            except TypeError as failed:
                logging.error('no keywords supplied,'
                              ' and file %r cannot be read: %s',
                              filename, failed)
                return None
        doctestdebug('type: %s, cls.classname: %s',
                     kwargs.get('type'), cls.classname)
        post_type = kwargs.get('type', cls.classname)
        # if no version specified, use latest
        default_version = max(cls.versions, key=tuplify)
        version = kwargs.get('version', default_version)
        if filename and post_type not in mapping:
            post_type = os.path.splitext(filename)[1].lstrip('.')
        subclass = mapping.get(post_type, cls)
        doctestdebug('updated kwargs: %s, subclass: %s', kwargs, subclass)
        try:
            # pylint: disable=no-value-for-parameter  # (why? dunno)
            instance = super(BasePost, subclass).__new__(subclass)
            # fill in defaults from things unknown at script load time
            instance.versions[version][post_type]['author'].required = \
                CACHED.get('username', True)
            instance.versions[version][post_type]['fingerprint'].required = \
                CACHED.get('gpgkey', '')[-16:] or True
        except TypeError:
            logging.exception('Unknown post type %s', subclass)
            instance = None
        return instance

    def __init__(self, filename='', **kwargs):
        '''
        initialize instantiation from file or from kwargs and defaults
        '''
        doctestdebug('BasePost.__init__(): kwargs=%s', kwargs)
        for key in kwargs:
            setattr(self, key, kwargs[key])
        if not getattr(self, 'timestamp', None):
            self.timestamp = make_timestamp()
        self.validate()

    def __str__(self):
        '''
        return string representation
        '''
        return self.to_html()

    def validate(self):
        '''
        make sure post contents fit the version given

        note that additional attributes can be given a post and they
        will not be checked; we only check the schema
        '''
        if not self.__doc__:
            raise RuntimeError('Must not run with optimization')
        # why doesn't 'author' have default value from cache?
        doctestdebug('BasePost.validate: CACHED: %s', CACHED)
        assert (getattr(self, 'type', None) == self.classname or
                getattr(self, 'filename', '').endswith('.' + self.classname))
        schema = self.versions[self.version][self.type]
        doctestdebug('post validation schema: %s', schema)
        for attribute in schema:
            doctestdebug('validating attribute %s in schema', attribute)
            schema[attribute].validate(self)

    def to_html(self):
        '''
        output contents as HTML
        '''
        template = read(self.classname + '.html').decode()
        return template.format(post=self)

    def to_json(self, for_hashing=False):
        '''
        output contents as JSON
        '''
        if for_hashing:
            dictionary = dict((value.hashvalue(self) for value in
                               self.versions[self.version][self.type].values()))
            del dictionary[None]  # clears out last of values not to be hashed
        else:
            dictionary = self.__dict__
            logging.warning('dictionary: %s', dictionary)
        return canonicalize(dictionary)

class Post(BasePost):
    r'''
    encapsulation of kybyz post

    >>> str(Post(author='test',
    ...          fingerprint='0000000000000000'))  # doctest: +ELLIPSIS
    '<div class="post">\n...'
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
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

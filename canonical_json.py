#!/usr/bin/python3
'''
kybyz version 0.1, since original has foundered

this will be built on ipfs, using canonical json objects
'''
import sys, json, logging  # pylint: disable=multiple-imports

def canonicalize(obj):
    '''
    dump object as canonical json

    https://gibson042.github.io/canonicaljson-spec/ and
    http://wiki.laptop.org/go/Canonical_JSON for reference

    if it's not json, just return it as is.

    >>> print(canonicalize({'test': [1, 2, 3, 'test again']}), end='')
    {"test":[1,2,3,"test again"]}
    '''
    if isinstance(obj, str):
        logging.debug('object passed as string: %s', obj)
        try:
            obj = json.loads(obj)
        except ValueError:
            logging.debug('%r does not represent a valid Python object', obj)
            return obj
    logging.debug('object being canonicalized: %s', obj)
    result = json.dumps(
        obj,
        ensure_ascii=False,  # is this correct by the standard?
        separators=(',', ':'),  # no unnecessary whitespace
        sort_keys=True,
    )
    return result

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
    try:
        print(canonicalize(sys.argv[1]), end='')  # no trailing whitespace
    except IndexError:
        print('Must pass a single string representing JSON object')

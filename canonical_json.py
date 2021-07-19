#!/usr/bin/python3
'''
kybyz version 0.1, since original has foundered

this will be built on ipfs, using canonical json objects
'''
import sys, json, logging  # pylint: disable=multiple-imports
from ast import literal_eval

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

def canonicalize(obj):
    '''
    dump object as canonical json

    https://gibson042.github.io/canonicaljson-spec/ and
    http://wiki.laptop.org/go/Canonical_JSON for reference

    >>> print(canonicalize({'test': [1, 2, 3, 'test again']}), end='')
    {"test":[1,2,3,"test again"]}
    '''
    if isinstance(obj, str):
        logging.debug('object passed as string: %s', obj)
        obj = literal_eval(obj)
    logging.debug('object being canonicalized: %s', obj)
    result = json.dumps(
        obj,
        ensure_ascii=False,  # is this correct by the standard?
        separators=(',', ':'),  # no unnecessary whitespace
        sort_keys=True,
    )
    return result

if __name__ == '__main__':
    try:
        print(canonicalize(sys.argv[1]), end='')  # no trailing whitespace
    except IndexError:
        print('Must pass a single string representing JSON object')

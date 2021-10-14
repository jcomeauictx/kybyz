#!/usr/bin/python3
'''
common data structures needed by various parts of kybyz
'''
import os
from collections import defaultdict

CACHED = defaultdict(str, {'uptime': None})
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz')
KYBYZ_HOME = os.path.join(CACHE, 'home')

#!/usr/bin/python3
'''
common data structures needed by various parts of kybyz
'''
import os

CACHED = {'uptime': None}
HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.kybyz')
KYBYZ_HOME = os.path.join(CACHE, 'home')

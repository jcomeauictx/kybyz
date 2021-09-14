#!/usr/bin/python3
'''
Kybyz utilities
'''

def read(filename):
    '''
    read and return file contents
    '''
    with open(filename, 'rb') as infile:
        return infile.read()

#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import sys, os, socket  
import threading
IRCSERVER = irc.lfnet.org

class IRC():
    '''
    Implements IRC client

    see https://www.techbeamers.com/create-python-irc-bot/`
    '''
    def __init__(self):
        '''
        initialize the client
        '''
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

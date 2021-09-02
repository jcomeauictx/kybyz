#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import socket, pwd, os, threading, logging

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

IRCSERVER = 'irc.lfnet.org'
PORT = 6667

class IRC():
    '''
    Implements IRC client

    see https://www.techbeamers.com/create-python-irc-bot/`
    also https://datatracker.ietf.org/doc/html/rfc2812
    '''
    def __init__(self, channel='#kybyz', server=IRCSERVER,
                 port=PORT, nickname=None, realname=None):
        '''
        initialize the client
        '''
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = server
        self.channel = channel
        self.nickname = nickname or pwd.getpwnam(os.geteuid()).pw_name
        self.realname = realname or pwd.getpwnam(os.geteuid()).pw_gecos
        self.connection = self.connect(server, channel, port,
                                       self.nickname, self.realname)
        self.terminate = False
        while not self.terminate:
            received = self.client.recv(2048).decode()
            logging.info(received)

    def connect(self, server, port, channel, nickname, realname):
        '''
        connect to the server and identify ourselves
        '''
        names = (nickname, realname)
        self.client.connect((server, port))
        self.client.send(('USER %s 0 * :%s\r\n' % names).encode())
        logging.info('received: %s', self.irc.recv(2048).decode())
        self.client.send(('NICK %s\r\n' % nickname).encode())
        logging.info('received: %s', self.irc.recv(2048).decode())

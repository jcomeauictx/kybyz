#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import socket, pwd, os, threading, logging, time

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

IRCSERVER = 'irc.lfnet.org'
PORT = 6667
CHANNEL = '#kybyz'

class IRCBot():
    '''
    Implements IRC client

    see https://www.techbeamers.com/create-python-irc-bot/`
    also https://datatracker.ietf.org/doc/html/rfc2812
    '''
    def __init__(self, server=IRCSERVER, port=PORT,
                 nickname=None, realname=None):
        '''
        initialize the client
        '''
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = server
        self.nickname = nickname or pwd.getpwuid(os.geteuid()).pw_name
        self.realname = realname or pwd.getpwuid(os.geteuid()).pw_gecos
        self.connection = self.connect(server, port,
                                       self.nickname, self.realname)
        self.terminate = False
        daemon = threading.Thread(target=self.monitor, name='ircbot_daemon')
        daemon.daemon = True
        daemon.start()

    def connect(self, server, port, nickname, realname):
        '''
        connect to the server and identify ourselves
        '''
        names = (nickname, realname)
        connection = self.client.connect((server, port))
        self.client.send(('USER %s 0 * :%s\r\n' % names).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())
        self.client.send(('NICK %s\r\n' % nickname).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())
        self.client.send(('JOIN %s\r\n' % CHANNEL).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())
        return connection

    def privmsg(self, message, target=CHANNEL):
        '''
        simulates typing a message in ircII with no preceding command
        '''
        self.client.send(('PRIVMSG %s %s\r\n' % (target, message)).encode())

    def monitor(self):
        '''
        wait for input. send a PONG for every PING

        intended to run in a daemon thread

        set ircbot.terminate to True in order to shut it down
        '''
        while not self.terminate:
            received = self.client.recv(2048).decode()
            logging.info(received)
            if received.split()[0] == 'PING':
                self.client.send(received.replace('I', 'O', 1).encode())
        logging.warning('IRC monitor terminated from launching thread')

def test():
    '''
    run a bot from the command line, for testing
    '''
    try:
        ircbot = IRCBot()
        time.sleep(600)
    except KeyboardInterrupt:
        logging.warning('Telling monitor to terminate')
        ircbot.terminate = True

if __name__ == '__main__':
    test()
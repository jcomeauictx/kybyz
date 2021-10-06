#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import socket, pwd, os, threading, logging, time
from select import select

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

IRCSERVER = 'irc.lfnet.org'
PORT = 6667
CHANNEL = '#kybyz'
FIFO = 'ircbot.fifo'

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
        self.connect(server, port, self.nickname, self.realname)
        if not os.path.exists(FIFO):
            self.fifo = os.mkfifo(FIFO, 0o660)
            self.listener = open(self.fifo)
        self.terminate = False
        daemon = threading.Thread(target=self.monitor, name='ircbot_daemon')
        daemon.daemon = True
        daemon.start()

    def connect(self, server, port, nickname, realname):
        '''
        connect to the server and identify ourselves
        '''
        names = (nickname, realname)
        self.client.connect((server, port))
        self.client.send(('USER %s 0 * :%s\r\n' % names).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())
        self.client.send(('NICK %s\r\n' % nickname).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())
        self.client.send(('JOIN %s\r\n' % CHANNEL).encode())
        logging.info('received: \n%s\n', self.client.recv(2048).decode())

    def privmsg(self, message, target=CHANNEL):
        '''
        simulates typing a message in ircII with no preceding command

        send to specific user by using. e.g. target='jcomeau' instead of
        a channel name.
        '''
        self.client.send(('PRIVMSG %s %s\r\n' % (target, message)).encode())

    def monitor(self):
        '''
        wait for input. send a PONG for every PING

        intended to run in a daemon thread

        set ircbot.terminate to True in order to shut it down
        '''
        logging.debug('ircbot monitoring incoming traffic')
        while not self.terminate:
            found = select([self.client, self.listener], [], [])
            if self.client in found[0]:
                received = self.client.recv(2048).decode()
                logging.info('received: %s', received)
                if received.split()[0] == 'PING':
                    pong = received.replace('I', 'O', 1)
                    logging.info('sending: %s', pong)
                    self.client.send(pong.encode())
            if self.listener in found[0]:
                received = self.client.recv(2048).decode()
                logging.info('received: %s', received)
        # this following message is never actually seen
        logging.warning('ircbot terminated from launching thread')

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

#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import socket, pwd, os, threading, logging, time
from kbcommon import CACHED
from kbutils import decrypt

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

IRCSERVER = 'irc.lfnet.org'
PORT = 6667
CHANNEL = '#kybyz'
BUFFERSIZE = 16 * 1024  # make it big enough to get full banner from IRC server
CACHED['irc_in'] = CACHED.get('irc_in', [])
CACHED['irc_out'] = CACHED.get('irc_out', [])

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
        logging.info('received: \n%r\n', self.client.recv(BUFFERSIZE).decode())
        self.client.send(('NICK %s\r\n' % nickname).encode())
        logging.info('received: \n%r\n', self.client.recv(BUFFERSIZE).decode())
        self.client.send(('JOIN %s\r\n' % CHANNEL).encode())
        received = self.client.recv(BUFFERSIZE).decode().split()
        CACHED['irc_id'] = received[0]
        logging.info('received: \n%r\n', received)
        return connection

    def privmsg(self, target, message):
        '''
        simulates typing a message in ircII with no preceding command

        target should be a channel name preceded by '#', or nick

        message should not have any embedded CRLFs, colons (":"), or non-ASCII
        characters.
        '''
        testmsg = ' '.join(
            [CACHED['irc_id'], 'PRIVMSG', target, ':' + message]
        ).encode()
        if len(testmsg) <= 510:
            self.client.send(('PRIVMSG %s %s\r\n' % (target, message)).encode())
        else:
            pieces = testmsg[:510].split(':')
            chunklength = pieces[-1]
            for chunk in [message[i:i+chunklength]
                          for i in range(0, len(message), chunklength)]:
                self.client.send(
                    ('PRIVMSG %s %s\r\n' % (target, chunk)).encode())

    def monitor(self):
        '''
        wait for input. send a PONG for every PING

        intended to run in a daemon thread

        set ircbot.terminate to True in order to shut it down
        '''
        logging.debug('ircbot monitoring incoming traffic')
        while not self.terminate:
            received = self.client.recv(BUFFERSIZE).decode()
            logging.info('received: %r', received)
            words = received.split()
            if words[0] == 'PING':
                pong = received.replace('I', 'O', 1)
                logging.info('sending: %s', pong)
                self.client.send(pong.encode())
            elif words[1] == 'PRIVMSG':
                if words[2] == CACHED.get('username', None):
                    logging.info('private message received from %s:', words[0])
                    try:
                        logging.info(decrypt(words[3].lstrip(':').encode()))
                    except ValueError:
                        CACHED['irc_in'].append(received)
                elif words[2] == CHANNEL:
                    logging.info('public message received from %s:', words[0])
                    logging.info(' '.join(words[3:]))
            # probably won't be using this but just for reference
            # self.client.send(CACHED['irc_out'].pop(0).encode())
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

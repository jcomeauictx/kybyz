#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import sys, os, socket, pwd, threading, logging, time
from kbcommon import CACHED
from kbutils import decrypt

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

IRCSERVER = 'irc.lfnet.org'
PORT = 6667
CHANNEL = '#kybyz'
BUFFERSIZE = 16 * 1024  # make it big enough to get full banner from IRC server
CRLF = '\r\n'
TIMEOUT = int(os.getenv('KB_DELAY') or 600)

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
        self.stream = self.client.makefile()
        self.server = server
        self.nickname = nickname or pwd.getpwuid(os.geteuid()).pw_name
        # NOTE: when we implement true p2p networking, realname should include
        # connection port
        self.realname = realname or pwd.getpwuid(os.geteuid()).pw_gecos
        self.connection = self.connect(server, port,
                                       self.nickname, self.realname)
        self.terminate = False
        daemon = threading.Thread(target=self.monitor, name='ircbot_daemon')
        daemon.daemon = True
        daemon.start()

    def nick(self, nickname):
        '''
        set new nickname
        '''
        self.client.send(('NICK %s\r\n' % nickname).encode())

    def join(self, channel=CHANNEL):
        '''
        join a new channel
        '''
        self.client.send(('JOIN %s\r\n' % CHANNEL).encode())

    def user(self, nickname, realname):
        '''
        tell server the names (the tuple (nickname, realname)) to use
        '''
        names = (nickname, realname)
        self.client.send(('USER %s 0 * :%s\r\n' % names).encode())
        

    def connect(self, server, port, nickname, realname):
        '''
        connect to the server and identify ourselves
        '''
        names = (nickname, realname)
        connection = self.client.connect((server, port))
        self.user(nickname, realname)
        self.nick(nickname)
        self.join(CHANNEL)
        line = ''
        while ' JOIN :' + CHANNEL not in line:
            line = self.stream.readline()
            logging.info('received: %s', line)
        CACHED['irc_id'] = line.split()[0]
        logging.info("CACHED['irc_id'] = %s", CACHED['irc_id'])
        return connection

    def privmsg(self, target, message):
        '''
        simulates typing a message in ircII with no preceding command

        target should be a channel name preceded by '#', or nick

        message should not have any embedded CRLFs, colons (":"), or non-ASCII
        characters.
        '''
        testmsg = ' '.join([CACHED['irc_id'], 'PRIVMSG', target, ':' + message])
        logging.debug('testmsg: %s', testmsg)
        if len(testmsg) <= 510:
            self.client.send(('PRIVMSG %s %s\r\n' % (target, message)).encode())
        else:
            pieces = testmsg[:510].split(':')
            chunklength = len(pieces[-1])
            for chunk in [message[i:i+chunklength]
                          for i in range(0, len(message), chunklength)]:
                logging.debug('sending chunk %s', chunk)
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
            received = self.stream.readline()
            logging.info('received: %r', received)
            words = received.split()
            if words[0] == 'PING':
                pong = received.replace('I', 'O', 1)
                logging.info('sending: %s', pong)
                self.client.send(pong.encode())
            elif words[1] == 'PRIVMSG':
                sender = words[0]
                privacy = 'public' if words[2] == CHANNEL else 'private'
                logging.info('%s message received from %s:', privacy, sender)
                CACHED[sender] += received.split(':')[-1].rstrip()
                # try decoding what we have so far
                logging.debug('attempting to decode %s', CACHED[sender])
                text, okay = decrypt(CACHED[sender].encode())
                logging.debug('text: %s, okay: %s', text, okay)
                if text:
                    CACHED[sender] = ''
                    logging.info('%s message from %s: %s',
                                 privacy, sender, text)
                else:
                    logging.debug("CACHED[%s] now %s", sender, CACHED[sender])
        logging.warning('ircbot terminated from launching thread')

def test(nickname=None, realname=None):
    '''
    run a bot from the command line, for testing
    '''
    try:
        ircbot = IRCBot(nickname=nickname, realname=realname)
        time.sleep(TIMEOUT)
    except KeyboardInterrupt:
        logging.warning('Telling monitor to terminate')
        ircbot.terminate = True

if __name__ == '__main__':
    sys.argv.extend(['', ''])  # in case no args given
    test(nickname=sys.argv[1], realname=sys.argv[2])

#!/usr/bin/python3
'''
IRC communications for server discovery
'''
# pylint: disable=multiple-imports
import sys, os, socket, pwd, threading, time
from kbcommon import CACHED, logging, TO_PAGE
from kbutils import decrypt, check_username

IRCSERVER = 'irc.lfnet.org'
PORT = 6667
CHANNEL = '#kybyz'
BUFFERSIZE = 16 * 1024  # make it big enough to get full banner from IRC server
CRLF = '\r\n'
TIMEOUT = int(os.getenv('KB_DELAY') or 600)
MAXSIZE = 1024 * 1024
MAXCACHE = MAXSIZE * 1024

class IRCBot():
    '''
    Implements IRC client

    see https://www.techbeamers.com/create-python-irc-bot/
    also https://datatracker.ietf.org/doc/html/rfc2812
    '''
    # pylint: disable=too-many-instance-attributes
    def __init__(self, server=IRCSERVER, port=PORT,
                 nickname=None, realname=None):
        '''
        initialize the client
        '''
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # enable keepalives at the socket (SOL_SOCKET) level
        self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # after 1 second of TCP inactivity, trigger keepalive pings
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
        # send a keepalive ping every 60 seconds
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60)
        # quit after 5 consecutive failures
        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
        self.stream = self.client.makefile()
        self.server = server
        self.port = port
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
        self.client.send(('JOIN %s\r\n' % channel).encode())

    def leave(self, channel=CHANNEL):
        '''
        join a new channel
        '''
        self.client.send(('PART %s\r\n' % channel).encode())

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
        connection = self.client.connect((server, port))
        self.user(nickname, realname)
        self.nick(nickname)
        self.join(CHANNEL)
        return connection

    def privmsg(self, target, message):
        '''
        simulates typing a message in ircII with no preceding command

        target should be a channel name preceded by '#', or nick

        message should not have any embedded CRLFs, or non-ASCII characters.
        '''
        sep = '\xa0'  # separates prefix from message
        logging.debug('message: %r', message)
        testmsg = ' '.join([CACHED['irc_id'], 'PRIVMSG', target, sep + message])
        logging.debug('testmsg: %s', testmsg.replace(sep, ':'))
        if len(testmsg) <= 510:
            self.sendchunk(('PRIVMSG %s :%s\r\n' % (target, message)).encode())
        else:
            pieces = testmsg[:510].split(sep)
            chunklength = len(pieces[-1])
            for chunk in [message[i:i+chunklength]
                          for i in range(0, len(message), chunklength)]:
                logging.debug('sending chunk %s', chunk)
                self.sendchunk(
                    ('PRIVMSG %s %s\r\n' % (target, chunk)).encode())

    def sendchunk(self, chunk):
        '''
        send a chunk. it must already be UTF8 encoded
        '''
        sent, tries = False, 0
        while not sent:
            try:
                self.client.send(chunk)
                sent = True
            except BrokenPipeError:
                logging.debug('lost connection, rejoining IRC...')
                self.connection = self.connect(
                    self.server, self.port, self.nickname, self.realname)
                tries += 1
                if tries == 5:
                    raise

    def monitor(self):
        '''
        wait for input. send a PONG for every PING

        intended to run in a daemon thread

        set ircbot.terminate to True in order to shut it down
        '''
        logging.debug('ircbot monitoring incoming traffic')
        while not self.terminate:
            received = self.stream.readline().rstrip()
            logging.info('received: %r, length: %d', received, len(received))
            end_message = len(received) < 510
            # make sure all words[n] references are accounted for
            words = received.split() + ['', '', '']
            nickname, matched = check_username(words[0])
            if words[0] == 'PING':
                pong = received.replace('I', 'O', 1).rstrip() + CRLF
                logging.info('sending: %r', pong)
                self.client.send(pong.encode())
            elif words[1] == 'JOIN' and matched:
                CACHED['irc_id'] = words[0]
                logging.info("CACHED['irc_id'] = %s", CACHED['irc_id'])
            elif words[1] == 'PRIVMSG':
                sender = nickname
                privacy = 'public' if words[2] == CHANNEL else 'private'
                logging.info('%s message received from %s:', privacy, sender)
                # chop preceding ':' from ':this is a private message'
                CACHED[sender] += ' '.join(words[3:])[1:].rstrip()
                # try decoding what we have so far
                logging.debug('attempting to decode %s', CACHED[sender])
                text, trustlevel = decrypt(CACHED[sender].encode())
                logging.debug('text: %s, trustlevel: %s', text, trustlevel)
                if text or end_message:
                    text = text or CACHED[sender][:256].encode()
                    logging.info(
                        '%s %s message from %s: %s', trustlevel,
                        privacy,
                        sender,
                        text.decode().replace('<', '&lt;').replace('>', '&gt;'),
                        **TO_PAGE)
                    CACHED[sender] = ''
                elif len(CACHED[sender]) > MAXSIZE:
                    logging.info(
                        'clearing overflow CACHED[%s]: %r..., length %d',
                        sender, CACHED[sender][:256], len(CACHED[sender]))
                    CACHED[sender] = ''
                else:
                    logging.debug('CACHED[%s] now %r', sender, CACHED[sender])
            clearcache()
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

def clearcache(maxcache=MAXCACHE):
    '''
    delete entries if CACHED size is greater than MAXCACHE

    >>> CACHED.update({':2': 'x' * 1024, ':1': 'y' * 64, ':3': 'z' * 2048})
    >>> logging.debug('sum of lengths: %d', sum(map(len,
    ...  [v for k, v in CACHED.items() if k.startswith(':')])))
    >>> logging.info('doctest CACHED.keys(): %s', list(CACHED.keys()))
    >>> clearcache(100)
    >>> {k: v for k, v in CACHED.items() if k.startswith(':')}
    {':1': 'yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'}
    >>> len(CACHED[':1'])
    64
    '''
    logging.debug('CACHED.keys(): %s', list(CACHED.keys()))
    while sum(map(len, [v for k, v in CACHED.items()
                        if k.startswith(':')])) > maxcache:
        next_biggest = max({k: v for k, v in CACHED.items()
                            if k.startswith(':')},
                           key=lambda k: len(CACHED[k]))
        logging.debug('next_biggest: %s', next_biggest)
        logging.warning('deleting CACHED[%s] of length %d', next_biggest,
                        len(CACHED[next_biggest]))
        del CACHED[next_biggest]

if __name__ == '__main__':
    sys.argv.extend(['', ''])  # in case no args given
    test(nickname=sys.argv[1], realname=sys.argv[2])

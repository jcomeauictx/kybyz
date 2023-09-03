#!/usr/bin/python3
'''
made for developing without functional python-gnupg package

this is probably not needed. I didn't realize that `gnupg` and `python-gnupg`
were two separate PyPI (pip) packages until Ildar told me -- jc
'''
import subprocess, re  # pylint: disable=multiple-imports
from kbcommon import logging

logging.warning('Using primitive GPG functionality')

def run_process(command, **kwargs):
    '''
    implementation of subprocess.run for older Python3

    https://pymotw.com/3/subprocess/
    '''
    text_input = kwargs.get('input', None)
    capture_output = kwargs.get('capture_output', False)
    logging.debug('capture_output %s ignored', capture_output)
    timeout = kwargs.get('timeout', None)
    check = kwargs.get('check', None)
    if timeout:
        raise NotImplementedError('"timeout" not supported')
    # pylint: disable=bad-option-value, consider-using-with
    process = subprocess.Popen(
        command,
        stdin=kwargs.get('stdin', subprocess.PIPE),
        stdout=kwargs.get('stdout', subprocess.PIPE),
        stderr=kwargs.get('stderr', subprocess.PIPE),
        # pylint: disable=bad-option-value, consider-using-dict-items
        **{k: kwargs[k] for k in kwargs if k not in
           ['input', 'capture_output', 'timeout', 'check']}
    )
    stdout, stderr = process.communicate(text_input)
    if check and process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command,
                                            output=(stdout, stderr))
    return type('', (), {
        'stdout': stdout,
        'stderr': stderr,
    })

class GPG():
    '''
    drop-in replacement for python3-gnupg class

    limited to the few calls that kybyz makes,
    and only for English language, among other limitations.
    '''
    def __init__(self, options=None):
        '''
        add subprocess.run replacement if it doesn't exist
        '''
        if not hasattr(subprocess, 'run'):
            subprocess.run = run_process
        else:
            try:
                subprocess.run(['ls'], capture_output=True, check=True)
            except TypeError:  # Python3.5
                subprocess.run = run_process
        options = options or []
        self.defaultkey = None
        if len(options) >= 2 and options[0] == '--default-key':
            self.defaultkey = options[1]

    def sign(self, data, keyid=None):
        '''
        gpg sign given data

        unlike python-gnupg, return as binary data

        NOTE: side effect: sets self.defaultkey if not set by constructor
        '''
        self.defaultkey = self.defaultkey or keyid
        command = ['gpg', '--sign']
        if self.defaultkey:
            command.extend(['--default-key', self.defaultkey])
        run = subprocess.run(
            command,
            input=data,
            capture_output=True,
            check=True)
        run.data = run.stdout
        return run

    def encrypt(self, data, recipients, **kwargs):
        '''
        gpg encrypt data for recipients
        '''
        self.defaultkey = self.defaultkey or kwargs.get('keyid', None)
        command = ['gpg', '--encrypt']
        if self.defaultkey:
            command.extend(['--defaultkey', self.defaultkey])
        for recipient in recipients:
            command.extend(['-r', recipient])
        if kwargs.get('sign', None):
            command.append('--sign')
        if kwargs.get('armor', None):
            command.append('--armor')
        run = subprocess.run(command, input=data,
                             capture_output=True, check=False)
        run.data = run.stdout
        return run

    def decrypt(self, data, keyid=None):
        '''
        gpg decrypt data
        '''
        self.defaultkey = self.defaultkey or keyid
        command = ['gpg', '--decrypt']
        if self.defaultkey:
            command.extend(['--default-key', self.defaultkey])
        run = subprocess.run(
            command,
            input=data,
            capture_output=True,
            check=False)
        run.data = run.stdout
        logging.debug('decrypt stderr: %s', run.stderr)
        output = list(filter(None, run.stderr.decode().split('\n')))
        logging.debug('looking for username and trust_text in %s',
                      output[-1])
        try:
            run.username, run.trust_text = re.compile(
                r'^gpg: Good signature from "([^"]+)" \[([^]]+)\]$').match(
                    output[-1]).groups()
        except AttributeError:
            run.username = run.trust_text = None
        return run

    def verify(self, signed):
        '''
        verify signature on given signed data
        '''
        run = subprocess.run(['gpg', '--verify'], input=signed,
                             capture_output=True, check=False)
        output = run.stderr.decode().split('\n')
        combined = ' '.join(output)
        try:
            run.timestamp = re.compile(
                r'^gpg: Signature made (.*?)(?: using .*)?$').match(
                    output[0]).groups()[0]
            # NOTE: `self` added to following log simply to defeat
            # recent `no-self-use` addition to pylint
            logging.debug('%s: run.timestamp: %s', self, run.timestamp)
            run.key_id = re.compile(
                r' using RSA key (?:ID )?([0-9A-F]{8,40})\s').search(
                    combined).groups()[0]
            logging.debug('run.key_id: %s', run.key_id)
            pattern = re.compile(
                r' Good signature from "([^"]+)"(?: \[([^]]+)\])?')
            logging.debug('pattern: %s', pattern)
            run.username, run.trust_text = pattern.search(combined).groups()
            logging.debug('run.username: %s, run.trust_text: %s',
                          run.username, run.trust_text)
        except (AttributeError, IndexError) as problem:
            logging.exception('did not find needed data in %r', combined)
            raise problem
        return run

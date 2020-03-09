#!/usr/bin/python
'''
This class allows you to run commands on a remote host and provide
input if necessary.

VERSION 1.2
'''
import paramiko
import logging
import socket
import time
import datetime
import re
import numpy as np

import pickle

import sys, os, re, string, curses
from optparse import OptionParser
import ConfigParser
from multiprocessing.pool import ThreadPool
from collections import defaultdict


#CONSTANTS
IPV4 = socket.AF_INET
TCP = socket.SOCK_STREAM
PORT = 1234

# ================================================================
# class MySSH
# ================================================================
class MySSH:
    '''
    Create an SSH connection to a server and execute commands.
    Here is a typical usage:

        ssh = MySSH()
        ssh.connect('host', 'user', 'password', port=22)
        if ssh.connected() is False:
            sys.exit('Connection failed')

        # Run a command that does not require input.
        status, output = ssh.run('uname -a')
        print 'status = %d' % (status)
        print 'output (%d):' % (len(output))
        print '%s' % (output)

        # Run a command that does requires input.
        status, output = ssh.run('sudo uname -a', 'sudo-password')
        print 'status = %d' % (status)
        print 'output (%d):' % (len(output))
        print '%s' % (output)
    '''

    def __init__(self, logger, compress=True):
        '''
        @param compress  Enable/disable compression.
        '''
        self.ssh = None
        self.transport = None
        self.compress = compress
        self.bufsize = 65536

        self.info = logger.info
        self.debug = logger.debug
        self.error = logger.error

    def __del__(self):
        if self.transport is not None:
            self.transport.close()
            self.transport = None

    def connect(self, hostname, username, password, port=22):
        '''
        Connect to the host.

        @param hostname  The hostname.
        @param username  The username.
        @param password  The password.
        @param port      The port (default=22).

        @returns True if the connection succeeded or false otherwise.
        '''
        self.debug('connecting %s@%s:%d' % (username, hostname, port))
        self.hostname = hostname
        self.username = username
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(hostname=hostname,
                             port=port,
                             username=username,
                             password=password)
            self.transport = self.ssh.get_transport()  #
            self.transport.use_compression(self.compress)  #
            self.info('succeeded: %s@%s:%d' % (username,
                                               hostname,
                                               port))
        except socket.error as e:
            self.transport = None
            self.error('failed: %s@%s:%d: %s' % (username,
                                                 hostname,
                                                 port,
                                                 str(e)))
        except paramiko.BadAuthenticationType as e:
            self.transport = None
            self.error('failed: %s@%s:%d: %s' % (username,
                                                 hostname,
                                                 port,
                                                 str(e)))

        return self.transport is not None  # return true if self.transport has a value

    def run(self, cmd, input_data=' ', timeout=10):
        '''
        Run a command with optional input data.

        Here is an example that shows how to run commands with no input:

            ssh = MySSH()
            ssh.connect('host', 'user', 'password')
            status, output = ssh.run('uname -a')
            status, output = ssh.run('uptime')

        Here is an example that shows how to run commands that require input:

            ssh = MySSH()
            ssh.connect('host', 'user', 'password')
            status, output = ssh.run('sudo uname -a', '<sudo-password>')

        @param cmd         The command to run.
        @param input_data  The input data (default is None).
        @param timeout     The timeout in seconds (default is 10 seconds).
        @returns The status and the output (stdout and stderr combined).
        '''
        self.debug('running command: (%d) %s' % (timeout, cmd))

        if self.transport is None:
            self.error('no connection to %s@%s:%s' % (str(self.username),
                                                      str(self.hostname),
                                                      str(self.port)))
            return -1, 'ERROR: connection not established\n'

        # Fix the input data.
        input_data = self._run_fix_input_data(input_data)

        # Initialize the session.
        self.debug('initializing the session')
        session = self.transport.open_session()
        session.set_combine_stderr(True)
        session.get_pty()  # height=1000)
        # session.exec_command(cmd)
        session.invoke_shell()
        session.send(cmd)
        session.send('\n')
        output, status = self._run_poll(session, timeout, input_data)
        # status = session.recv_exit_status()
        self.debug('output size %d' % (len(output)))
        self.debug('status %d' % (status))
        return status, output

    def connected(self):
        '''
        Am I connected to a host?

        @returns True if connected or false otherwise.
        '''
        return self.transport is not None

    def _run_fix_input_data(self, input_data):
        '''
        Fix the input data supplied by the user for a command.

        @param input_data  The input data (default is None).
        @returns the fixed input data.
        '''
        if input_data is not None:
            if len(input_data) > 0:
                if '\\n' in input_data:
                    # Convert \n in the input into new lines.
                    lines = input_data.split('\\n')
                    input_data = '\n'.join(lines)
            return input_data.split('\n')
        return []

    def _run_send_input(self, session, stdin, input_data):
        '''
        Send the input data.

        @param session     The session.
        @param stdin       The stdin stream for the session.
        @param input_data  The input data (default is None).
        '''
        if input_data is not None:
            # self.info('session.exit_status_ready() %s' % str(session.exit_status_ready()))
            self.error('stdin.channel.closed %s' % str(stdin.channel.closed))
            if stdin.channel.closed is False:
                self.debug('sending input data')
                stdin.write(input_data)

    def _run_poll(self, session, timeout, input_data, prompt=[' > ', ' # ']):
        '''
        Poll until the command completes.

        @param session     The session.
        @param timeout     The timeout in seconds.
        @param input_data  The input data.
        @returns the output
        '''

        def check_for_prompt(output, prompt):
            for prmt in prompt:
                # Only check last 3 characters in return string
                if output[-3:].find(prmt) > -1:
                    return True
            return False

        interval = 0.1
        maxseconds = timeout
        maxcount = maxseconds / interval

        # Poll until completion or timeout
        # Note that we cannot directly use the stdout file descriptor
        # because it stalls at 64K bytes (65536).
        input_idx = 0
        timeout_flag = False
        self.debug('polling (%d, %d)' % (maxseconds, maxcount))
        start = datetime.datetime.now()
        start_secs = time.mktime(start.timetuple())
        output = ''
        session.setblocking(0)
        status = -1
        while True:
            if session.recv_ready():
                data = session.recv(self.bufsize)
                self.debug(repr(data))
                output += data
                self.debug('read %d bytes, total %d' % (len(data), len(output)))

                if session.send_ready():
                    # We received a potential prompt.
                    # In the future this could be made to work more like
                    # pexpect with pattern matching.

                    # If 'lines 1-45' found in ouput, send space to the pty
                    # to trigger the next page of output. This is needed if
                    # more that 24 lines are sent (default pty height)
                    pattern = re.compile('lines \d+-\d+')

                    if re.search(pattern, output):
                        session.send(' ')
                    elif input_idx < len(input_data):
                        data = input_data[input_idx] + '\n'
                        input_idx += 1
                        self.debug('sending input data %d' % (len(data)))
                        session.send(data)

            # exit_status_ready signal not sent when using 'invoke_shell'
            # self.info('session.exit_status_ready() = %s' % (str(session.exit_status_ready())))
            # if session.exit_status_ready():
            if check_for_prompt(output, prompt) == True:
                status = 0
                break

            # Timeout check
            now = datetime.datetime.now()
            now_secs = time.mktime(now.timetuple())
            et_secs = now_secs - start_secs
            self.debug('timeout check %d %d' % (et_secs, maxseconds))
            if et_secs > maxseconds:
                self.debug('polling finished - timeout')
                timeout_flag = True
                break
            time.sleep(0.200)

        self.debug('polling loop ended')
        if session.recv_ready():
            data = session.recv(self.bufsize)
            output += data
            self.debug('read %d bytes, total %d' % (len(data), len(output)))

        self.debug('polling finished - %d output bytes' % (len(output)))
        if timeout_flag:
            self.debug('appending timeout message')
            output += '\nERROR: timeout after %d seconds\n' % (timeout)
            session.close()

        return output, status

# ================================================================
# FUNCTIONS
# ================================================================
def ssh_conn(hostname):
    ssh = MySSH(logger)
    ssh.connect(hostname=hostname,
                username=username,
                password=password,
                port=port)
    if ssh.connected() is False:
        logger.error('Connection failed.')
        return hostname
    return ssh


def rem_extra_chars(in_str):
    pat = re.compile('lines \d+-\d+ ')
    in_str = re.sub(pat, '', in_str)
    pat = re.compile('lines \d+-\d+\/\d+ \(END\) ')
    in_str = re.sub(pat, '', in_str)
    return in_str.replace('\r', '')


def run_cmd(ssh_obj, cmd, indata=None, enable=False):
    '''
    Run a command with optional input.

    @param cmd    The command to execute.
    @param indata The input data.
    @returns The command exit status and output.
             Stdout and stderr are combined.
    '''
    prn_cmd = cmd
    cmd = 'terminal type dumb\n' + cmd
    if enable:
        cmd = 'enable\n' + cmd

    output = ''
    output += ('\n' + '=' * 64 + '\n')
    output += ('host    : ' + ssh_obj.hostname + '\n')
    output += ('command : ' + prn_cmd + '\n')
    status, outp = ssh_obj.run(cmd, indata, timeout=10)
    output += ('status  : %d' % (status) + '\n')
    output += ('output  : %d bytes' % (len(output)) + '\n')
    output += ('=' * 64 + '\n')
    outp = rem_extra_chars(outp)
    output += outp
    return output


def run_threaded_cmd(ssh_list, cmd, enable=False):
    '''
    Run threaded command on all clients in ssh_list
    '''
    thread_obj = [0] * len(ssh_list)
    pool = ThreadPool(processes=len(ssh_list))
    output = []
    for i, ssh_obj in enumerate(ssh_list):
        thread_obj[i] = pool.apply_async(run_cmd, args=(ssh_obj, cmd), kwds={'enable': enable})
    for i, ssh_obj in enumerate(ssh_list):
        output.append(thread_obj[i].get())
    pool.close()
    pool.join()
    return [x.split('\n') for x in output]


def close_ssh(ssh_list):
    thread_obj = [0] * len(ssh_list)
    pool = ThreadPool(processes=len(ssh_list))
    logger.info('Closing SSH connections')
    for i, ssh_obj in enumerate(ssh_list):
        thread_obj[i] = pool.apply_async(ssh_obj.ssh.close)
    for i, ssh_obj in enumerate(ssh_list):
        thread_obj[i].get()
    pool.close()
    pool.join()


# Natural sort
def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    last element in return value is empty string if last value in string is a digit
    '''
    value = [atoi(c) for c in re.split('(\d+)', text)]
    return value


def get_rates(switch_dict, ssh_list):

    # Get switch rates:
    speed_exp = ['B/s', 'KB/s', 'MB/s', 'GB/s']
    cmd = 'show interface ethernet rates'
    good_output = False
    # timeout = 5
    # while not good_output and timeout > 0:
    try:
        all_output = run_threaded_cmd(ssh_list, cmd)
        for output in all_output:
            sw_name_idx = [i for i, s in enumerate(output) if 'CBFSW' in s][0]
            sw_name = output[sw_name_idx].split(' ')[0].split('-')[-1]
            rates = [filter(None, output[y].split(' ')) for y in [i for i, s in enumerate(output) if 'Eth' in s]]
            for line in rates:
                eth = line[0]
                egress = float(line[1]) * (1000 ** (speed_exp.index(line[2])))
                ingress = float(line[4]) * (1000 ** (speed_exp.index(line[5])))
                switch_dict[sw_name][eth]['egress'] = egress
                switch_dict[sw_name][eth]['ingress'] = ingress
        good_output = True
    except (ValueError, IndexError):
        pass
        #        timeout -= 1
    # if timeout == 0:
    #    logger.error('Malformed switch output... trying again')

    # Create rates matrix
    cols = len(switch_dict.keys()) + 1
    if opts.display == 'spines':
        lines = mleaves * 2 + 1
    else:
        # Find how many ethernet ports there are on the leavs
        port_list = []
        lines = 0
        for k, v in switch_dict.iteritems():
            for port in v.keys():
                try:
                    port_list.index(port)
                except ValueError:
                    port_list.append(port)
        port_list = sorted(port_list, key=natural_keys)
        lines = len(port_list) * 2 + 1
    matrix = [[0 for x in range(cols)] for y in range(lines)]
    try:
        sorted_swlist = sorted(switch_dict.keys(), key=natural_keys)
        first_sw = int(natural_keys(sorted_swlist[0])[-2])
    except (ValueError, IndexError):
        logger.error('Switch name not end in a number: {}'.format(first_sw))
        close_ssh(ssh_list)
        raise ValueError
    for switch in switch_dict.keys():
        idx = sorted_swlist.index(switch) + 1
        for port, data in switch_dict[switch].iteritems():
            if opts.display == 'spines':
                if data.has_key('remote_switch'):
                    rem_sw = re.split('(\d+)', data['remote_switch'])
                    try:
                        rem_sw_nr = int(rem_sw[-2])
                    except (ValueError, IndexError):
                        logger.error('Remote switch name from LLDP does not end in a number: {}'.format(
                            data['remote_switch']))
                        close_ssh(ssh_list)
                        raise ValueError
                    try:
                        matrix[0][idx] = switch
                        matrix[rem_sw_nr * 2 - 1][idx] = data['egress']
                        matrix[rem_sw_nr * 2][idx] = data['ingress']
                        matrix[rem_sw_nr * 2 - 1][0] = 'L' + str(rem_sw_nr) + ' out'
                        matrix[rem_sw_nr * 2][0] = 'L' + str(rem_sw_nr) + '  in'
                    except IndexError:
                        pass
            else:
                try:
                    port_idx = port_list.index(port) + 1
                    matrix[0][idx] = switch
                    matrix[port_idx * 2 - 1][idx] = data['ingress']
                    matrix[port_idx * 2][idx] = data['egress']
                    matrix[port_idx * 2 - 1][0] = port[3:] + ' out'
                    matrix[port_idx * 2][0] = port[3:] + '  in'
                except IndexError:
                    pass
    return matrix

# ================================================================
# MAIN
# ================================================================
if __name__ == '__main__':


    desc = """This programs connects to Mellanox switches via SSH and maps connections
              between switches and hosts using LLDP. Switch rates are read and displayed
              in a matrix.
           """
    parser = OptionParser(description=desc)
    parser.set_usage('%prog [options]')
    parser.add_option('-l', dest='loglevel', type=str, default='INFO',
                      help='Log level: DEBUG,INFO,ERROR,WARINING,FATAL. Default = INFO')
    parser.add_option('-a', '--maxleaves', type=int, default=36,
                      help='Number of leaf switches in the system.')
    parser.add_option('-p', '--maxspines', type=int, default=18,
                      help='Number of spine switches in the system.')
    parser.add_option('-n', '--numsw', type=int, default=36,
                      help='Number of switches to process.')
    parser.add_option('-t', '--startswitch', type=int, default=1,
                      help='Start displaying from specified switch.')
    parser.add_option('-d', '--display', type=str, default='leaves', #default of spines changed to leaves
                      help='Display spines or leaves.')
    opts, args = parser.parse_args()

    # Setup the logger
    loglevel = opts.loglevel
    logger = logging.getLogger('mellanox_switch_comms')
    level = logging.getLevelName(loglevel)
    logger.setLevel(level)
    # fmt = '%(asctime)s %(funcName)s:%(lineno)d %(message)s'
    fmt = '%(asctime)s %(levelname)s: %(message)s'
    date_fmt = '%Y-%m-%d %H:%M:%S'
    logging_format = logging.Formatter(fmt, date_fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(logging_format)
    handler.setLevel(level)
    logger.addHandler(handler)

    port = 22
    username = 'monitor'
    password = 'monitor'
    sudo_password = password  # assume that it is the same password
    hosts = []
    strsw = opts.startswitch
    numsw = opts.numsw
    mspines = opts.maxspines
    mleaves = opts.maxleaves
    if opts.display == 'spines':
        if strsw + numsw > mspines + 1:
            rng = mspines + 1
        else:
            rng = strsw + numsw

        for i in range(strsw, rng):
            hosts.append('cbfsw-s{}.cbf.mkat.karoo.kat.ac.za'.format(i))
    else:
        if strsw + numsw > mleaves + 1:
            rng = mleaves + 1
        else:
            rng = strsw + numsw
        for i in range(strsw, rng):
            hosts.append('cbfsw-l{}.cbf.mkat.karoo.kat.ac.za'.format(i))

    # Main Code
    # Open SSH connections to all host
    exit = False
    while not exit:  # while exit is not True, while exit is False
        full_ssh_list = []
        thread_obj = [0] * len(hosts)  # creates list of zeros
        pool = ThreadPool(processes=len(hosts))  # create pool object
        logger.info('Opening ssh connections.')
        for i, host in enumerate(hosts):
            thread_obj[i] = pool.apply_async(ssh_conn, args=(host,))
        for i, host in enumerate(hosts):
            full_ssh_list.append(thread_obj[i].get())
        pool.close()
        pool.join()
        ssh_list = []
        for i, ssh_obj in enumerate(full_ssh_list):
            if type(ssh_obj) == str:
                logger.error('Connection to {} failed.'.format(ssh_obj))
            else:
                ssh_list.append(ssh_obj)
        logger.info('SSH connections established.')

        # Map switches:
        logger.info('Mapping switch connections using LLDP')
        # Create 3 level dictionary for switch info
        switch_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        cmd = 'show lldp interfaces ethernet remote | include "Eth|Remote system name"'
        all_output = run_threaded_cmd(ssh_list, cmd)
        new_ssh_list = []
        for output in all_output:
            try:
                host_name = None
                for ln in output:
                    if 'host ' in ln:
                        host_name = ln.split()[2]
                sw_name_idx = [i for i, s in enumerate(output) if 'CBFSW' in s][0]
                sw_name = output[sw_name_idx].split(' ')[0].split('-')[-1]
                rem_port_id = [i for i, v in enumerate(output) if 'Remote port-id' in v]
                for idx in rem_port_id:
                    eth = output[idx - 1]
                    remote = output[idx + 1].split(' ')[-1]
                    switch_dict[sw_name][eth]['remote_switch'] = remote
                for ssh_obj in ssh_list:
                    if ssh_obj.hostname == host_name:
                        new_ssh_list.append(ssh_obj)

            except IndexError:
                if host_name:
                    logger.error('Switch output malformed for {}:\n{}'.format(host_name, output))
                else:
                    logger.error('Switch output malformed while mapping switches: {}'.format(output))
                _null = raw_input("Press any key to continue...")
        logger.info('Done mapping switches.')


        # creates list from list of objects in new_ssh_list - IJ
        ssh_list_values = []
        for ssh_obj in new_ssh_list:
            ssh_list_values.append(ssh_obj.hostname)
        print 'ssh_list_values: ', ssh_list_values

        # converts 3-level default dictionary into standard python 3-level dictionary - IJ
        switch_dict_undefault = dict(switch_dict)  # level1
        for k, v in switch_dict_undefault.items():
            for k2, v2 in v.items():
                switch_dict_undefault[k][k2] = dict(v2)  # level3
            switch_dict_undefault[k] = dict(v)  # level 2
        print 'switch_dict_undefault: ', switch_dict_undefault

        #############################################################
        # construct message with header + id + data - IJ
        #############################################################

        HEADERSIZE = 10
        IDSIZE = 5

        s = socket.socket(IPV4, TCP)  # create socket object
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # allows reuse of address and port

        try:
            print 'Server started...\nPress ctrl+c to exit'
            s.bind(('0.0.0.0', PORT))  # Binding to '0.0.0.0' or '' allows connections from any IP address:
            s.listen(5)  # queue of 5
            logger.debug('Socket is listening.')

            clientsocket, address = s.accept()  # accept connection from client
            logger.debug('Connection accepted from %s port %s', address, PORT)
            # clientsocket.send(bytes(msg, "utf-8"))  # send message
            while True:
                start = time.time()
                matrix = get_rates(switch_dict, new_ssh_list)
                end = time.time()
                print end - start
                msg3 = pickle.dumps(matrix)  # pickles matrix
                msg3 = 'ID01'.ljust(IDSIZE) + msg3  #
                msg3 = str(len(msg3)).ljust(HEADERSIZE) + msg3  # header and id added to data
                clientsocket.send(msg3)  # send message
                print 'msg sent'
                logger.debug('Message3 sent to client.')

        except socket.error as e:
            print "Socket Error: %s" % e
            logger.debug("Socket Error: %s" % e)
        except KeyboardInterrupt as e:
            print("KeyboardInterrupt has been caught.")
            logger.debug("Keyboard Error: %s" % e)
        except Exception as e:
            print "Generic error: %s" % e
            logger.debug("Generic Error: %s" % e)
        finally:
            s.close()
            logger.debug('Socket closed')

        #############################################################

        # curses.wrapper(draw, switch_dict, new_ssh_list)

        exit = True

        close_ssh(ssh_list)


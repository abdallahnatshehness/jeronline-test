#!/usr/bin/env python

import os
import sys
import time
import psutil
import threading
from multiprocessing.dummy import Pool
import queue
import subprocess as sub
from colorama import Fore, Style


from infra.decorators import retry
from infra import custom_exceptions as ce
from infra import logger, reporter
log = logger.get_logger(__name__)
flushed_q = queue.Queue()

__author__ = 'Amr.Shaloudi'


def main():
    for i in range(100):
        sudo_sub_popen('echo', apass='_AutoUser1_')


def sub_popen(*cmd_args, **kwargs):
    '''
    The function opens a subprocess Pipe and uses communicate() to wait until the executable is done.
    If the return code of the executable != 0 an exception is raised using stderr as the message, otherwise the function returns the stdout of the executable.
    The exception will include the process returncode.
    If the return code is 0 but the stderr is not empty, the stderr will be written as an error log message.
    The function also used a timer which can kill the executable and raise WETimeOutError if the timer is done before the executable is finished.

    Optional arguments:
        initial_path - Changes the current working directory to the path before running the process, and changing back when process is finished.
        return_err - if True, err will be returned in addition to output. (return value - output, err)
    '''
    return_err = kwargs.pop('return_err', False)
    org_path = os.getcwd()
    initial_path = kwargs.pop('initial_path', None)

    if initial_path is not None:
        os.chdir(initial_path)
    try:
        p = Popen(*cmd_args, **kwargs)
    except OSError as e:
        raise ce.MJRunTimeError(e) from e
    else:
        if kwargs.get('no_wait'):
            p.timer.cancel()
            # returning popen object
            return p
        else:
            output, err = p.communicate()  # Waiting for process to finish
            if return_err:
                return output, err
            else:
                return output
    finally:
        os.chdir(org_path)


@retry(3, ce.MJRunTimeError, delay=3)  # to avoid 'sudo: 4294967295: invalid value\n sudo: error initializing audit plugin sudoers_audit'
def sudo_sub_popen(*cmd_args, **kwargs):
    '''A function that opens two pipes and runs a command with arguments with admin privileges.
The first pipe stores the the admin password, the second pipe runs the command in 'sudo'.
Raises an exception on error, and returns stdout.'''

    if kwargs.get('apass') is None:
        raise ce.MJValueError('No sudo password was supplied')
    pin = sub.Popen(['echo', str(kwargs.pop('apass'))], stdout=sub.PIPE)
    kwargs['p_stdin'] = pin.stdout
    return sub_popen('sudo', '-S', '-k', '-p', '', *cmd_args, **kwargs)



def sub_popen_thread(*args, **kwargs):
    '''Opens a pipe using a thread. This is needed for applications that constantly write to the console and can create a deadlock in python.'''
    no_wait = kwargs.get('no_wait', False)  # Storing no_wait value for later use
    kwargs['no_wait'] = False  # Disabling no_wait so sub_popen will not return, which causes a deadlock
    th = threading.Thread(target=sub_popen, args=args, kwargs=kwargs, name=f'sub_process: {args[0]}')
    log.debug('Command: %s %s' % (kwargs.get('stdin', ''), ' '.join(args)))
    th.start()
    if not no_wait:  # Waiting for thread to end if requested
        th.join()
    return th


class MultiProcessRunner(object):
    '''A class that can run multiple processes using a pool'''
    def __init__(self, max_processes=8):
        self.process_dict = {}
        log.info('Creating process pool - %s' % max_processes)
        self.pool = Pool(processes=max_processes)

    def add_processes(self, cmds_dict, wait=False):
        """
        Adds processes to the pool.
        :param cmds_dict - A dictionary that includes the id of the process (key) and the command arguments (value)
        :param wait - if true, wait for all processes to complete
        """
        results = []
        for pid, cmd_dict in list(cmds_dict.items()):
            if pid in self.process_dict:
                raise ce.MJValueError('%s id already exists in process dictionary - %s' % (pid, cmd_dict['args']))
            self.process_dict[pid] = {'finished': False}
            res = self.pool.apply_async(self._execute_process, args=(pid, cmd_dict['args']), kwds=cmd_dict.get('kwargs', {}))
            results.append(res)
        if wait:
            [res.wait() for res in results]

    def _execute_process(self, pid, cmd_args, **kwargs):
        '''
        Executes a single process and stores the result in the class's process dictionary.
        The result is a dictionary in the following format: {'id': pid, 'returncode': proc.returncode, 'output': output, 'err': err}
        In case of an exception (Popen creation failure or timeout) the returncode is None
        '''
        try:
            start_time = time.time()
            func = kwargs.get('run_func', None)
            if func is None:
                self.process_dict[pid] = self._run_popen(start_time, *cmd_args, **kwargs)
            else:
                self.process_dict[pid] = self._run_func(start_time, *cmd_args, **kwargs)
        except Exception as e:
            self.process_dict[pid] = {'finished': True, 'returncode': None, 'output': '', 'err': e, 'process_time': None}

    def _run_popen(self, start_time, *cmd_args, **cmd_kwargs):
        proc = Popen(*cmd_args, check_returncode=False, **cmd_kwargs)
        output, err = proc.communicate(timeout=cmd_kwargs.get('timeout'))
        return {'finished': True, 'returncode': proc.returncode, 'output': output, 'err': err,
                'process_time': time.time() - start_time}

    def _run_func(self, start_time, *cmd_args, **cmd_kwargs):
        func = cmd_kwargs['run_func']
        run_kwargs = {key: val for key, val in cmd_kwargs.items() if key != 'run_func'}
        output = func(*cmd_args, **run_kwargs)
        return {'finished': True, 'returncode': 0, 'output': output, 'err': '', 'process_time': time.time() - start_time}

    def poll_processes(self):
        '''
        A polling function that blocks the process until all processes are finished and the result is returned.
        For any process id that is finished, the function yields the process dict that was created by the execution function
        '''
        pids = list(self.process_dict.keys())
        active_ids = pids[:]
        while active_ids:
            for pid in pids:
                if self.process_dict[pid]['finished']:
                    proc_dict = self.process_dict.pop(pid)
                    active_ids.remove(pid)
                    yield pid, proc_dict
            if len(active_ids) < len(pids):
                pids = active_ids[:]


def get_stdout_q_gen(th):
    '''A generator function that fetches the stdout from the flushed q and yields the values.
    The generator runs in a loop as long as the thread is not empty, then it yields all remaining items in the q'''
    while th.isAlive():
        try:
            yield flushed_q.get_nowait()
        except queue.Empty:
            pass
    while not flushed_q.empty():  # Emptying the rest of the q after the thread is finished
        yield flushed_q.get_nowait()


def clear_stdout_q():
    '''Emptying flushed output q'''
    with flushed_q.mutex:
        flushed_q.queue.clear()


def filter_stderr(std_err):
    return '\n'.join([i for i in std_err.split('\n') if 'Which one is undefined.' not in i])


class Popen(psutil.Popen):
    '''A class that extends the Popen class
        cmd_args - A list of command line arguments, including the executable command itself.
                   The list can also be one long string instead of an actual list. This is necessary if running commands in Windows that include quotation marks "
                   For example: 'Msiexec.exe /a "%s" /qn TARGETDIR="%s"' % (installer_path, destination_path)
    Optional arguments:
        shell - This flag enables shell mode when opening pipes. This flag is not advised.
                Invoking via the shell does allow you to expand environment variables and file globs according to the shell's usual mechanism.
                On POSIX systems, the shell expands file globs to a list of files.
                On Windows, a file glob (e.g., "*.*") is not expanded by the shell, anyway (but environment variables on a command line are expanded by cmd.exe).
        input - Any input that the command might require (using the command prompt).
                If input is set then it will be used as an input to the command.
        p_stdin - Piped stdin - to be used in Popen constructor. This must be a file handle.
                  This can be used to pass a sudo password (see sudo_sub_popen).
        no_wait - This flag stops the timer and returns from the function immediately after creating the pipe and running the executable.
                  This is a must for GUI applications on Windows which causes the function to wait until the application quits (or killed).
                  This flag causes the function to return an empty string instead of the stdout.
        no_timer - This flag doesn't start the timer and continues to run the function until the executable is finished.
                   This flag is needed in order that threaded pipes are not killed during process when used in conjunction with no_wait.
        timeout - This argument defines the time required for the executable to finish. If no_timer or no_wait is True then this argument is useless.
        flush_stdout - Flushes the stdout to a q that can be picked up later.
        log_stderr - Writes error log with stderr if not empty.
        no_console - Disables console window opening on Windows (for compiled applications). This is True by default
        check_returncode - Checks the return code and raises an exception if the command failed. This is True by default
    '''

    def __init__(self, *cmd_args, **kwargs):
        self.p_stdin = kwargs.pop('p_stdin', sub.PIPE)
        self.no_wait = kwargs.pop('no_wait', False)
        self.no_timer = kwargs.pop('no_timer', False)
        self.flush_stdout = kwargs.pop('flush_stdout', False)
        self.log_stderr = kwargs.pop('log_stderr', True)
        self.check_returncode = kwargs.pop('check_returncode', True)
        self.no_console = kwargs.pop('no_console', True)
        self.timeout = kwargs.pop('timeout', 60)  # Default timeout
        self.encoding = kwargs.pop('encoding', 'utf-8')
        self.input = kwargs.pop('input', None)
        stdout = kwargs.pop('stdout', sub.PIPE)
        if self.input is not None:
            self.input = str(self.input).encode(self.encoding)
        self.timer = threading.Timer(self.timeout, self.f_timeout)
        self.is_timeout = False

        if sys.platform == 'win32' and self.no_console:
            startupinfo = sub.STARTUPINFO()
            startupinfo.dwFlags |= sub.STARTF_USESHOWWINDOW
        else:
            startupinfo = None
        cmd_args = [none for none in cmd_args if none is not None]  # Removing None arguments from cmd_args
        if len(cmd_args) == 1:
            cmd_args = cmd_args[0]
            self.cmd_string = cmd_args
        else:
            cmd_args = list(map(str, cmd_args))  # Converting all arguments to string
            self.cmd_string = ' '.join(cmd_args)
        try:
            log_level = kwargs.pop('log_level', 'debug')
            log_level = eval(f"log.{log_level}")
            pretty_cmd_args = cmd_args if type(cmd_args) != str else [cmd_args]
            pretty_cmd = ' '.join(['"%s"' % str(z) if ' ' in str(z) else str(z) for z in pretty_cmd_args])
            log_level(f'Command: {pretty_cmd}')
        except Exception as e:
            log.error(f'could not print command {e}')

        self.start_time = time.time()
        super(Popen, self).__init__(cmd_args, stdin=self.p_stdin, stdout=stdout, stderr=sub.PIPE, startupinfo=startupinfo, **kwargs)
        if not self.no_timer:
            self.timer.start()

    def __str__(self):
        if self.input is not None:
            return '%s %s' % (self.input, self.cmd_string)  # Joining stdin with cmd_args to one string
        else:
            return self.cmd_string

    def decode_and_convert_string(self, string):
        try:
            decoded_string = string.decode(self.encoding).replace('<br>', '\n').replace('\r', '').strip()
        except UnicodeDecodeError as e:
            log.warning(f'Failed to decode using {self.encoding}, trying ISO-8859-1')
            decoded_string = string.decode('ISO-8859-1').replace('<br>', '\n').replace('\r', '').strip()
        return decoded_string

    def communicate(self, **kwargs):
        if self.flush_stdout:
            flushed_output = self._do_flush_stdout()
        output, err = (self.decode_and_convert_string(string) for string in self.__subproc.communicate(input=self.input, **kwargs))
        self.timer.cancel()
        # log.debug('Command: - %.2f seconds' % (time.time() - self.start_time))
        if self.is_timeout:
            raise ce.MJTimeOutError('Process timeout occurred (%s sec), Process was terminated. - %s' % (self.timeout, self.cmd_string))

        if self.flush_stdout:
            output = flushed_output
        if self.check_returncode:
            self._do_check_returncode(output, err)

        return output, err

    def _do_check_returncode(self, output, err):
        '''Tests return code of process and raises an exception in case return code is not 0'''
        if self.returncode != 0:  # Process failed
            if err:
                if output:
                    log.info(output)
                msg = err
            elif output:  # In case the process mistakenly wrote to stdout instead of stderr
                msg = output
            else:
                msg = 'Command failed - unknown error (no stderr from process). Return code %s' % self.returncode
            raise ce.MJRunTimeError(msg, returncode=self.returncode, output=output)
        if self.log_stderr and err:
            # patch to go over bad error output
            if 'WARNING:tensorflow' in err:
                log.warning(err)
            elif 'Class ResizeWindow is implemented in both' not in err:
                log.error(err)
            else:
                log.warning(err)

    def f_timeout(self):
        '''Timeout function for running processes'''
        if self.poll() is None:
            try:
                log.debug('Timeout occurred (%s sec), terminating process.' % self.timeout)
                self.is_timeout = True
                for child in self.children(recursive=True):
                    child.kill()
                self.kill()
                self.wait(timeout=60)
            except psutil.NoSuchProcess:
                pass  # Process was finished before the kill process ended
            except psutil.TimeoutExpired:
                raise ce.MJTimeOutError('Process termination timeout occurred (%s sec), Unable to terminate process.' % self.timeout)

    def _do_flush_stdout(self):
        '''A function that flushes stdout to a queue so it can be picked up from another thread.'''
        flushed_list = list()
        while True:
            line = self.stdout.readline().strip().decode(self.encoding)
            log.debug('>>  ' + line)
            flushed_q.put(line)
            flushed_list.append(line)
            if line == '' and self.poll() is not None:
                break
        return '\n'.join(flushed_list)


if __name__ == '__main__':
    main()

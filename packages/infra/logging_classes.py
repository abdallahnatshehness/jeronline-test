#!/usr/bin/env python

from infra import custom_exceptions as ce
import re
import os
import sys
import time
import copy
import inspect
import logging
import logging.handlers
log = logging.getLogger(__name__)


def main():
    '''A Python module that includes custom logging classes.

Written by nira@waves.com'''


class LogWithFailure(logging.Logger):
    '''This class adds a failure message to the logging class.
       Note: This class must be defined first in the file, so logging.setLoggerClass(logging_classes.LogWithFailure) will work.
       Class holds counters for messages per lvl type. There are 2 counter types - global <master> and recent <current>. '''
    logging.FAILURE = 35  # Setting FAILURE level in main logger
    logging.DROP = 33  # Setting DROP level in main logger
    logging.TIMING = 100
    logging.addLevelName(logging.FAILURE, 'FAILURE')  # Setting FAILURE name
    logging.addLevelName(logging.DROP, 'DROP')  # Setting DROP name
    logging.addLevelName(logging.TIMING, 'TIMING')  # Setting DROP name


    master_msg_counter = {}
    for k, v in logging._levelToName.items():
        master_msg_counter[v] = 0
    current_msg_counter = copy.deepcopy(master_msg_counter)

    def __init__(self, name, level=logging.DEBUG, counter_logging_lvl='DROP'):
        logging.Logger.__init__(self, name, level)
        self.counter_logging_lvl = counter_logging_lvl
        self.timing_list = {}

    def makeRecord(self, name, level, *args, **kwargs):
        rv = super().makeRecord(name, level, *args, **kwargs)
        # If msg.lvl is at least the required recording lvl (counter_logging_lvl) - update counters
        if level >= logging._nameToLevel[self.counter_logging_lvl]:
            LogWithFailure.master_msg_counter[logging.getLevelName(level)] += 1
            LogWithFailure.current_msg_counter[logging.getLevelName(level)] += 1
        return rv

    def get_msg_count(self):
        ''' Returns the global <master> counters. '''
        return LogWithFailure.master_msg_counter

    def get_latest_msg_count(self, reset=True):
        # Return only counters for levels at least as self.counter_logging_lvl
        res = {k: v for k, v in LogWithFailure.current_msg_counter.items() if logging._nameToLevel[k] >= logging._nameToLevel[self.counter_logging_lvl]}
        if reset:
            self.reset_latest_msg_count()
        return res

    def reset_latest_msg_count(self):
        for k in LogWithFailure.current_msg_counter.keys():
            LogWithFailure.current_msg_counter[k] = 0

    def fail(self, message, *args, **kwargs):
        if self.isEnabledFor(logging.FAILURE):
            self.log(logging.FAILURE, message, *args, **kwargs)

    def drop(self, message, *args, **kwargs):
        if self.isEnabledFor(logging.DROP):
            self.log(logging.DROP, message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        ex_type, ex_value, ex_traceback = sys.exc_info()
        if ex_type is not None:
            if message == ex_value:
                message = '{}: {}'.format(ex_value.__class__.__name__, ex_value)
            else:
                message = '{}: {}, {}'.format(ex_value.__class__.__name__, ex_value, message)
        super().exception(message, *args, **kwargs)

    def timing(self, name, duration, *args, **kwargs):
        if self.timing_list.get(name):
            self.timing_list[name].append(duration)
        else:
            self.timing_list[name] = [duration]
        if self.isEnabledFor(logging.TIMING):
            self.log(logging.TIMING, f'{name} duration = {duration} seconds', *args, **kwargs)
    #
    # def timeit(method):
    #     def timed(*args, **kw):
    #         ts = time.time()
    #         result = method(*args, **kw)
    #         te = time.time()
    #         log.info()
    #         return result
    #
    #     return timed

class StderrLogger(object):
    '''A class that directs stderr to a log handler'''
    def __init__(self, name, level):
        self.logger = logging.getLogger(name)
        self.level = level

    def write(self, message):
        if message not in ('', '\n', ' '):
            self.logger.log(BaseHandlerPlus.log_lvls[self.level], message)


class BaseHandlerPlus(logging.Handler):
    log_lvls = {'NOTSET': logging.NOTSET,  # 0
                'DEBUG': logging.DEBUG,  # 10
                'INFO': logging.INFO,  # 20
                'WARNING': logging.WARNING,  # 30
                'DROP': logging.DROP,  # 33
                'FAILURE': logging.FAILURE,  # 35
                'ERROR': logging.ERROR,  # 40
                'CRITICAL': logging.CRITICAL,  # 50
                'TIMING': logging.TIMING}  # 100

    def setLevel(self, levelname=None):
        '''
        Override to logging.FileHandler.setLevel.
        If 'log_same_level' is True - Forces the log file handler to include only messages from the same level/type.
        Note, setLevel accepts a string 'levelname' and converts it to int using FileHandlerPlus.log_lvls dictionary.
        If levelname is not supplied, it will use the current levelname (defined in self.__init__), setting only level number.
        '''
        if levelname is not None:  # Setting level name
            self.set_level_name(levelname)

        lvl = BaseHandlerPlus.log_lvls[self.get_level_name()]
        super(BaseHandlerPlus, self).setLevel(lvl)
        if self.log_same_level:
            self.addFilter(SameLevelFilter(lvl))

    def get_level_name(self, lvl=None):
        '''Returns self._levelname, or a levelname of lvl (int) if set'''
        if lvl is None:
            return self._levelname
        else:
            try:
                return [levelname for levelname, levelnum in list(BaseHandlerPlus.log_lvls.items()) if levelnum == lvl][0]
            except IndexError:
                raise ce.WEValueError('Unknown level - %s' % lvl)

    def set_level_name(self, lvl):
        '''Sets self._levelname based on lvl (int)'''
        try:
            self._levelname = [levelname for levelname, levelnum in list(BaseHandlerPlus.log_lvls.items()) if levelnum == lvl][0]
        except IndexError:
            raise ce.WEValueError('Unknown level - %s' % lvl)


class FileHandlerPlus(logging.FileHandler, BaseHandlerPlus):
    '''A file handler object that stores information about the handler.'''

    def __init__(self, path=None, **kwargs):
        '''Instantiates a FileHandler and stores additional arguments:
           path - Path to log file.
           levelname - Sets the log's level. Default is NOTSET
           mode - Setting file mode (write/append). Default is 'w'.
           summary - Printing message type count when running collect_messages. Default is True.
           collect - Printing a collection of each message type to EOF/BOF. when running collect_messages. Default is True.
           use_for_collect - This flag sets the handler to be collected by other log handlers. Default if False.
           tempfile - Creating a temporary log file. This file will be deleted when close_log_hdlrs will run. Default is False.
           log_same_level - The log file will include only messages from the same level/type. This is done to quickly count and collect messages. Default is False.'''

        kwargs['mode'] = kwargs.get('mode', 'w')  # Setting default mode to write
        self._levelname = kwargs.pop('levelname', 'NOTSET')
        self.summary = kwargs.pop('summary', True)
        self.collect = kwargs.pop('collect', True)
        self.tempfile = kwargs.pop('tempfile', False)
        self.log_same_level = kwargs.pop('log_same_level', False)
        self.use_for_collect = kwargs.pop('use_for_collect', False)
        if path is None:
            raise ce.WEValueError('Log path not supplied')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            super(FileHandlerPlus, self).__init__(path, **kwargs)
        except IsADirectoryError:
            time.sleep(3)  # Patch - Sometimes a logfile is shown as a directory, especially when opening a log file on a mounted folder. I suspect that waiting will do the trick.
            super(FileHandlerPlus, self).__init__(path, **kwargs)

    def __str__(self):
        return self._levelname

    def _open(self):
        '''
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        This disables inheritance of the OS of the log file to sub processes.
        This function solves the locking problem that is caused by external processes,
        which prevents the logger of closing the file handler before the external processes.
        '''
        if sys.platform == 'win32' and self.encoding is None:
            import msvcrt
            import _winapi
            import subprocess

            def _make_inheritable(handle):
                """Return a duplicate of handle, which is inheritable"""
                h = _winapi.DuplicateHandle(
                    _winapi.GetCurrentProcess(), handle,
                    _winapi.GetCurrentProcess(), 0, 1,
                    _winapi.DUPLICATE_SAME_ACCESS)
                duplicated_h = subprocess.Handle(h).Detach()
                return duplicated_h

            stream = open(self.baseFilename, self.mode)
            newosf = _make_inheritable(msvcrt.get_osfhandle(stream.fileno()))
            newFD = msvcrt.open_osfhandle(newosf, os.O_APPEND)
            newstream = os.fdopen(newFD, self.mode)
            stream.close()
            return newstream
        else:
            return super(FileHandlerPlus, self)._open()

    def get_messages(self, levelname=None):
        '''A function that parses log files and returns a list of lines that match the requested level'''
        if levelname is None:
            levelname = self.get_level_name()
        filename = os.path.abspath(self.baseFilename)
        if not os.path.exists(filename):
            log.error('Log file not found - %s' % filename)
            return None

        self.flush()
        messages = list()
        with open(filename, 'r') as stream:
            for line in stream:
                if levelname in line:
                    messages.append(line.strip())
        return messages


class RotatingFileHandlerPlus(FileHandlerPlus, logging.handlers.RotatingFileHandler):
    '''A rotating file handler object that stores information about the handler.'''


class QLogHandler(BaseHandlerPlus):
    '''A logging handler that emits a Qt signal. This signal can be connected to other Qt objects to display logging messages
    Instantiates a FileHandler and stores additional arguments:
    q_sig - The QT signal that will be used. The signal needs to have one string argument - QtCore.pyqtSignal(str)
    levelname - Sets the log's level. Default is NOTSET
    log_same_level - The log file will include only messages from the same level/type. This is done to quickly count and collect messages. Default is False.'''

    def __init__(self, **kwargs):
        self.q_sig = kwargs.pop('q_sig')
        self._levelname = kwargs.pop('levelname', 'NOTSET')
        self.log_same_level = kwargs.pop('log_same_level', False)
        super(QLogHandler, self).__init__(**kwargs)

    def emit(self, record):
        msg = self.format(record)
        self.q_sig.emit(str(msg))


class ParentFilter(logging.Filter):
    '''Adds additional info to the log message - stack level, parent info: module, function name, line number.'''
    def filter(self, record):
        record.name = re.sub('.*\.', '', record.name)
        try:
            stack = inspect.stack()
            record.stack_lvl = '  ' * (len(stack) - 8)
            record.parent_mod = inspect.getmodulename(stack[8][1])
            record.parent_func_name = stack[8][3]
            record.parent_line_no = stack[8][2]
        except IndexError:
            record.stack_lvl = None
            record.parent_mod = None
            record.parent_func_name = None
            record.parent_line_no = None
        return True


class SameLevelFilter(logging.Filter):
    '''This filter will force the log file handler to include only messages from the same level/type. This is done to quickly count and collect messages.'''
    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


if __name__ == "__main__":
    main()

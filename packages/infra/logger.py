#!/usr/bin/env python

import os
import sys
import re
from collections import defaultdict, OrderedDict
import logging

from infra import custom_exceptions as ce

logging.getLogger("requests").setLevel(logging.ERROR)  # Disable warning messages from requests module
logging.getLogger("http.cookiejar").setLevel(logging.ERROR)  # Disable debug messages from cookiejar module
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)  # Disable debug messages from connectionpool module
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.ERROR)  # Disable debug messages from connectionpool module
logging.getLogger("selenium.webdriver").setLevel(logging.ERROR)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

from infra import logging_classes

msg_format = '[%(asctime)s.%(msecs)03d]| %(levelname)-7s| %(message)-150s | { %(name)s|%(funcName)s|%(lineno)-3s}|{%(parent_mod)s|%(parent_func_name)s|%(parent_line_no)s}'
hour_format = '%H:%M:%S'
date_format = '%d-%m-%y %H:%M:%S'


def main():
    """
    A Python module to set up a custom logger.
    Written by amr.shaloudi@ness-tech.com
    """
    rep = get_reporter()
    import traceback
    if sys.platform == 'win32':
        user_desktop = os.path.join('C:', os.environ['HOMEPATH'], 'Desktop')
    elif sys.platform == 'darwin':
        user_desktop = os.path.join(os.environ['HOME'], 'Desktop')
    logs_list = [
        {'levelname': 'INFO', 'path': os.path.join(user_desktop, 'logger_test', 'test_log.txt'), 'summary': False,
         'use_for_collect': True},
        {'levelname': 'DEBUG', 'path': os.path.join(user_desktop, 'logger_test', 'debug_log.txt'), 'summary': False},
        {'levelname': 'ERROR', 'path': os.path.join(user_desktop, 'logger_test', 'error_log.txt'), 'tempfile': True,
         'log_same_level': True},
        {'levelname': 'WARNING', 'path': os.path.join(user_desktop, 'logger_test', 'warning_log.txt'),
         'tempfile': False, 'log_same_level': True},
        {'levelname': 'FAILURE', 'path': os.path.join(user_desktop, 'logger_test', 'failure_log.txt'),
         'tempfile': False, 'log_same_level': True},
        {'levelname': 'DROP', 'path': os.path.join(user_desktop, 'logger_test', 'drop_log.txt'), 'tempfile': True,
         'log_same_level': True},
        {'levelname': 'CRITICAL', 'path': os.path.join(user_desktop, 'logger_test', 'critical_log.txt'),
         'tempfile': True, 'log_same_level': True}]

    set_logger(logs_list, debug_to_stdout=True)
    rep.set_hdlr(os.path.join(user_desktop, 'logger_test'), 'report')
    log.fail('A fail message')
    # for i in range(1000000):
    #     log.debug('A debug message')
    # log.drop('A drop message')
    log.info('Some message')
    log.info('-' * 150)
    log.debug('Debug message')
    # log.error('An error!')
    # log.error('An error!')
    log.error('An error!')
    # log.critical('oops')
    log.warning('A warning')

    exit_code = 0
    try:
        # raise SystemExit
        pass
        raise ce.MJIOError('oops')
    except Exception as e:
        exit_code = 3
        # if not isinstance(e, SystemExit):
        #     log.warning('%s: %s\n%s' % (e.__class__.__name__, e, traceback.format_exc()))
        # else:
        log.critical('%s: %s\n%s' % (e.__class__.__name__, e, traceback.format_exc()))
    finally:
        return collect_messages_and_exit(exit_code)


def get_logger(name):
    '''Sets logging class as LogWithFailure and returns logger object from logging'''
    logging.setLoggerClass(logging_classes.LogWithFailure)
    return logging.getLogger(name)


def get_reporter():
    """A function that helps avoid import loop. Should be called from in the code and not from the module level"""
    import reporter
    return reporter.get_reporter()


log = get_logger(__name__)


def set_logger(logs_list=None, name=None, debug_to_stdout=False, quiet=False,
               stderr_level=None):
    '''Sets up a logger when called.
It receives a list of dictionaries. Each dict will be used to define different arguments for the logfile:
Arguments:
    name - Name of logger object. This will enable logging to multiple handlers from multiple loggers.
    debug_to_stdout - writes debug messages to standard output
    quiet - cancel stream handler, doesn't print anything to screen
    stderr_level - Sets log level for stderr stream. Type is integer (like logging.INFO) or string representation ('INFO')
                    By default logging to stderr is disabled (level is set to 100). Please use only for debug.

log dict arguments:
    path - Path to log file.
    q_sig - Qt signal that will be used to emit messages. This can be any Qt signal that has a string attribute.
    mode - Setting file mode (write/append). Default is 'w'.
    summary - Printing message type count when running collect_messages. Default is True.
    collect - Printing a collection of each message type to EOF/BOF. when running collect_messages. Default is True.
    tempfile - Creating a temporary log file. This file will be deleted when close_log_hdlrs will run. Default is False.
    rotating - Creating a rotating file handler. By default, DEBUG file handlers are automatically set as rotating.
    backup_count - The number of backup files to be created when using a rotating file handler. Default is 100.
    log_same_level - The log file will include only messages from the same level/type. This is done to quickly count and collect messages. Default is False.'''

    log = logging.getLogger(name=name)
    log.setLevel(logging.DEBUG)
    dated_formatter = logging.Formatter(msg_format, date_format)

    if len(log.handlers) == 0:

        non_existing_log_level = 100

        stdout_stream_hdlr = logging.StreamHandler(stream=sys.stdout)
        stderr_stream_hdlr = logging.StreamHandler(stream=sys.stderr)

        # determining stdout log level
        stdout_level = logging.INFO
        if quiet:
            stdout_level = non_existing_log_level
        elif debug_to_stdout:
            stdout_level = logging.DEBUG

        stdout_stream_hdlr.setLevel(stdout_level)

        # determinig stderr log level
        # if stderr_level argument is None - setting level to nonexistent
        # otherwise using level as specified in arguments
        stderr_stream_hdlr.setLevel(stderr_level if stderr_level is not None else non_existing_log_level)

        for strm_hdlr in [stdout_stream_hdlr, stderr_stream_hdlr]:
            strm_hdlr.setFormatter(dated_formatter)
            strm_hdlr.addFilter(logging_classes.ParentFilter())
            log.addHandler(strm_hdlr)

    if logs_list is None:
        logs_list = []
    for log_dict in logs_list:
        hdlr = prepare_file_hdlr(log_dict, dated_formatter)
        log.addHandler(hdlr)

        if isinstance(hdlr, logging_classes.FileHandlerPlus):
            hdlr.setFormatter(dated_formatter)  # writing first line with a date


def prepare_file_hdlr(log_dict, formatter):
    '''A function that prepares a log file handler, sets its level, a formatter and additional filters from logging_classes.py'''
    rotating_fh = log_dict.pop('rotating', False)
    if 'path' in log_dict:
        # Creating a rotating file handler that rotates every 100MB and stores 100 backups == 10GB
        handler = logging_classes.RotatingFileHandlerPlus(maxBytes=100000000,
                                                          backupCount=log_dict.pop('backup_count', 100), **log_dict)
    elif 'q_sig' in log_dict:
        handler = logging_classes.QLogHandler(**log_dict)
    else:
        raise ce.MJValueError('Missing values in log dictionary. Supply either "path" or "q_sig"')
    handler.setLevel()  # Setting level to self._levelname
    handler.setFormatter(formatter)
    handler.addFilter(
        logging_classes.ParentFilter())  # Adds additional info to the log message - stack level, parent info: module, function name, line number.
    return handler


def get_hdlrs(hdlr_cls=logging_classes.FileHandlerPlus, hdlr_name=None):
    '''Returning a list of all logger handlers, based on the requested handler class type.
       The default type is FileHandlerPlus. hdlr_name is an optional argument to be able to fetch specific handler'''
    root_logger = logging.getLogger()
    return [hdlr for hdlr in root_logger.handlers if
            isinstance(hdlr, hdlr_cls) and (not hdlr_name or hdlr_name == hdlr.baseFilename)]


def close_log_hdlrs(hdlr_cls=logging_classes.FileHandlerPlus, hdlr_name=None):
    '''Walks through all logging handlers (based on the requested handler class type), and closes them
       The default type is FileHandlerPlus'''
    from utils import files_utils
    root_logger = logging.getLogger()
    hdlrs_to_close = sorted(get_hdlrs(hdlr_cls=hdlr_cls, hdlr_name=hdlr_name),
                            key=lambda hdlr: str(hdlr) == 'DEBUG')  # Placing debug handler at the end
    for hdlr in hdlrs_to_close:
        root_logger.removeHandler(hdlr)
        try:
            hdlr.close()
        except OSError:
            log.warning('Failed to close log handler - %s' % hdlr)
        if isinstance(hdlr, logging_classes.FileHandlerPlus):
            filename = os.path.abspath(hdlr.baseFilename)
            if hdlr.tempfile and os.path.exists(filename):
                log.debug('Removing temp file - %s' % filename)
                try:
                    files_utils.remove_paths(filename)
                except ce.MJOSError as e:
                    if os.path.exists(filename):
                        log.warning('Failed to remove temp log file - %s' % e)


def write_to_file(filename, lines, write_to_BOF=False):
    '''Writes to a log file - either to EOF or to BOF'''
    if write_to_BOF:
        with open(filename, 'r') as stream:
            org_lines = stream.readlines()
        with open(filename, 'w') as stream:
            for line in lines:
                stream.write("%s\n" % line.strip())
            for line in org_lines:
                stream.write(line)
    else:
        with open(filename, 'a') as stream:
            for line in lines:
                stream.write("%s\n" % line.strip())


def collect_messages(input_log_file, write_to_BOF=True):
    '''Collects messages and writes them to EOF or BOF.
Warning: if write_to_BOF is False, logging messages after collect will overwrite lines.
If summary is True, it will print a count of all messages found (per message type).
If collect is True, it will print a collection of each message type to EOF/BOF.'''

    messages = defaultdict(list)
    log.info('-' * 150)
    log.info('Test summary:')
    for hdlr in logging.getLogger().handlers:
        if isinstance(hdlr, logging_classes.FileHandlerPlus) and hdlr.summary:
            tmp_messages = hdlr.get_messages()
            message_type = hdlr.get_level_name()
            if tmp_messages is not None:
                if tmp_messages != []:
                    if hdlr.collect:
                        messages[message_type].extend(tmp_messages)
                    log.info('Found %i \'%s\' messages in - %s' % (
                        len(tmp_messages), message_type, os.path.abspath(hdlr.baseFilename)))
                else:
                    log.info('No \'%s\' messages found in - %s' % (message_type, os.path.abspath(hdlr.baseFilename)))
    log.info('-' * 150)
    msg_list = list()
    summary = list()
    for message_type, msgs in list(messages.items()):
        if len(msgs) > 0:
            msg_list.append('-' * 150 + '\n')
            msg_list.append('\'%s\' messages found: %s' % (message_type, len(msgs)))
            msg_list.extend(msgs)
            msg_list.append('-' * 150 + '\n')
            if message_type == 'CRITICAL':
                summary.append('CRITICAL - %s' % ', '.join(message[35:] for message in messages['CRITICAL']))
            else:
                summary.append('%s %s(s)' % (len(messages[message_type]), message_type))
    if write_to_BOF:
        msg_list.append('Full log:\n' + '-' * 150 + '\n')
    log.info('Finished test.')
    log.info('-' * 150)
    rep = get_reporter()
    rep.add_header_rows('-' * 200, {'text': 'Test summary (see log file for more info): %s' % ', '.join(summary)})
    if msg_list != []:
        write_to_file(input_log_file, msg_list, write_to_BOF=write_to_BOF)
    return messages


def collect_messages_and_exit(exit_code=0, write_to_BOF=True):
    '''Collects messages based on log_files_dict and closes all file handlers. It then returns the defined exit_code'''

    msg_types_dict = OrderedDict((('ERROR', 4), ('FAILURE', 5), ('DROP', 6), ('WARNING', 7)))

    # Finding all log files which will be used as input log file in the collect procedure
    input_log_files = list()
    messages = list()
    for hdlr in logging.getLogger().handlers:
        if isinstance(hdlr, logging_classes.FileHandlerPlus) and hdlr.use_for_collect:
            input_log_files.append(hdlr.baseFilename)
    for input_log_file in input_log_files:
        messages = collect_messages(input_log_file, write_to_BOF=write_to_BOF)

    non_critical_exit_code = 999  # default value
    if exit_code > 0:  # entered exit code is non zero only when method is called with critical exception
        ret_exit_code = exit_code
    else:  # derive exit_code from non critical logs messages (exit codes 4 - 7)
        ret_exit_code = non_critical_exit_code
        for msg_type in msg_types_dict:
            if msg_type in messages:
                ret_exit_code = msg_types_dict[msg_type]
                break
        if ret_exit_code == non_critical_exit_code:
            ret_exit_code = exit_code  # exit_code 0
    log.debug('Return code - %s' % ret_exit_code)

    close_log_hdlrs()
    return ret_exit_code


def parse_messages_from_log_file(log_file_path):
    '''A function that parses log file and returns a dictionary of errors'''
    regex = re.compile(r"'(?P<message>.+)' messages found: (?P<count>[0-9]+)")  # Fetching message count
    regex_critical = re.compile(r"CRITICAL\|(?P<exception>.*?):(?P<critical_massage>.*)")  # Fetching exception massage
    msg_dict = {}
    with open(log_file_path, 'r') as stream:
        for line in stream:
            if line.strip() == 'Full log:':
                break
            match = re.search(regex, line)
            match_critical = re.search(regex_critical, line)
            if match is not None:
                msg_dict[match.group('message')] = match.group('count')
            if match_critical is not None:
                msg_dict['CRITICAL'] = match_critical.group('exception').strip()
    return msg_dict


if __name__ == "__main__":
    sys.exit(main())

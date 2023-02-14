#!/usr/bin/env python

import time
import logging
import functools

from infra import logger

log = logger.get_logger(__name__)


def main():
    logger.set_logger(debug_to_stdout=True)

    @clock
    @retry(1, exceptions=(IOError, ValueError), delay=1, exp_handle_func=excep_print)
    def funcx():
        log.info('run')
        raise IOError('fff')
    funcx()


def excep_print():
    log.debug('This func was called during exception in Retry...')


default_exceptions = (Exception,)


def retry(tries, exceptions=default_exceptions, delay=0, exp_handle_func=None, retry_log_level=logging.DEBUG):
    """ Decorator for retrying a function if exception occurs

        tries -- num of retries (not including 1st try.)
        exceptions -- exceptions to catch (optional), default=all
        delay -- wait between retries (optional), default=0
        exp_handle_func -- function to run on exception

        example - @retry(5, exceptions=(IOError, ValueError), delay=1) """

    def decorate(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            for retry in range(1, tries+2):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    log.log(retry_log_level, 'Decorator Retry (for function %s) @ try no. %s, exception: %s' % (func.__name__, retry, e))
                    if exp_handle_func is not None:
                        exp_handle_func()
                    time.sleep(delay)

                    if retry == tries+1:
                        raise
        return _wrapper
    return decorate


def clock(func):
    '''A decorator that measures the time it takes to run the original function that was decorated.
       The decorator will print a debug log msg with 8 decimal points, and will work even if an exception was raised.'''
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        name = func.__name__
        arg_lst = []
        if args:
            arg_lst.extend(repr(arg) for arg in args)
        if kwargs:
            arg_lst.extend('%s=%r' % (k, w) for k, w in sorted(kwargs.items()))
        args_str = ', '.join(arg_lst)

        caught_exception = False
        result = None
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except:
            caught_exception = True
            raise
        finally:
            elapsed = time.perf_counter() - t0
            msg = '[{elapsed:0.8f}s] {name}({args_str})'.format(**locals())
            if not caught_exception:
                msg += ' -> {}' .format(result)
            log.debug(msg)
        return result
    return clocked


if __name__ == '__main__':
    main()

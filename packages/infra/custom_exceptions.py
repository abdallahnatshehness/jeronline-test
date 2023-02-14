#!/usr/bin/env python


class MJBaseError(Exception):
    """This custom exception stores an exit code for python to exit"""

    def __init__(self, message, exit_code=1):
        self.exit_code = exit_code
        super(MJBaseError, self).__init__(message)


class MJRunTimeError(MJBaseError):
    '''This custom exception is usually raised from a sub process call that failed.
       returncode stores the return code of the process'''
    def __init__(self, message, returncode=1, output='', **kwargs):
        self.returncode = returncode
        self.output = output
        super(MJRunTimeError, self).__init__(message, **kwargs)


class MJTimeOutError(MJBaseError):
    pass


class MJConfigurationError(MJBaseError):
    pass


class MJURLError(MJBaseError):
    pass


class MJFileNotFoundError(MJBaseError):
    pass


class MJValueError(MJBaseError):
    pass


class MJIOError(MJBaseError):
    pass


class MJOSError(MJBaseError):
    pass

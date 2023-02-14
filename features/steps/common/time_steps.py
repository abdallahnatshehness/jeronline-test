import time

from behave import *

from infra import logger, reporter

log = logger.get_logger(__name__)
rep = reporter.get_reporter()

use_step_matcher("parse")


@When('I wait for "{wait_time:f}" seconds')
def wait_for_seconds_float(context, wait_time, dependency_name='wait_for_seconds_float'):
    time.sleep(wait_time)


@When('I wait for "{wait_time:d}" seconds')
def wait_for_seconds_int(context, wait_time, dependency_name='wait_for_seconds_int'):
    time.sleep(wait_time)
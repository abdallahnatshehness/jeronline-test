from behave.model_core import Status
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from infra import reporter, logger

rep = reporter.get_reporter()
log = logger.get_logger(__name__)


def before_scenario(context, scenario):
    scenario.continue_after_failed_step = True


def before_all(context):
    context._config.current_page = None
    browser = context.opt_dict.get('browser', 'chrome')
    if browser == 'chrome':
        context.driver = webdriver.Chrome(ChromeDriverManager().install())
        context.driver.maximize_window()
    pass


def after_step(context, step):
    step_pass = True
    if step.status != Status.passed:
        step_pass = False

    if not step_pass:
        screenshot = f'{context.result_folder_path}/screenshot_after_failure.png'
        context.driver.save_screenshot(screenshot)
        rep.add_image_to_step(screenshot, "ScreenShot After Failure")

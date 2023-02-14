from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class AccessibilityMenu(BaseWidget):
    def __init__(self):
        super().__init__(self)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//div[@id='INDmenu']"
        }

    def close_menu(self):
        close_button = self.web_element.find_element(self.locator['By'], "//button[@id='INDcloseAccMenu']")
        close_button.click()

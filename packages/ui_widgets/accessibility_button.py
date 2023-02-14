from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class AccessibilityButton(BaseWidget):
    def __init__(self):
        super().__init__(self)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//button[@id='INDmenu-btn']"
        }


    def click_button(self):
        self.web_element.click()


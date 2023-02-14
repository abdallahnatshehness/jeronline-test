from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class Button(BaseWidget):
    def __init__(self, label):
        super().__init__(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//button[contains(.,'{self.label}')]"
        }

    def click_button(self):
        self.web_element.click()

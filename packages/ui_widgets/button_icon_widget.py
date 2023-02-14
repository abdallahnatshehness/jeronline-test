from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce
from ui_widgets.button_widget import Button

log = logger.get_logger(__name__)


class ButtonIcon(Button):
    def __init__(self, label):
        super().__init__(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//button[@title='{self.label}']"
        }

    def set_custom_locator(self, web_element):
        self.set_web_element(web_element)

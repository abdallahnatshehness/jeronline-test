from selenium.webdriver.common.by import By

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class AlertText(BaseWidget):
    def __init__(self, label, path_locator="following-sibling::div[@role='alert']"):
        super().__init__(label)
        self.path_locator = path_locator

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"/{self.path_locator}"
        }

    def has_text(self, text):
        return text in self.get_text

    def check_text(self, text):
        self.has_text(text)

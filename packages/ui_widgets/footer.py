from selenium.webdriver.common.by import By

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class Footer(BaseWidget):
    def __init__(self, label):
        super().__init__(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//footer[@class='lib-footer']",
        }

    def get_footer(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Value'])

    @property
    def get_text(self):
        return self.web_element.text

    def has_text(self, text):
        return text in self.get_text

    def check_text(self, text):
        self.has_text(text)

    def check_footer(self):
        footer_text = self.get_text
        if not self.web_element.is_displayed():
            raise AssertionError("Footer is not displayed")
        elif not len(footer_text) > 0:
            raise AssertionError("Footer text is not displayed")
        else:
            log.info("All footer elements are displayed")

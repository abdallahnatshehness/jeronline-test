from selenium.webdriver.common.by import By

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class PageNumber(BaseWidget):
    def __init__(self, label):
        super().__init__(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//ul[@class='lib-stepper-list']"
        }

    def get_pages_list(self):
        return self.web_element.find_elements(self.locator['By'], "li")

    def get_current_page_number(self):
        pages_list = self.get_pages_list()
        for item in pages_list:
            if bool(item.get_attribute('aria-selected')):
                return item.text.split('\n')[0]
        return -1

    def get_page_count(self):
        return len(self.get_pages_list())

    def validate_page_count(self, expected_number):
        return str(self.get_page_count()) == expected_number

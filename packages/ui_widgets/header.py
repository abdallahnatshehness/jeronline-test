import time

from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class Header(BaseWidget):
    def __init__(self, label):
        super().__init__(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//nav[starts-with(@class,'p-d-flex p-ai-center')]",
            'Logo': "//a[@href='https://www.jerusalem.muni.il/']",
            'Title': "//div[starts-with(@class,'lib-header__title')]",
            'ar': "//a[contains(text(),'العربية')]",
            'he': "//a[contains(text(),'עברית')]"
        }

    def get_logo(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Logo'])

    def get_header_title(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Title'])

    def get_language_button(self, language='he'):
        return self.web_element.find_element(self.locator['By'], self.locator[language])

    def get_current_selected_language(self):
        hebrew_button = self.get_language_button()
        is_selected = hebrew_button.find_element(self.locator['By'], "//parent::li[contains(@class,'active')]")
        if 'active' in is_selected.get_attribute("class"):
            return 'he'
        return 'ar'

    def select_language(self, language='he'):
        button = self.get_language_button(language)
        button.click()
        time.sleep(1)

    def check_header_displayed(self):
        if not self.get_logo().is_displayed():
            raise AssertionError("Header logo is not displayed")
        elif not self.get_header_title().is_displayed():
            raise AssertionError("Header title is not displayed")
        elif not self.get_language_button('ar').is_displayed():
            raise AssertionError("Arabic language button is not displayed")
        elif not self.get_language_button().is_displayed():
            raise AssertionError("Hebrew language button is not displayed")
        else:
            log.info("All header elements are displayed")

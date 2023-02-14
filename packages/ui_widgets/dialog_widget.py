from selenium.webdriver.common.by import By
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class Dialog(BaseWidget):
    def __init__(self):
        super().__init__(self)
        self.text = None

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//div[@role='dialog' and @aria-labelledby='pr_id_1-label']",
            'Main-Title': "//strong",
            'Logo': "//div[@class='p-mb-2']//*[name()='svg']",
            'Close-Button': "//span[@class='p-dialog-header-close-icon ng-tns-c40-4 pi pi-times']"
        }

    def get_main_title(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Main-Title'])

    def get_logo(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Logo'])

    def get_close_button(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Close-Button'])

    def click_close_button(self):
        button = self.get_close_button()
        button.click()

    def check_dialog_is_displayed(self, title):
        try:
            logo = self.get_logo()
            logo.is_displayed()
            assert logo.is_displayed() and title in self.get_main_title().text
            self.click_close_button()
            return True
        except:
            return False

    def dialog_is_not_display(self, txt):
        return not self.check_dialog_is_displayed(txt)

from selenium.webdriver.common.by import By

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class DropDown(BaseWidget):
    def __init__(self, label):
        super().__init__(label)
        self.chosen_text = None
        self.dropdown = None



    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//label[contains(text(),'{self.label}')]",
        }

    def set_dropdown(self, path_locator="following-sibling::p-dropdown"):
        self.dropdown = self.web_element.find_element(self.locator['By'], path_locator)
        self.set_web_element(self.dropdown)

    def set_custom_dropdown(self,web_element):
        self.dropdown = web_element
        self.set_web_element(self.dropdown)

    def get_dropdown(self):
        return self.dropdown

    def get_dropdown_list(self):
        return self.web_element.find_elements(self.locator['By'], "//ul//p-dropdownitem")

    # if dropdown already initialized - select from it
    # if not initialize with or without the default xpath then select from it
    def set_text(self, text, init=True, path_locator=None):
        self.chosen_text = text
        if init and path_locator is None and self.dropdown is None:
            self.set_dropdown()
            self.select_listbox_item(text)
        elif init and path_locator is not None and self.dropdown is None:
            self.set_dropdown(path_locator)
            self.select_listbox_item(text)
        else:
            self.select_listbox_item(text)

    # if the dropdown does not show everything use scroll down and then search
    # if the dropdown return 14 scroll to last value and check if its update

    def is_dropdown_opened(self):
        return len(self.get_dropdown_list()) > 0

    def select_listbox_item(self, text):
        if not self.is_dropdown_opened():
            self.click()
        items = self.get_dropdown_list()
        for item in items:
            if item.text == str(text):
                item.click()
                break
        else:
            self.click()

    def clear(self):
        self.web_element.clear()

    def click(self):
        self.web_element.click()

    def has_text(self, text):
        assert self.has_text(text), f"Text {text} in widget {self.label} is found and selected"

    @property
    def is_valid(self):
        return self.has_text(self.chosen_text)

    @property
    def is_invalid(self):
        return not self.is_valid

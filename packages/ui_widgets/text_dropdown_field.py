from selenium.webdriver.common.by import By

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce
from ui_widgets.dropdown_selector import DropDown
from ui_widgets.text_field import TextField

log = logger.get_logger(__name__)


class TextDropDown(BaseWidget):
    def __init__(self, label):
        super().__init__(label)
        self.dropdown_widget = DropDown(label)
        self.text_widget = TextField(label)

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//label[contains(text(),'{self.label}')]",
        }

    def initial_widgets(self):
        text_field_element = self.web_element.find_element(self.locator['By'], "following-sibling::div/input")
        self.text_widget.set_web_element(text_field_element)
        dropdown_element = self.web_element.find_element(self.locator['By'], "following-sibling::div/p-dropdown")
        self.dropdown_widget.set_web_element(dropdown_element)

    def set_text(self, text, use_child=False):
        new_text = text.split("-")
        self.initial_widgets()
        self.dropdown_widget.set_text(new_text[0],use_child)
        self.text_widget.set_text(new_text[1], use_child)

    @property
    def is_invalid(self):
        return self.text_widget.is_invalid is True or self.dropdown_widget.is_valid is False

    @property
    def is_valid(self):
        return self.text_widget.is_valid is True and self.dropdown_widget.is_valid is True

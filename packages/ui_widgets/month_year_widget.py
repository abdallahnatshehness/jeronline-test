from selenium.webdriver.common.by import By
from infra import logger, custom_exceptions as ce
from ui_widgets.base_widget import BaseWidget
from ui_widgets.button_icon_widget import ButtonIcon
from ui_widgets.button_widget import Button
from ui_widgets.dropdown_selector import DropDown

log = logger.get_logger(__name__)


class MonthYear(BaseWidget):
    def __init__(self, label):
        super().__init__(label)
        self.removeItemButton = ButtonIcon('הסר')
        self.year_dropdown = DropDown(' חודשים לבדיקה')

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"./following-sibling::div/div[{self.label}]"
        }

    def removeItem(self):
        remove_button = self.web_element.find_element(self.removeItemButton.locator['By'],
                                                      self.removeItemButton.locator['Value'])
        self.removeItemButton.set_custom_locator(remove_button)
        self.removeItemButton.click_button()

    def set_year(self, year):
        dropdown = self.web_element.find_element(self.locator['By'], "//p-dropdown")
        self.year_dropdown.set_custom_dropdown(dropdown)
        self.year_dropdown.set_text(year, False)

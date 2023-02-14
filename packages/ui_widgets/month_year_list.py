from selenium.webdriver.common.by import By
from infra import logger, custom_exceptions as ce
from ui_widgets.base_widget import BaseWidget
from ui_widgets.button_icon_widget import ButtonIcon
from ui_widgets.month_year_widget import MonthYear

log = logger.get_logger(__name__)


class MonthYearList(BaseWidget):
    def __init__(self, label):
        super().__init__(label)
        self.addItemButton = ButtonIcon('הוסף')
        # self.main_list = None
        # self.month_year_list = []

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//label[contains(text(),'{self.label}')]",
            'List': "following-sibling::div/div"
        }

    def create_widget(self, index):
        widget = MonthYear(index)
        widget_element = self.web_element.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(widget_element)
        return widget

    def init_widget(self):
        add_item_button = self.web_element.find_element(self.addItemButton.locator['By'],
                                                        self.addItemButton.locator['Value'])
        self.addItemButton.set_custom_locator(add_item_button)

    def add_item(self):
        self.addItemButton.click_button()

    def remove_item(self, index):
        widget = self.create_widget(index)
        widget.removeItem()
        pass

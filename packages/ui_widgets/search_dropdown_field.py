from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce

log = logger.get_logger(__name__)


class SearchDropDown(BaseWidget):
    def __init__(self, label):
        super().__init__(label)
        self.dropdown_widget = None
        self.text_widget = None
        self.virtual_list = None
        self.chosen_text = None
        self.clickable_dropdown = None

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': f"//label[contains(text(),'{self.label}')]",
            'Virtual-List': '//following-sibling::p-dropdown//div[starts-with(@class,"ng-trigger")]'
        }

    def open_dropdown(self):
        self.clickable_dropdown = self.web_element.find_element(self.locator['By'], "following-sibling::p-dropdown")
        self.clickable_dropdown.click()

    def initial_widgets(self):
        self.open_dropdown()
        self.virtual_list = self.web_element.find_element(self.locator['By'], self.locator['Virtual-List'])
        self.text_widget = self.virtual_list.find_element(self.locator['By'],
                                                          '//input[starts-with(@class,"p-dropdown-filter")]')
        self.dropdown_widget = self.virtual_list.find_element(self.locator['By'], "//ul[@role='listbox']")

    def find_by_text(self, text):
        self.text_widget.send_keys(text)
        first_result = self.dropdown_widget.find_element(self.locator['By'], "//p-dropdownitem[1]")
        first_result.click()
        pass

    def find_by_scroll(self, text):
        pass

    def set_text(self, text, find_by_scroll=False):
        self.chosen_text = text
        self.initial_widgets()
        if find_by_scroll:
            self.find_by_scroll(text)
        else:
            self.find_by_text(text)

    def item_search_scroll(self, text, driver):
        # it works for a lot of conditions but not fully ready yet
        self.web_element.click()
        element = ""
        anotherone = ""

        while True:
            WebDriverWait(self.web_element, 30).until(EC.presence_of_element_located(
                (By.XPATH, "//div/following-sibling::div/ul/cdk-virtual-scroll-viewport")))
            element = driver.find_element(by=By.XPATH,
                                          value=f"//div/following-sibling::div/ul/cdk-virtual-scroll-viewport")
            driver.execute_script("arguments[0].scrollBy(0,70);", element)
            element = element.text
            log.info(element)

            if text in element:
                i = i + 1
            if text in element and i == 5:
                chosenElement = self.driver.find_element(by=By.XPATH, value=f"//li[@aria-label='{text}']")
                chosenElement.click()
                break

    @property
    def is_invalid(self):
        return self.chosen_text not in self.clickable_dropdown.text

    @property
    def is_valid(self):
        return self.chosen_text in self.clickable_dropdown.text

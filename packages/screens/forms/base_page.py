from selenium.webdriver.common.by import By

from ui_widgets.accessibility_button import AccessibilityButton
from ui_widgets.accessibility_menu import AccessibilityMenu
from ui_widgets.button_widget import Button
from ui_widgets.dialog_widget import Dialog
from ui_widgets.footer import Footer
from ui_widgets.header import Header
from ui_widgets.page_number import PageNumber


# <html lang="he" id="html">

class BasePage(object):
    def __init__(self, driver):
        self.driver = driver
        self.main_url = 'https://jeronlineforms.jerusalem.muni.il/'
        self.url_postfix = ''
        self.current_language = 'he'
        self.widgets = {'המשך': Button('המשך'), 'Header': Header('Header'), 'Footer': Footer('Footer'),
                        'PageNumber': PageNumber('PageNumber'), 'Accessibility': AccessibilityButton(),
                        'AccessibilityMenu': AccessibilityMenu(), 'Dialog': Dialog()}

        self.main_elements_to_wait_when_load = []

    def navigate_to_page_url(self):
        self.driver.get(self.main_url + self.url_postfix)

    def get_current_lang(self):
        try:
            self.driver.find_element(By.XPATH, "//a[contains(text(),'עברית')]//parent::li[contains(@class,'active')]")
            self.current_lang = 'he'
        except:
            self.current_lang = 'ar'

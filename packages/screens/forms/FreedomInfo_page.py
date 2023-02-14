from infra import config
from screens.forms.base_page import BasePage
from ui_widgets.dropdown_selector import DropDown
from ui_widgets.search_dropdown_field import SearchDropDown
from ui_widgets.text_dropdown_field import TextDropDown
from ui_widgets.text_field import TextField


class FreedomInfo(BasePage):
    def __init__(self, driver, language):
        super().__init__(driver)
        self.page_title = 'FreedomInfo'
        self.url_postfix = 'FreedomInfo'
        self.widgets['שם פרטי'] = TextField(config.language['שם פרטי'].get(language))
        self.widgets['שם משפחה'] = TextField(config.language['שם משפחה'].get(language))
        self.widgets['מספר ת.ז.'] = TextField(config.language['מספר ת.ז.'].get(language))
        self.widgets['דוא"ל'] = TextField(config.language['דוא"ל'].get(language))
        self.widgets['מספר דרכון'] = TextField(config.language['מספר דרכון'].get(language))
        self.widgets['מספר בית'] = TextField(config.language['מספר בית'].get(language))
        self.widgets['מיקוד'] = TextField(config.language['מיקוד'].get(language))
        self.widgets['יישוב'] = SearchDropDown(config.language['יישוב'].get(language))
        self.widgets['רחוב'] = SearchDropDown(config.language['רחוב'].get(language))
        self.widgets['טלפון נייד'] = TextDropDown(config.language['טלפון נייד'].get(language))
        self.widgets['טלפון קווי'] = TextDropDown(config.language['טלפון קווי'].get(language))
        self.widgets['סוג זיהוי'] = DropDown(config.language['סוג זיהוי'].get(language))

        self.main_elements_to_wait_when_load = [
            self.widgets['שם פרטי'],
            self.widgets['שם משפחה'],
            self.widgets['דוא"ל'],
        ]

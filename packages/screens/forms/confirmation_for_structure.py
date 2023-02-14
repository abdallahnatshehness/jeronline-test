from infra import config
from screens.forms.base_page import BasePage
from ui_widgets.text_dropdown_field import TextDropDown
from ui_widgets.text_field import TextField


class ConfirmationForStructure(BasePage):
    def __init__(self, driver, language):
        super().__init__(driver)
        self.page_title = 'ConfirmationForStructure'
        self.url_postfix = 'ConfirmationForStructure'
        self.widgets['שם פרטי'] = TextField(config.language['שם פרטי'].get(language))
        self.widgets['שם משפחה'] = TextField(config.language['שם משפחה'].get(language))
        self.widgets['מספר ת.ז.'] = TextField(config.language['מספר ת.ז.'].get(language))
        self.widgets['דוא"ל'] = TextField(config.language['דוא"ל'].get(language))
        self.widgets['טלפון נייד'] = TextDropDown(config.language['טלפון נייד'].get(language))
        self.widgets['טלפון קווי'] = TextDropDown(config.language['טלפון קווי'].get(language))

        self.main_elements_to_wait_when_load = [
            self.widgets['שם פרטי'],
            self.widgets['שם משפחה'],
            self.widgets['מספר ת.ז.'],
            self.widgets['דוא"ל'],
        ]

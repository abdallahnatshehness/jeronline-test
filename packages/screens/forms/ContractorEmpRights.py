from screens.forms.base_page import BasePage
from ui_widgets.footer_new import FooterNew
from ui_widgets.month_year_list import MonthYearList


class ContractorEmpRights(BasePage):
    def __init__(self, driver, language):
        super().__init__(driver)
        self.page_title = 'ContractorEmpRights'
        self.url_postfix = 'ContractorEmpRights'
        self.widgets['footer_new'] = FooterNew('footer_new',driver)
        self.widgets[' חודשים לבדיקה'] = MonthYearList(' חודשים לבדיקה')

        self.main_elements_to_wait_when_load = []

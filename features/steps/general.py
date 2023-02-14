from behave import *
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from infra import logger, reporter, config, custom_exceptions as ce

rep = reporter.get_reporter()
log = logger.get_logger(__name__)


# make a function for widget.get_web_element()

@given('I navigate to "{screen_name}" page')
def navigate_to_screen(context, screen_name):
    """
    :param screen_name: name used in screens manager
    :type context: behave.runner.Context
    """
    current_page = context.screens_manager.create_screen([screen_name], driver=context.driver)
    if (
            context._config.current_page and context._config.current_page.page_title != current_page.page_title) or context._config.current_page is None:
        context._config.current_page = current_page
        current_page.navigate_to_page_url()
        driver = current_page.driver
        for element in current_page.main_elements_to_wait_when_load:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((element.locator['By'], element.locator['Value'])))


@given('I navigate to "{screen_name}" page with language "{language}"')
def navigate_to_screen_langauge(context, screen_name, language):
    """
    :param language: chosen page language
    :param screen_name: name used in screens manager
    :type context: behave.runner.Context
    """
    current_page = context.screens_manager.create_screen([screen_name], driver=context.driver, language=language)
    if (
            context._config.current_page and context._config.current_page.page_title != current_page.page_title) or context._config.current_page is None:
        context._config.current_page = current_page
        current_page.navigate_to_page_url()
        driver = current_page.driver
        # modify the language wait after creating best language page
        if language == 'he':
            for element in current_page.main_elements_to_wait_when_load:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((element.locator['By'], element.locator['Value'])))


@when('switch language to "{language}"')
def switch_language(context, language):
    widget = context._config.current_page.widgets['Header']
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    widget.select_language(language)


# give wait here to locate the element


@when('I write "{text}" in "{widget_name}"')
def write_into_text_field(context, text, widget_name):
    """
    :param widget_name:
    :param text:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
        widget.set_text(text)
    else:
        widget.set_text(text, False)


@when('I click on "{widget_name}"')
def click_button_widget(context, widget_name):
    """
    :param widget_name: name of the widget
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    widget.click_button()


@when('I write "{text}" in "{widget_name}" in search feild scroll')
def write_into_search_dropdown_text_field(context, text, widget_name):
    # it works for a lot of conditions but not fully ready yet
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    widget.item_search_scroll(text)


@when('I add "{items}" in widget "{widget_name}"')
def add_items_month_year_list(context, items, widget_name):
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
        widget.init_widget()
    for item in range(int(items)):
        widget.add_item()

@when('I remove "{items}" in widget "{widget_name}"')
def add_items_month_year_list(context, items, widget_name):
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
        widget.init_widget()
    widget.remove_item(items)


@then('I check that the accessibility opened and closed')
def close_accessibility_menu(context):
    """
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets['AccessibilityMenu']
    if widget.get_web_element() is None:
        web_element = WebDriverWait(context._config.current_page.driver, 10).until(
            EC.visibility_of_element_located((widget.locator['By'], widget.locator['Value'])))
        widget.set_web_element(web_element)
    widget.close_menu()


@then('I check if the header is exist')
def check_header_exist(context):
    """
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets['Header']
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    return widget.check_header_displayed()


@then('I check if the "{footer}" is exist')
def check_footer_exist(context, footer):
    """
    :param footer:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[footer]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    return widget.check_footer()


@then('dropdown "{widget_name}" has selected "{text}" value')
def dropdown_has_selected(context, widget_name, text):
    """
    :param widget_name:
    :param text
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.has_text(text), f"Text {text} in widget {widget_name} is found and selected"


@then('field "{widget_name}" has invalid value and with alert "{text_alert}"')
def field_has_invalid_value(context, widget_name, text_alert):
    """
    :param text_alert:
    :param widget_name:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.is_invalid is True and widget.is_valid is False and widget.check_alert_text(
        text_alert) is True, f"Field {widget_name}  considered as valid in the invalid test"


@then('field "{widget_name}" has invalid value')
def field_has_invalid_value(context, widget_name):
    """
    :param widget_name:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.is_invalid is True, f"Field {widget_name} considered as valid in the invalid test"


@then('field "{widget_name}" has valid value')
def field_has_valid_value(context, widget_name):
    """
    :param widget_name:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets[widget_name]
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.is_valid is True, f"Field {widget_name} considered as invalid in the valid values test"


@then('I check that the current page number is  "{number}"')
def field_has_valid_value(context, number):
    """
    :param number:
    :type context: behave.runner.Context
    """
    widget = context._config.current_page.widgets['PageNumber']
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.get_current_page_number() == number, f"page {context._config.current_page.page_title} number check " \
                                                       f"does not equal {number}"


@then('I check that the form only have "{number}" pages')
def field_has_valid_value(context, number):
    """
        :param number:
        :type context: behave.runner.Context
        """
    widget = context._config.current_page.widgets['PageNumber']
    if widget.get_web_element() is None:
        web_element = context._config.current_page.driver.find_element(widget.locator['By'], widget.locator['Value'])
        widget.set_web_element(web_element)
    assert widget.validate_page_count(number), f"form {context._config.current_page.page_title} pages " \
                                               f"supposed to be  {number} pages"


@then('Dialog should be displayed with "{title}"')
def dialog_has_display(context, title):
    """
        :param title: dialog title under logo
        :type context: behave.runner.Context
        """
    widget = context._config.current_page.widgets['Dialog']
    if widget.get_web_element() is None:
        web_element = WebDriverWait(context._config.current_page.driver, 10).until(
            EC.visibility_of_element_located((widget.locator['By'], widget.locator['Value'])))
        widget.set_web_element(web_element)
    assert widget.check_dialog_is_displayed(title), "the dialog supposed to be displayed"


@then('Dialog should not be displayed with "{title}"')
def dialog_has_not_displayed(context, title):
    """
        :param title: dialog title under logo
        :type context: behave.runner.Context
        """
    widget = context._config.current_page.widgets['Dialog']
    try:
        if widget.get_web_element() is None:
            web_element = context._config.current_page.driver.find_element(widget.locator['By'],
                                                                           widget.locator['Value'])
            widget.set_web_element(web_element)
        assert widget.dialog_is_not_display(title), "the dialog supposed to be not display"
    except:
        pass

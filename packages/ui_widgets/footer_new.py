import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.relative_locator import locate_with

from ui_widgets.base_widget import BaseWidget
from infra import logger, custom_exceptions as ce
from ui_widgets.footer import Footer

log = logger.get_logger(__name__)


class FooterNew(Footer):
    def __init__(self, label, driver):
        super().__init__(label)
        self.driver = driver

    @property
    def locator(self):
        return {
            'By': By.XPATH,
            'Value': "//footer",
            'Text': "//div[@class='link-help links']",
            'Sites': "//div[@class='social']"
        }

    @property
    def get_text(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Text']).text

    def get_sites(self):
        return self.web_element.find_element(self.locator['By'], self.locator['Sites'])

    def check_link_and_title(self, link, expected_title):
        # Open the link in a new tab
        self.driver.execute_script("window.open('{}', '_blank');".format(link))

        # Switch to the new tab
        self.driver.switch_to.window(self.driver.window_handles[-1])

        # Get the page title
        page_title = self.driver.title

        # Check the page title
        if expected_title in page_title:
            result = True
        else:
            result = False
        # Close the new tab and switch back to the original tab
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return result

    def check_facebook(self):
        facebook = self.web_element.find_element(self.locator['By'], "//a[@class='fa fa-facebook-f']")
        link = facebook.get_attribute("href")
        return self.check_link_and_title(link, 'עיריית ירושלים')

    def check_twitter(self):
        twitter = self.web_element.find_element(self.locator['By'], "//a[@class='fa fa-twitter contacts']")
        link = twitter.get_attribute("href")
        return self.check_link_and_title(link, 'עיריית ירושלים')

    def check_instagram(self):
        instagram = self.web_element.find_element(self.locator['By'], "//a[@class='fa fa-instagram contacts']")
        link = instagram.get_attribute("href")
        return self.check_link_and_title(link, 'עיריית ירושלים')

    def check_social_media(self):
        return self.check_facebook() and self.check_instagram() and self.check_twitter()

    def check_footer(self):
        footer_text = self.get_text
        if not locate_with(self.locator['By'], self.locator['Sites']).to_left_of(
                {self.locator['By']: self.locator['Text']}):
            raise AssertionError("Sites not on the left of the Text")
        elif not len(footer_text) > 5:
            raise AssertionError("Footer text is not displayed")
        elif not self.check_social_media():
            raise AssertionError("social media link are incorrect")

        else:
            log.info("All footer elements are displayed")

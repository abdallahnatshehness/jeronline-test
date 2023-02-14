# Created by LENOVO at 10/02/2023
Feature: FreedomInfo page tests in arabic language (Prof Of Concept)

  @minor
  Scenario: change the page language to arabic and test first name input in the invalid case
    Given I navigate to "FreedomInfo" page with language "ar"
    When switch language to "ar"
    When I write "עבד" in "שם פרטי"
    Then field "שם פרטי" has invalid value and with alert "يجب إدخال الأحرف العربية والأحرف الخاصة فقط"


  @minor
  Scenario: change the page language to arabic and test first name input in the valid case
    Given I navigate to "FreedomInfo" page with language "ar"
    When switch language to "ar"
    When I write "عبدالله" in "שם פרטי"
    Then field "שם פרטי" has valid value
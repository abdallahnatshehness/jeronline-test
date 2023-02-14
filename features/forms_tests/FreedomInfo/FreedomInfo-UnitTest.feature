Feature: Testing FreedomInfo page

  @critical
  Scenario: Header check if displayed
    Given I navigate to "FreedomInfo" page
    Then I check if the header is exist
    Then I check that the form only have "3" pages
    Then I check that the current page number is  "1"

  @normal
  Scenario: Footer check if displayed
    Given I navigate to "FreedomInfo" page
    Then I check if the footer is exist

  @critical
  Scenario Outline: First name field test with invalid values to test the alert "only numbers and special characters allowed" message
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "שם פרטי"
    Then field "שם פרטי" has invalid value and with alert "יש להזין אותיות בעברית בלבד ותווים מיוחדים"
    Examples:
    | text  |
    | אבגד/()'.,_-זחט12 |
    | אבגד/()'.,_-זחט!  |
    | אבגד/()'.,_-זחט@  |
    | אבגד/()'.,_-זחט#  |
    | אבגד/()'.,_-זחט$  |
    | אבגד/()'.,_-זחט%  |
    | אבגד/()'.,_-זחט^  |
    | אבגד/()'.,_-זחט&  |
    | אבגד/()'.,_-זחט*  |
    | אבגד/()'.,_-זחט+  |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    |32kj4k324|
    |432اتتاלחךל|
    |כגד09לחi09تهךח|
    |234324324|
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/() |
    | רשת12  |
    |חכלכיעחלך|
    | בגדי!  |
    | הוזח@  |
    | לכמנ#  |

  @critical
  Scenario Outline: First name field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "שם פרטי"
    Then field "שם פרטי" has valid value
    Examples:
    | text  |
    |גדכגדכ|
    |דגכככככככככ|
    |םיעןחפםעיח|


  @critical
  Scenario Outline: Family name field test with invalid values to test the alert "only numbers and special characters allowed" message
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "שם משפחה"
    Then field "שם משפחה" has invalid value and with alert "יש להזין אותיות בעברית בלבד ותווים מיוחדים"
    Examples:
    | text  |
    | אבגד/()'.,_-זחט12 |
    | אבגד/()'.,_-זחט!  |
    | אבגד/()'.,_-זחט@  |
    | אבגד/()'.,_-זחט#  |
    | אבגד/()'.,_-זחט$  |
    | אבגד/()'.,_-זחט%  |
    | אבגד/()'.,_-זחט^  |
    | אבגד/()'.,_-זחט&  |
    | אבגד/()'.,_-זחט*  |
    | אבגד/()'.,_-זחט+  |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    |32kj4k324|
    |432اتتاלחךל|
    |כגד09לחi09تهךח|
    |234324324|
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/() |
    | רשת12  |
    |חכלכיעחלך|
    | בגדי!  |
    | הוזח@  |
    | לכמנ#  |

  @critical
  Scenario Outline: Family name field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "שם משפחה"
    Then field "שם משפחה" has valid value
    Examples:
    | text  |
    |גדכגדכ|
    |דגכככככככככ|
    |םיעןחפםעיח|

    @minor
    Scenario Outline: unit test to choose id type - ID NUMBER -
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "סוג זיהוי"
    Then field "סוג זיהוי" has valid value
    Examples:
      | text |
      |ת.ז.|
      |דרכון|
      |ת.ז.|

  @critical
  Scenario Outline: I.D. field test with invalid values to test the alert "not correct" message
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר ת.ז."
    Then field "מספר ת.ז." has invalid value and with alert "מספר זהות לא תקין"
    Examples:
    | text |
    |000000000|
    |000000009|
    |000000018|
    |2345|
    |ab123456|
    |12341234567|
    |12-3456789|
    |1234:56789|
    |1234ab56|
    |1234 56789|
    |1234_56789|
    |1234.56789|
    |12a3456789|
    |12b3456789|
    |12c3456789|
    |12d3456789|
    |12e3456789|
    |12f3456789|


  @critical
  Scenario Outline: I.D. field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר ת.ז."
    Then field "מספר ת.ז." has valid value
    Examples:
    | text  |
    |319076618|

  @critical
  Scenario Outline: Mobile phone field test with invalid values to test the alert "Numbers only" message
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון נייד"
    Then field "טלפון נייד" has invalid value and with alert "יש להזין ספרות בלבד"
    Examples:
      | text |
      |dd-7133772|
      |053-oiخهع|
      |يت-تننتاتنا|
      |07-3457654387646734567 |
      |053-34876556734567 |

  @critical
  Scenario Outline: Mobile phone field test with invalid values to test "missing numbers" alert
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון נייד"
    Then field "טלפון נייד" has invalid value and with alert "יש להשלים את הספרות החסרות"
    Examples:
      | text |
      |dd-1|
      |053-12|
      |123-تننتاتنا|
      |07-76554|
      |053-12|


  @critical
  Scenario Outline:  Mobile phone field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון נייד"
    Then field "טלפון נייד" has valid value
    Examples:
      | text |
      |053-7133772|
      |050-6393648|
      |077-7383632|

  @critical
  Scenario Outline: Land-line phone field test with invalid values to test "only numbers" alert
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון קווי"
    Then field "טלפון קווי" has invalid value and with alert "יש להזין ספרות בלבד"
    Examples:
      | text |
      |dd-7133772|
      |053-oiخهع|
      |يت-تننتاتنا|
      |07-3457654387646734567 |
      |053-34876556734567 |

  @critical
  Scenario Outline: Land-line phone field test with invalid values to test "missing numbers" alert
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון קווי"
    Then field "טלפון קווי" has invalid value and with alert "יש להשלים את הספרות החסרות"
    Examples:
      | text |
      |dd-1|
      |053-12|
      |123-تننتاتنا|
      |07-76554|
      |053-12|


  @critical
  Scenario Outline: Land-line phone field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "טלפון קווי"
    Then field "טלפון קווי" has valid value
    Examples:
      | text |
      |053-7133772|
      |073-7383632|


  @critical
  Scenario Outline: Email field test with invalid values to test "incorrect feild" alert
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "דוא"ל"
    Then field "דוא"ל" has invalid value and with alert "שדה לא תקין"
    Examples:
      |text|
      |user@.com|
      | @missingusername.com|
      | user@missingtld|
      | user@.missingtld.|
      | user@missingtld.|
      | user@-invalidtld.com|
      | plainaddress |
      | #@%^%#$@#$@#.com|
      | @missingatsign.com|
      | missingdot@.com|
      | two@@missingatsigns.com|
      | leadingdot@.com|
      | .leadingdot@com.com|
      | email.with!symbol@com.com|
      | email.with%percent@com.com|
      | email.with_underscore@com.com|

  @critical
  Scenario Outline: Email field test with valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "דוא"ל"
    Then field "דוא"ל" has valid value
   Examples:
    | text|
    | user@example.com|
    | user@example.co.il|
    | user.name@example.co.il|
    | user.name@example.com|
    | user_name@example.com|
    | user+name@example.com|
    | user.nametag@example.com|
    | user@subdomain.example.com|
    | user@sub.example.com|
    | user@sub-domain.example.com|

   @minor
  Scenario Outline:  test  Postal Code input for invalid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מיקוד"
    Then field "מיקוד" has invalid value and with alert "יש להזין ספרות בלבד"
    Examples:
    | text  |
    | אבגד/()'.,_-זחט12 |
    | אבגד/()'.,_-זחט!  |
    | אבגד/()'.,_-זחט@  |
    | אבגד/()'.,_-זחט#  |
    | אבגד/()'.,_-זחט$  |
    | אבגד/()'.,_-זחט%  |
    | אבגד/()'.,_-זחט^  |
    | אבגד/()'.,_-זחט&  |
    | אבגד/()'.,_-זחט*  |
    | אבגד/()'.,_-זחט+  |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    |32kj4k324|
    |432اتتاלחךל|
    |כגד09לחi09تهךח|
    |234324324|
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/() |
    | רשת12  |
    |חכלכיעחלך|
    | בגדי!  |
    | הוזח@  |
    | לכמנ#  |

    @minor
  Scenario Outline:  test  Postal Code for valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מיקוד"
    Then field "מיקוד" has valid value
    Examples:
    | text  |
    |76543|
    |123456789|
    |876543|
    |632486|

    @minor
  Scenario Outline:  test  home number input for invalid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר בית"
    Then field "מספר בית" has invalid value and with alert "יש להזין ספרות בלבד"
    Examples:
    | text  |
    | אבגד/()'.,_-זחט12 |
    | אבגד/()'.,_-זחט!  |
    | אבגד/()'.,_-זחט@  |
    | אבגד/()'.,_-זחט#  |
    | אבגד/()'.,_-זחט$  |
    | אבגד/()'.,_-זחט%  |
    | אבגד/()'.,_-זחט^  |
    | אבגד/()'.,_-זחט&  |
    | אבגד/()'.,_-זחט*  |
    | אבגד/()'.,_-זחט+  |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/12 |
    | דהו!   |
    | זחט@   |
    | יכל#   |
    | מנס$   |
    | פצק%   |
    | רשת^   |
    |32kj4k324|
    |432اتتاלחךל|
    |כגד09לחi09تهךח|
    |234324324|
    | בגדי&   |
    | הוזח*   |
    | לכמנ+   |
    | אבג/() |
    | רשת12  |
    |חכלכיעחלך|
    | בגדי!  |
    | הוזח@  |
    | לכמנ#  |

    @minor
  Scenario Outline:  test  home number input for valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר בית"
    Then field "מספר בית" has valid value
    Examples:
    | text  |
    |76543|
    |123456789|
    |876543|
    |632486|

  @minor
  Scenario Outline:  test to choose id type - PASSPORT NUMBER -
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "סוג זיהוי"
    Then field "סוג זיהוי" has valid value
    Examples:
      | text |
      |דרכון|
      |ת.ז.|
      |דרכון|

 @minor
  Scenario Outline:  test  passport number input for invalid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר דרכון"
    Then field "מספר דרכון" has invalid value and with alert "מספר דרכון לא תקין"
    Examples:
    | text |
    |2345|
    |ab123456|
    |12341234567|
    |12-3456789|
    |1234:56789|
    |1234ab56|
    |1234 56789|
    |1234_56789|
    |1234.56789|
    |12a3456789|
    |12b3456789|
    |12c3456789|
    |12d3456789|
    |12e3456789|
    |12f3456789|


  @minor
  Scenario Outline:  test  passport number input for valid values
    Given I navigate to "FreedomInfo" page
    When I write "<text>" in "מספר דרכון"
    Then field "מספר דרכון" has valid value
    Examples:
    | text  |
    |319076618|


  @critical
  Scenario: test for search dropdown
    Given I navigate to "FreedomInfo" page
    When I write "ירושלים" in "יישוב"
    Then field "יישוב" has valid value

  @normal
  Scenario: test for search dropdown
    Given I navigate to "FreedomInfo" page
    When I write "החלוץ" in "רחוב"
    Then field "רחוב" has valid value


  @critical
  Scenario: Accessibility icon test
    Given I navigate to "FreedomInfo" page
    When I click on "Accessibility"
    Then I check that the accessibility opened and closed

  @Blocker:
  Scenario: Fill valid values except First Name field, then click continue button to check the process,
    it should give an alert message and will not continue to second page
    Given I navigate to "FreedomInfo" page
    When I write "darweesh" in "שם פרטי"
    And I write "קימרי" in "שם משפחה"
    And I write "ת.ז." in "סוג זיהוי"
    And I write "039886544" in "מספר ת.ז."
    And I write "052-5768719" in "טלפון נייד"
    And I write "02-6287296" in "טלפון קווי"
    And I write "darweeshq@ness-tech.co.il" in "דוא"ל"
    And I click on "המשך"
    Then Dialog should not be displayed with "לצורך המשך מילוי הטופס"
    #Then Validate the result (stay at same page)



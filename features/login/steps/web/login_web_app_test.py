"""
Login Web Tests — with Self-Healing Locator integration.
If a locator breaks, SelfHealer automatically tries to find a working alternative.
Target: app-dev.thehono.com/login
"""
import os
import pytest
import allure
from dotenv import load_dotenv
from playwright.sync_api import Page

from core.self_healer import self_healer
from features.login.pages.web.login_page import LoginPage
from features.login.locators.web.login_web_locators import (
    EMAIL_FIELD, PASSWORD_FIELD, LOGIN_BUTTON,
    ELEMENT_DESCRIPTIONS, LOCATOR_REGISTRY,
)

load_dotenv(dotenv_path=".env")

from features.login.test_data.login_test_data import LoginTestData
from config.test_config import TestConfig

pytestmark = [allure.feature("Login"), allure.suite("Web")]

EMAIL    = LoginTestData.VALID_EMAIL
PASSWORD = LoginTestData.VALID_PASSWORD
LOCATORS_FILE = TestConfig.LOGIN_LOCATORS_WEB


@pytest.mark.web
@pytest.mark.smoke
def test_TC_WEB_001_login_button_disabled_when_empty(page: Page):
    """
    TC-WEB-001 | Boundary | Login button disabled when fields empty
    Given: Login page loaded
    When: No input provided
    Then: Login button is disabled
    """
    login_page = LoginPage(page)
    login_page.open()
    self_healer._create_snapshot("login", LOCATORS_FILE)
    login_page.assert_button_disabled()


@pytest.mark.web
def test_TC_WEB_002_login_button_disabled_email_only(page: Page):
    """
    TC-WEB-002 | Boundary | Login button disabled with email only
    Given: Login page loaded
    When: Only email filled, password empty
    Then: Login button remains disabled
    """
    LoginPage(page).open().enter_email(EMAIL).assert_button_disabled()


@pytest.mark.web
@pytest.mark.smoke
def test_TC_WEB_003_login_button_enabled_both_fields(page: Page):
    """
    TC-WEB-003 | Smoke | Login button enabled when both fields filled
    Given: Login page loaded
    When: Email and password filled
    Then: Login button is enabled
    """
    LoginPage(page).open().enter_email(EMAIL).enter_password(PASSWORD).assert_button_enabled()


@pytest.mark.web
@pytest.mark.negative
def test_TC_WEB_004_sql_injection_blocked(page: Page):
    """
    TC-WEB-004 | Security | SQL injection blocked by frontend validation
    Given: Login page loaded
    When: SQL injection string entered as email
    Then: Login button stays disabled (invalid email format)
    """
    malicious = "'; DROP TABLE users;--"
    LoginPage(page).open().enter_email(malicious).enter_password("AnyPass123!").assert_button_disabled()


@pytest.mark.web
def test_TC_WEB_005_self_healing_demo(page: Page):
    """
    TC-WEB-005 | Self-Healing Demo | Simulate broken locator + auto-heal
    Given: Login page loaded
    When: A deliberately wrong locator is used
    Then: Self-healer finds correct locator automatically
    """
    LoginPage(page).open()
    broken_locator = 'input[name="email"]'  # wrong — app uses type not name

    result = self_healer.heal(
        page=page,
        feature="login",
        element="EMAIL_FIELD",
        broken_locator=broken_locator,
        locators_file=LOCATORS_FILE,
    )

    assert result.healed, (
        f"Self-healing failed. Candidates tried: {len(result.candidates)}\n"
        f"Candidates: {[c.get('locator') for c in result.candidates]}"
    )
    print(f"\n✓ Self-healed to: {result.applied}")
    print(f"  Candidates tried: {len(result.candidates)}")

"""Login Web Tests — app-dev.thehono.com/login"""
import allure
import pytest
from playwright.sync_api import Page

from features.login.pages.web.login_page import LoginPage
from features.login.test_data.login_test_data import LoginTestData

pytestmark = [
    allure.feature("Login"),
    allure.suite("Web"),
]


@pytest.mark.smoke
@pytest.mark.web
def test_TC_WEB_001_login_button_disabled_when_empty(page: Page):
    """TC-WEB-001 | Boundary | Login button disabled when fields are empty"""
    LoginPage(page).open().assert_button_disabled()


@pytest.mark.web
def test_TC_WEB_002_login_button_disabled_email_only(page: Page):
    """TC-WEB-002 | Boundary | Login button disabled with only email filled"""
    LoginPage(page).open().enter_email(LoginTestData.VALID_EMAIL).assert_button_disabled()


@pytest.mark.smoke
@pytest.mark.web
def test_TC_WEB_003_login_button_enabled_both_fields(page: Page):
    """TC-WEB-003 | Smoke | Login button enabled when both fields are filled"""
    (
        LoginPage(page)
        .open()
        .enter_email(LoginTestData.VALID_EMAIL)
        .enter_password(LoginTestData.VALID_PASSWORD)
        .assert_button_enabled()
    )


@pytest.mark.negative
@pytest.mark.web
def test_TC_WEB_004_sql_injection_blocked(page: Page):
    """TC-WEB-004 | Security | SQL injection string keeps button disabled (invalid email format)"""
    (
        LoginPage(page)
        .open()
        .enter_email("'; DROP TABLE users;--")
        .enter_password("AnyPass123!")
        .assert_button_disabled()
    )


@pytest.mark.web
def test_TC_WEB_005_self_healing_demo(page: Page):
    """TC-WEB-005 | Self-Healing | Broken locator is auto-healed by SelfHealer"""
    from core.self_healer import self_healer
    from features.login.locators.web.login_web_locators import LOCATOR_REGISTRY
    from config.test_config import TestConfig

    login_page = LoginPage(page).open()

    broken_locator = 'input[name="email"]'
    result = self_healer.heal(
        page=page,
        feature="login",
        element="EMAIL_FIELD",
        broken_locator=broken_locator,
        locators_file=TestConfig.LOGIN_LOCATORS_WEB,
    )

    assert result.healed, (
        f"Self-healing failed. Candidates tried: {len(result.candidates)}\n"
        f"Candidates: {[c.get('locator') for c in result.candidates]}"
    )

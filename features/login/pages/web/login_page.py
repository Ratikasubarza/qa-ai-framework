"""
LoginPage — Page Object for app-dev.thehono.com/login

Encapsulates all login page interactions. Tests never call page.click() directly.

Usage:
    login_page = LoginPage(page)
    login_page.login(email, password)
    login_page.assert_that.url_contains("/feed")

    # Negative flow:
    login_page.login_with_wrong_password()
    assert login_page.has_error_message()
"""
from playwright.sync_api import Page
from platforms.web.pages.base_page import BasePage
from features.login.locators.web.login_web_locators import (
    EMAIL_FIELD, EMAIL_LABEL,
    PASSWORD_FIELD, PASSWORD_LABEL,
    LOGIN_BUTTON, LOGIN_BUTTON_NAME,
    ERROR_MESSAGE, SUCCESS_URL,
)


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Actions ───────────────────────────────────────────────────────────────

    def open(self) -> "LoginPage":
        self.goto()
        self.wait_for(EMAIL_FIELD)
        return self

    def enter_email(self, email: str) -> "LoginPage":
        self.fill_by_locator(
            self.page.get_by_label(EMAIL_LABEL), email, description="Email field"
        )
        return self

    def enter_password(self, password: str) -> "LoginPage":
        self.fill_by_locator(
            self.page.get_by_label(PASSWORD_LABEL), password, description="Password field"
        )
        return self

    def submit(self) -> "LoginPage":
        self.click_by_locator(
            self.page.get_by_role("button", name=LOGIN_BUTTON_NAME), description="Login button"
        )
        return self

    def login(self, email: str, password: str) -> "LoginPage":
        """Full login flow — open page, fill credentials, submit."""
        self.open()
        self.enter_email(email)
        self.enter_password(password)
        self.submit()
        return self

    def login_with_wrong_password(self, email: str) -> "LoginPage":
        from features.login.test_data.login_test_data import LoginTestData
        return self.login(email, LoginTestData.WRONG_PASSWORD)

    # ── State queries ─────────────────────────────────────────────────────────

    def is_login_button_enabled(self) -> bool:
        return self.is_enabled(LOGIN_BUTTON)

    def has_error_message(self) -> bool:
        return self.is_visible(ERROR_MESSAGE)

    def get_error_text(self) -> str:
        if self.has_error_message():
            return self.get_text(ERROR_MESSAGE)
        return ""

    def is_on_feed(self) -> bool:
        return SUCCESS_URL in self.current_url

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_login_success(self) -> "LoginPage":
        self.wait_for_url(SUCCESS_URL)
        self.assert_that.url_contains(SUCCESS_URL)
        return self

    def assert_login_failed(self) -> "LoginPage":
        self.assert_that.url_contains(self.URL)
        return self

    def assert_button_disabled(self) -> "LoginPage":
        self.assert_that.element_disabled(LOGIN_BUTTON, "Login button")
        return self

    def assert_button_enabled(self) -> "LoginPage":
        self.assert_that.element_enabled(LOGIN_BUTTON, "Login button")
        return self

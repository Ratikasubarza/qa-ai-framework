"""
LoginScreen — Android screen object for the Hono login screen.

Encapsulates all login screen interactions. Tests never call driver.find() directly.

Usage:
    login_screen = LoginScreen(driver)
    login_screen.login(email, password)
    login_screen.assert_that.page_contains("Home")

    # Navigate to login from any state:
    login_screen.ensure_on_login_screen()
"""
import time
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.screens.base_mobile_screen import BaseMobileScreen
from features.login.locators.mobile.login_android_locators import (
    LOGIN_BUTTON, EMAIL_FIELD_INDEX as EMAIL_INDEX,
    PASSWORD_FIELD_INDEX as PASSWORD_INDEX,
)


class LoginScreen(BaseMobileScreen):

    # ── Navigation ────────────────────────────────────────────────────────────

    def ensure_on_login_screen(self) -> "LoginScreen":
        """Navigate to login from any app state — handles feed, onboarding, etc."""
        from config.test_config import TestConfig
        source = self.get_page_source()

        if "Home" in source or "Network" in source:
            self._logout_from_feed()

        if "Welcome to HONO" in source or "personalize profile" in source:
            self.driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
            time.sleep(2)
            self.driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
            time.sleep(4)

        try:
            self.driver.find(
                AppiumBy.ANDROID_UIAUTOMATOR,
                'new UiSelector().descriptionContains("Log in")',
                timeout=5,
            ).click()
            time.sleep(3)
        except AssertionError:
            pass  # already on login screen
        return self

    def _logout_from_feed(self):
        try:
            self.driver.driver.tap([(50, 120)])
            time.sleep(2)
            self.driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
            time.sleep(2)
            self.driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
            time.sleep(3)
        except Exception:
            pass

    # ── Actions ───────────────────────────────────────────────────────────────

    def enter_email(self, email: str) -> "LoginScreen":
        self.fill_by_index(EMAIL_INDEX, email, description="Email field")
        return self

    def enter_password(self, password: str) -> "LoginScreen":
        self.fill_by_index(PASSWORD_INDEX, password, description="Password field")
        return self

    def tap_login(self) -> "LoginScreen":
        self.hide_keyboard()
        time.sleep(0.5)
        self.tap(AppiumBy.ANDROID_UIAUTOMATOR,
                 'new UiSelector().description("Login to my account")',
                 description="Login button")
        time.sleep(10)
        return self

    def login(self, email: str, password: str) -> "LoginScreen":
        """Full login flow."""
        self.enter_email(email)
        self.enter_password(password)
        self.tap_login()
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def is_on_feed(self) -> bool:
        source = self.get_page_source()
        return "Home" in source or "'Network'" in source

    def has_error_message(self) -> bool:
        source = self.get_page_source()
        return any(k in source for k in ["Invalid", "incorrect", "Wrong", "error"])

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_login_success(self) -> "LoginScreen":
        self.assert_that.page_contains("Home")
        return self

    def assert_login_failed(self) -> "LoginScreen":
        assert self.has_error_message(), (
            "[LoginScreen] Expected error message after failed login, but none found.\n"
            f"  Page source preview: {self.get_page_source()[:300]}"
        )
        return self

"""
RegisterScreen — Android screen object for the Hono registration form.

Encapsulates all register screen interactions. Tests never call driver.find() directly.

Usage:
    screen = RegisterScreen(driver)
    screen.fill_form(fullname="Jane", email="j@x.com", phone="811", linkedin="...")
    screen.tap_apply()
    screen.assert_on_verify_email_screen()
"""
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.screens.base_mobile_screen import BaseMobileScreen
from features.register.locators.mobile.register_android_locators import (
    FULLNAME_INDEX, EMAIL_INDEX, PHONE_INDEX, LINKEDIN_INDEX,
    JOIN_COMMUNITY_BTN, APPLY_NOW_BTN, VERIFY_EMAIL_SCREEN,
)


class RegisterScreen(BaseMobileScreen):

    # ── Navigation ────────────────────────────────────────────────────────────

    def tap_join_community(self, timeout: int = 5) -> "RegisterScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, JOIN_COMMUNITY_BTN, timeout=timeout).click()
        return self

    # ── Form fields ───────────────────────────────────────────────────────────

    def enter_fullname(self, name: str) -> "RegisterScreen":
        self.fill_by_index(FULLNAME_INDEX, name, description="Full name field")
        return self

    def enter_email(self, email: str) -> "RegisterScreen":
        self.fill_by_index(EMAIL_INDEX, email, description="Email field")
        return self

    def enter_phone(self, phone: str) -> "RegisterScreen":
        self.fill_by_index(PHONE_INDEX, phone, description="Phone field")
        return self

    def enter_linkedin(self, url: str) -> "RegisterScreen":
        self.fill_by_index(LINKEDIN_INDEX, url, description="LinkedIn field")
        return self

    def fill_form(
        self,
        fullname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        linkedin: str | None = None,
    ) -> "RegisterScreen":
        if fullname is not None:
            self.enter_fullname(fullname)
        if email is not None:
            self.enter_email(email)
        if phone is not None:
            self.enter_phone(phone)
        if linkedin is not None:
            self.enter_linkedin(linkedin)
        self.hide_keyboard()
        return self

    # ── Actions ───────────────────────────────────────────────────────────────

    def tap_apply(self, timeout: int = 5) -> "RegisterScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN, timeout=timeout).click()
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def is_apply_button_enabled(self) -> bool:
        try:
            el = self.driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN, timeout=3)
            return el.is_enabled()
        except Exception:
            return False

    def is_on_verify_email_screen(self) -> bool:
        return self.driver.is_element_present(
            AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=5
        )

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_apply_button_disabled(self) -> "RegisterScreen":
        self.assert_that.element_disabled_by_accessibility(APPLY_NOW_BTN, "Apply now button")
        return self

    def assert_on_verify_email_screen(self) -> "RegisterScreen":
        assert self.driver.is_element_present(
            AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=10
        ), "Verify email screen not shown after register"
        return self

    def assert_not_on_verify_email_screen(self) -> "RegisterScreen":
        assert not self.driver.is_element_present(
            AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=3
        ), "Should not proceed to verify email screen with invalid input"
        return self

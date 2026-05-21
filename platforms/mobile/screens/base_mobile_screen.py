"""
BaseMobileScreen — foundation for all Android screen objects.

Every screen class inherits from this. It owns:
  - Element interaction (tap, fill, scroll)
  - Assertions via MobileAssertions
  - Screenshot + Allure attachment on failure
  - AppiumDriver access

Usage:
    class LoginScreen(BaseMobileScreen):
        EMAIL_FIELD    = (AppiumBy.CLASS_NAME, "android.widget.EditText")
        LOGIN_BUTTON   = (AppiumBy.ACCESSIBILITY_ID, "Login to my account")

        def login(self, email: str, password: str) -> "LoginScreen":
            self.fill_by_index(0, email)
            self.fill_by_index(1, password)
            self.tap(*self.LOGIN_BUTTON)
            return self
"""
import time
import allure
import structlog
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from platforms.mobile.appium_driver import AppiumDriver

logger = structlog.get_logger(__name__)


class BaseMobileScreen:
    def __init__(self, driver: AppiumDriver):
        self.driver = driver

    # ── Element interaction ───────────────────────────────────────────────────

    def tap(self, by: str, value: str,
            description: str = "", timeout: int = 10) -> "BaseMobileScreen":
        label = description or value[:40]
        with allure.step(f"Tap '{label}'"):
            self.driver.tap(by, value, timeout)
        return self

    def fill(self, by: str, value: str, text: str,
             description: str = "", timeout: int = 10) -> "BaseMobileScreen":
        label = description or value[:40]
        with allure.step(f"Fill '{label}' with '{text[:30]}'"):
            self.driver.type_text(by, value, text, timeout)
        return self

    def fill_by_index(self, index: int, text: str,
                      description: str = "") -> "BaseMobileScreen":
        label = description or f"field[{index}]"
        with allure.step(f"Fill '{label}' with '{text[:30]}'"):
            els = self.driver.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.EditText"
            )
            assert len(els) > index, (
                f"[BaseMobileScreen] EditText index {index} not found. "
                f"Found {len(els)} fields."
            )
            els[index].click()
            els[index].send_keys(text)
        return self

    def tap_accessibility(self, label: str, timeout: int = 10) -> "BaseMobileScreen":
        return self.tap(AppiumBy.ACCESSIBILITY_ID, label, description=label, timeout=timeout)

    def wait_for_element(self, by: str, value: str, timeout: int = 10) -> "BaseMobileScreen":
        """Explicit wait until element is present; replaces time.sleep after navigation."""
        self.driver.find(by, value, timeout=timeout)
        return self

    def wait_for_text_in_source(self, text: str, timeout: int = 10) -> bool:
        """Poll page source until text appears or timeout. Returns True if found."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in self.get_page_source():
                return True
            time.sleep(0.5)
        return False

    def scroll_down(self) -> "BaseMobileScreen":
        self.driver.scroll_down()
        return self

    def scroll_up(self) -> "BaseMobileScreen":
        self.driver.scroll_up()
        return self

    def hide_keyboard(self) -> "BaseMobileScreen":
        self.driver.hide_keyboard()
        return self

    def back(self) -> "BaseMobileScreen":
        self.driver.back()
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def is_visible(self, by: str, value: str, timeout: int = 5) -> bool:
        return self.driver.is_element_present(by, value, timeout)

    def get_page_source(self) -> str:
        return self.driver.get_page_source()

    def get_text(self, by: str, value: str, timeout: int = 10) -> str:
        el = self.driver.find(by, value, timeout)
        return (el.text or el.get_attribute("content-desc") or "").strip()

    # ── Assertions ────────────────────────────────────────────────────────────

    @property
    def assert_that(self):
        from skills.assertions.mobile_assertions import MobileAssertions
        return MobileAssertions(self.driver)

    # ── Screenshot / Allure ───────────────────────────────────────────────────

    def screenshot(self, name: str = "mobile_screenshot") -> str:
        import os
        os.makedirs("reports/debug_logs", exist_ok=True)
        path = f"reports/debug_logs/{name}.png"
        self.driver.screenshot(name)
        try:
            with open(path, "rb") as f:
                allure.attach(
                    f.read(),
                    name=name,
                    attachment_type=allure.attachment_type.PNG,
                )
        except Exception:
            pass
        return path

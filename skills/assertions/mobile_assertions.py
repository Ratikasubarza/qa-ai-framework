"""
Mobile Assertions — chainable Appium assertion layer with Allure integration.

Usage:
    ma = MobileAssertions(driver)
    ma.element_visible(AppiumBy.ACCESSIBILITY_ID, "Login button")
    ma.text_contains(AppiumBy.ACCESSIBILITY_ID, "Welcome", "Hono")
"""
import allure
import structlog
from appium.webdriver.common.appiumby import AppiumBy

logger = structlog.get_logger(__name__)


class MobileAssertions:
    def __init__(self, driver):
        self.driver = driver

    def _screenshot_to_allure(self, label: str = "screenshot"):
        try:
            raw = self.driver.driver.get_screenshot_as_png()
            allure.attach(
                raw,
                name=label,
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass

    def _find(self, by: str, value: str, timeout: int = 10):
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        try:
            return WebDriverWait(self.driver.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    # ── Visibility ────────────────────────────────────────────────────────────

    def element_visible(self, by: str, value: str, timeout: int = 10,
                        description: str = "") -> "MobileAssertions":
        label = description or value
        el = self._find(by, value, timeout)
        if not el:
            self._screenshot_to_allure(f"not_visible_{label[:20]}")
            raise AssertionError(
                f"[MobileAssertions] Element not visible: '{label}'\n"
                f"  Locator: [{by}] {value}"
            )
        return self

    def element_not_visible(self, by: str, value: str, timeout: int = 3,
                            description: str = "") -> "MobileAssertions":
        label = description or value
        el = self._find(by, value, timeout)
        assert el is None, (
            f"[MobileAssertions] Element should NOT be visible: '{label}'"
        )
        return self

    # ── Text ──────────────────────────────────────────────────────────────────

    def text_equals(self, by: str, value: str, expected: str) -> "MobileAssertions":
        el = self._find(by, value)
        assert el is not None, f"[MobileAssertions] Element not found: {value}"
        actual = (el.text or el.get_attribute("content-desc") or "").strip()
        assert actual == expected, (
            f"[MobileAssertions] Text mismatch for '{value}'.\n"
            f"  Expected : '{expected}'\n"
            f"  Actual   : '{actual}'"
        )
        return self

    def text_contains(self, by: str, value: str, expected: str) -> "MobileAssertions":
        el = self._find(by, value)
        assert el is not None, f"[MobileAssertions] Element not found: {value}"
        actual = (el.text or el.get_attribute("content-desc") or "").strip()
        assert expected in actual, (
            f"[MobileAssertions] '{value}' text should contain '{expected}'\n"
            f"  Actual: '{actual}'"
        )
        return self

    # ── Page source ───────────────────────────────────────────────────────────

    def page_contains(self, keyword: str) -> "MobileAssertions":
        source = self.driver.driver.page_source
        assert keyword in source, (
            f"[MobileAssertions] Page source does not contain: '{keyword}'"
        )
        return self

    def page_not_contains(self, keyword: str) -> "MobileAssertions":
        source = self.driver.driver.page_source
        assert keyword not in source, (
            f"[MobileAssertions] Page source should NOT contain: '{keyword}'"
        )
        return self

    # ── Allure ────────────────────────────────────────────────────────────────

    def attach_screenshot(self, name: str = "screenshot") -> "MobileAssertions":
        self._screenshot_to_allure(name)
        return self

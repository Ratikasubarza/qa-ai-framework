"""
Mobile Assertion Skill — standardized assertions for Android tests.
"""
import structlog
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.appium_driver import AppiumDriver

logger = structlog.get_logger(__name__)


class MobileAssertion:
    def __init__(self, driver: AppiumDriver):
        self.driver = driver

    def text_visible(self, text: str):
        assert self.driver.is_element_present(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().text("{text}")'
        ), f"Text not visible: '{text}'"
        logger.debug("assert_text_visible", text=text)

    def element_visible_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        assert self.driver.is_element_present(
            AppiumBy.ID,
            f"{self.driver.app_package}:id/{resource_id}"
        ), f"Element not visible: '{label}'"

    def element_not_visible_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        assert not self.driver.is_element_present(
            AppiumBy.ID,
            f"{self.driver.app_package}:id/{resource_id}",
            timeout=3,
        ), f"Element should not be visible: '{label}'"

    def current_activity_is(self, activity: str):
        actual = self.driver.driver.current_activity
        assert actual == activity, (
            f"Activity assertion failed.\n"
            f"Expected: '{activity}'\n"
            f"Actual:   '{actual}'"
        )

    def element_enabled_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        el = self.driver.find_by_id(resource_id)
        assert el.is_enabled(), f"Element should be enabled: '{label}'"

    def element_disabled_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        el = self.driver.find_by_id(resource_id)
        assert not el.is_enabled(), f"Element should be disabled: '{label}'"

    def text_contains(self, resource_id: str, expected: str):
        el     = self.driver.find_by_id(resource_id)
        actual = el.text
        assert expected in actual, (
            f"Text assertion failed.\n"
            f"Expected to contain: '{expected}'\n"
            f"Actual: '{actual}'"
        )
    def element_disabled_by_accessibility(self, label: str, description: str = ""):
        el = self.driver.find_by_accessibility(label)
        assert not el.is_enabled(), f"Element should be disabled: '{description or label}'"

    def element_enabled_by_accessibility(self, label: str, description: str = ""):
        el = self.driver.find_by_accessibility(label)
        assert el.is_enabled(), f"Element should be enabled: '{description or label}'"

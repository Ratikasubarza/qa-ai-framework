"""
Mobile Interaction Skill — reusable mobile UI actions.
Works with AppiumDriver for Android testing.
Mirrors ElementInteraction API for consistency across platforms.
"""
import structlog
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.appium_driver import AppiumDriver

logger = structlog.get_logger(__name__)


class MobileInteraction:
    def __init__(self, driver: AppiumDriver):
        self.driver = driver

    def tap_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        self.driver.tap(AppiumBy.ID, f"{self.driver.app_package}:id/{resource_id}")
        logger.debug("tap", element=label)

    def tap_by_text(self, text: str):
        self.driver.tap(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().text("{text}")'
        )
        logger.debug("tap_text", text=text)

    def tap_by_accessibility(self, label: str):
        self.driver.tap(AppiumBy.ACCESSIBILITY_ID, label)
        logger.debug("tap_accessibility", label=label)

    def fill_by_id(self, resource_id: str, text: str, description: str = ""):
        label = description or resource_id
        self.driver.type_text(
            AppiumBy.ID,
            f"{self.driver.app_package}:id/{resource_id}",
            text,
        )
        logger.debug("fill", element=label, text=text[:20])

    def fill_by_accessibility(self, label: str, text: str):
        """Flutter: tap field to focus, then type character by character."""
        from appium.webdriver.common.appiumby import AppiumBy
        import time
        el = self.driver.find_by_accessibility(label)
        # Tap to focus
        el.click()
        time.sleep(0.5)
        # Clear existing content
        el.clear()
        time.sleep(0.3)
        # Type character by character for Flutter reliability
        for char in text:
            el.send_keys(char)
            time.sleep(0.05)
        logger.debug("fill_accessibility", label=label)

    def get_text_by_id(self, resource_id: str) -> str:
        el = self.driver.find_by_id(resource_id)
        return el.text

    def get_text_by_accessibility(self, label: str) -> str:
        el = self.driver.find_by_accessibility(label)
        return el.text

    def is_visible_by_id(self, resource_id: str) -> bool:
        return self.driver.is_element_present(
            AppiumBy.ID,
            f"{self.driver.app_package}:id/{resource_id}",
        )

    def is_visible_by_text(self, text: str) -> bool:
        return self.driver.is_element_present(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().text("{text}")',
        )

    def scroll_to_text(self, text: str):
        """Scroll until text is visible."""
        self.driver.find(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true)).scrollIntoView(new UiSelector().text("{text}"))',
        )

    def assert_text_visible(self, text: str):
        assert self.is_visible_by_text(text), f"Text not visible: '{text}'"
        logger.debug("assert_text_visible", text=text)

    def assert_element_visible_by_id(self, resource_id: str, description: str = ""):
        label = description or resource_id
        assert self.is_visible_by_id(resource_id), f"Element not visible: '{label}'"
        logger.debug("assert_visible", element=label)
    def fill_by_edittext_index(self, index: int, text: str):
        """
        Fill input field by EditText index.
        Used for Flutter apps that don't expose resource-id.
        index 0 = email, index 1 = password
        """
        from appium.webdriver.common.appiumby import AppiumBy
        els = self.driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
        if index >= len(els):
            raise AssertionError(f"EditText index {index} not found, only {len(els)} found")
        el = els[index]
        el.click()
        import time
        time.sleep(0.5)
        el.clear()
        el.send_keys(text)
        logger.debug("fill_edittext", index=index, text=text[:20])

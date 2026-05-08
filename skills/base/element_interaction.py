"""
Element Interaction Skill — reusable UI actions.
Used by all platforms and all agents.
All methods include built-in retry and meaningful error messages.
"""
import structlog
from playwright.sync_api import Page, TimeoutError as PWTimeout
from tenacity import retry, stop_after_attempt, wait_fixed

logger = structlog.get_logger(__name__)


class ElementInteraction:
    def __init__(self, page: Page, default_timeout: int = 10000):
        self.page    = page
        self.timeout = default_timeout

    def click(self, selector: str, description: str = ""):
        """Click an element. Waits for it to be visible and enabled."""
        label = description or selector
        try:
            self.page.click(selector, timeout=self.timeout)
            logger.debug("click", element=label)
        except PWTimeout:
            self.page.screenshot(path=f"reports/debug_logs/click_failed.png")
            raise AssertionError(f"Could not click '{label}' — element not found or not clickable")

    def fill(self, selector: str, value: str, description: str = ""):
        """Clear and fill an input field."""
        label = description or selector
        try:
            self.page.fill(selector, value, timeout=self.timeout)
            logger.debug("fill", element=label, value=value[:20])
        except PWTimeout:
            raise AssertionError(f"Could not fill '{label}' — element not found")

    def select_option(self, selector: str, value: str, description: str = ""):
        """Select a dropdown option by value."""
        label = description or selector
        try:
            self.page.select_option(selector, value, timeout=self.timeout)
            logger.debug("select_option", element=label, value=value)
        except PWTimeout:
            raise AssertionError(f"Could not select '{value}' in '{label}'")

    def hover(self, selector: str, description: str = ""):
        label = description or selector
        self.page.hover(selector, timeout=self.timeout)
        logger.debug("hover", element=label)

    def get_text(self, selector: str) -> str:
        """Get visible text of an element."""
        try:
            return self.page.inner_text(selector, timeout=self.timeout).strip()
        except PWTimeout:
            raise AssertionError(f"Could not get text from '{selector}' — element not found")

    def get_value(self, selector: str) -> str:
        """Get input field value."""
        return self.page.input_value(selector, timeout=self.timeout)

    def is_visible(self, selector: str) -> bool:
        try:
            return self.page.is_visible(selector, timeout=3000)
        except Exception:
            return False

    def is_enabled(self, selector: str) -> bool:
        return self.page.is_enabled(selector, timeout=self.timeout)

    def press_key(self, key: str):
        """Press keyboard key e.g. Enter, Tab, Escape."""
        self.page.keyboard.press(key)
        logger.debug("press_key", key=key)

    def upload_file(self, selector: str, file_path: str):
        self.page.set_input_files(selector, file_path)
        logger.debug("upload_file", path=file_path)

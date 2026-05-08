"""
Assertion Helper — standardized assertions across all tests.
Provides clear failure messages with context.
"""
import structlog
from playwright.sync_api import Page

logger = structlog.get_logger(__name__)


class AssertionHelper:
    def __init__(self, page: Page):
        self.page = page

    def url_contains(self, expected: str):
        current = self.page.url
        assert expected in current, (
            f"URL assertion failed.\n"
            f"Expected to contain: '{expected}'\n"
            f"Actual URL: '{current}'"
        )
        logger.debug("assert_url_contains", expected=expected)

    def url_is(self, expected: str):
        current = self.page.url
        assert current == expected, (
            f"URL assertion failed.\n"
            f"Expected: '{expected}'\n"
            f"Actual:   '{current}'"
        )

    def element_visible(self, selector: str, description: str = ""):
        label = description or selector
        assert self.page.is_visible(selector), (
            f"Element not visible: '{label}'"
        )
        logger.debug("assert_visible", element=label)

    def element_hidden(self, selector: str, description: str = ""):
        label = description or selector
        assert not self.page.is_visible(selector), (
            f"Element should be hidden but is visible: '{label}'"
        )

    def text_equals(self, selector: str, expected: str):
        actual = self.page.inner_text(selector).strip()
        assert actual == expected, (
            f"Text assertion failed for '{selector}'.\n"
            f"Expected: '{expected}'\n"
            f"Actual:   '{actual}'"
        )

    def text_contains(self, selector: str, expected: str):
        actual = self.page.inner_text(selector).strip()
        assert expected in actual, (
            f"Text assertion failed for '{selector}'.\n"
            f"Expected to contain: '{expected}'\n"
            f"Actual: '{actual}'"
        )

    def page_has_text(self, expected: str):
        content = self.page.content()
        assert expected in content, (
            f"Page does not contain text: '{expected}'"
        )

    def element_count(self, selector: str, expected_count: int):
        actual = len(self.page.query_selector_all(selector))
        assert actual == expected_count, (
            f"Element count assertion failed for '{selector}'.\n"
            f"Expected: {expected_count}\n"
            f"Actual:   {actual}"
        )

    def input_value_equals(self, selector: str, expected: str):
        actual = self.page.input_value(selector).strip()
        assert actual == expected, (
            f"Input value assertion failed for '{selector}'.\n"
            f"Expected: '{expected}'\n"
            f"Actual:   '{actual}'"
        )

    def no_console_errors(self):
        """Check no JS errors in console (requires console listener setup)."""
        pass  # Implement with page.on("console") listener if needed
    def element_disabled(self, selector: str, description: str = ""):
        label = description or selector
        assert not self.page.is_enabled(selector), f"Element should be DISABLED: '{label}'"

    def element_enabled(self, selector: str, description: str = ""):
        label = description or selector
        assert self.page.is_enabled(selector), f"Element should be ENABLED: '{label}'"

"""
Wait Strategy Skill — smart waits to eliminate flaky tests.
80% of flaky tests are caused by poor wait logic.
Never use hard sleep() — always wait for a condition.
"""
import structlog
from playwright.sync_api import Page, TimeoutError as PWTimeout

logger = structlog.get_logger(__name__)


class WaitStrategy:
    def __init__(self, page: Page, default_timeout: int = 15000):
        self.page    = page
        self.timeout = default_timeout

    def for_element(self, selector: str, state: str = "visible", timeout: int = None):
        """
        Wait for element to reach desired state.
        state: visible | hidden | attached | detached
        """
        try:
            _timeout = timeout if timeout is not None else self.timeout
            self.page.wait_for_selector(selector, state=state, timeout=_timeout)
        except PWTimeout:
            raise AssertionError(
                f"Element '{selector}' did not reach state '{state}' "
                f"within {self.timeout}ms"
            )

    def for_url(self, url_pattern: str):
        """Wait for URL to match a pattern."""
        try:
            self.page.wait_for_url(url_pattern, timeout=self.timeout)
        except PWTimeout:
            current = self.page.url
            raise AssertionError(
                f"URL did not match '{url_pattern}' within {self.timeout}ms. "
                f"Current: {current}"
            )

    def for_navigation(self):
        """Wait for full page navigation to complete."""
        self.page.wait_for_load_state("networkidle", timeout=self.timeout)

    def for_text(self, text: str, selector: str = "body"):
        """Wait for specific text to appear on page."""
        try:
            self.page.wait_for_selector(
                f"{selector}:has-text('{text}')",
                timeout=self.timeout
            )
        except PWTimeout:
            raise AssertionError(f"Text '{text}' did not appear within {self.timeout}ms")

    def for_network_idle(self):
        """Wait for all network requests to complete."""
        self.page.wait_for_load_state("networkidle", timeout=self.timeout)

    def for_response(self, url_pattern: str):
        """Wait for a specific API response."""
        with self.page.expect_response(url_pattern) as resp:
            return resp.value

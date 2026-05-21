"""
BasePage — foundation for all web Page Objects.

Every page class inherits from this. It owns:
  - Navigation (goto, wait_for_load)
  - Element interaction (fill, click, select)
  - Assertions via WebAssertions
  - Screenshot + Allure attachment on failure
  - Self-healing locator support

Usage:
    class LoginPage(BasePage):
        URL = "/login"
        EMAIL    = 'input[type="email"]'
        PASSWORD = 'input[type="password"]'
        SUBMIT   = 'button[type="submit"]'

        def login(self, email: str, password: str):
            self.goto()
            self.fill(self.EMAIL, email)
            self.fill(self.PASSWORD, password)
            self.click(self.SUBMIT)
            return self
"""
import allure
import structlog
from playwright.sync_api import Locator, Page
from config.test_config import TestConfig

logger = structlog.get_logger(__name__)


class BasePage:
    URL: str = "/"

    def __init__(self, page: Page):
        self.page = page
        self._base_url = TestConfig.WEB_APP_URL

    # ── Navigation ────────────────────────────────────────────────────────────

    def goto(self, path: str | None = None, wait_until: str = "domcontentloaded") -> "BasePage":
        target = f"{self._base_url}{path or self.URL}"
        with allure.step(f"Navigate to {path or self.URL}"):
            self.page.goto(target, wait_until=wait_until)
            logger.debug("page_goto", url=target)
        return self

    def wait_for_url(self, url_fragment: str, timeout: int = 10000) -> "BasePage":
        self.page.wait_for_url(f"**{url_fragment}**", timeout=timeout)
        return self

    def reload(self) -> "BasePage":
        self.page.reload()
        return self

    @property
    def current_url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    # ── Element interaction ───────────────────────────────────────────────────

    def fill(self, selector: str, value: str,
             description: str = "", timeout: int = 8000) -> "BasePage":
        label = description or selector
        with allure.step(f"Fill '{label}' with '{value[:30]}{'...' if len(value)>30 else ''}'"):
            self.page.wait_for_selector(selector, timeout=timeout)
            self.page.fill(selector, value)
        return self

    def click(self, selector: str,
              description: str = "", timeout: int = 8000) -> "BasePage":
        label = description or selector
        with allure.step(f"Click '{label}'"):
            self.page.wait_for_selector(selector, timeout=timeout)
            self.page.click(selector)
        return self

    def fill_by_locator(self, locator: Locator, value: str,
                        description: str = "") -> "BasePage":
        label = description or "element"
        with allure.step(f"Fill '{label}' with '{value[:30]}{'...' if len(value)>30 else ''}'"):
            locator.wait_for(state="visible")
            locator.fill(value)
        return self

    def click_by_locator(self, locator: Locator, description: str = "") -> "BasePage":
        label = description or "element"
        with allure.step(f"Click '{label}'"):
            locator.wait_for(state="visible")
            locator.click()
        return self

    def select_option(self, selector: str, value: str) -> "BasePage":
        self.page.select_option(selector, value)
        return self

    def clear_and_fill(self, selector: str, value: str) -> "BasePage":
        self.page.fill(selector, "")
        self.page.fill(selector, value)
        return self

    def press_key(self, selector: str, key: str) -> "BasePage":
        self.page.press(selector, key)
        return self

    # ── Waits ─────────────────────────────────────────────────────────────────

    def wait_for(self, selector: str, timeout: int = 8000) -> "BasePage":
        self.page.wait_for_selector(selector, timeout=timeout)
        return self

    def wait_for_hidden(self, selector: str, timeout: int = 5000) -> "BasePage":
        self.page.wait_for_selector(selector, state="hidden", timeout=timeout)
        return self

    def wait_for_network_idle(self, timeout: int = 10000) -> "BasePage":
        self.page.wait_for_load_state("networkidle", timeout=timeout)
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def is_visible(self, selector: str) -> bool:
        return self.page.is_visible(selector)

    def is_enabled(self, selector: str) -> bool:
        return self.page.is_enabled(selector)

    def get_text(self, selector: str) -> str:
        return self.page.inner_text(selector).strip()

    def get_input_value(self, selector: str) -> str:
        return self.page.input_value(selector).strip()

    # ── Assertions (returns WebAssertions for chaining) ───────────────────────

    @property
    def assert_that(self):
        from skills.assertions.web_assertions import WebAssertions
        return WebAssertions(self.page)

    # ── Screenshot / Allure ───────────────────────────────────────────────────

    def screenshot(self, name: str = "screenshot") -> str:
        import os
        os.makedirs("reports/debug_logs", exist_ok=True)
        path = f"reports/debug_logs/{name}.png"
        self.page.screenshot(path=path)
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

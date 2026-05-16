"""
Web Assertions — chainable Playwright assertion layer with Allure integration.

Extends AssertionHelper with:
- Screenshot attached to Allure on assertion failure
- Soft assertion mode (collect all failures, report at end)
- Network response assertions

Usage:
    wa = WebAssertions(page)
    wa.url_contains("/feed").element_visible("[data-testid='dashboard']")

    # Soft mode — collect failures:
    with wa.soft() as s:
        s.url_contains("/feed")
        s.element_visible(".header")
    # raises at context exit if any failed
"""
import allure
import structlog
from playwright.sync_api import Page
from skills.base.assertion_helper import AssertionHelper

logger = structlog.get_logger(__name__)


class WebAssertions(AssertionHelper):
    def __init__(self, page: Page):
        super().__init__(page)
        self._failures: list[str] = []
        self._soft_mode = False

    def _assert(self, condition: bool, message: str) -> "WebAssertions":
        if not condition:
            if self._soft_mode:
                self._failures.append(message)
                self._screenshot_to_allure(label="soft_fail")
            else:
                self._screenshot_to_allure(label="assertion_failed")
                raise AssertionError(message)
        return self

    def _screenshot_to_allure(self, label: str = "screenshot"):
        try:
            screenshot = self.page.screenshot()
            allure.attach(
                screenshot,
                name=f"{label}_{self.page.url.split('/')[-1] or 'page'}",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:
            pass

    # ── Overrides with chaining ───────────────────────────────────────────────

    def url_contains(self, expected: str) -> "WebAssertions":
        current = self.page.url
        return self._assert(
            expected in current,
            f"[WebAssertions] URL should contain '{expected}'\n  Actual: '{current}'"
        )

    def url_is(self, expected: str) -> "WebAssertions":
        current = self.page.url
        return self._assert(
            current == expected,
            f"[WebAssertions] URL mismatch.\n  Expected: '{expected}'\n  Actual: '{current}'"
        )

    def element_visible(self, selector: str, description: str = "") -> "WebAssertions":
        label = description or selector
        return self._assert(
            self.page.is_visible(selector),
            f"[WebAssertions] Element not visible: '{label}'"
        )

    def element_hidden(self, selector: str, description: str = "") -> "WebAssertions":
        label = description or selector
        return self._assert(
            not self.page.is_visible(selector),
            f"[WebAssertions] Element should be hidden: '{label}'"
        )

    def element_enabled(self, selector: str, description: str = "") -> "WebAssertions":
        label = description or selector
        return self._assert(
            self.page.is_enabled(selector),
            f"[WebAssertions] Element should be ENABLED: '{label}'"
        )

    def element_disabled(self, selector: str, description: str = "") -> "WebAssertions":
        label = description or selector
        return self._assert(
            not self.page.is_enabled(selector),
            f"[WebAssertions] Element should be DISABLED: '{label}'"
        )

    def text_contains(self, selector: str, expected: str) -> "WebAssertions":
        actual = self.page.inner_text(selector).strip()
        return self._assert(
            expected in actual,
            f"[WebAssertions] '{selector}' text should contain '{expected}'\n  Actual: '{actual}'"
        )

    def text_equals(self, selector: str, expected: str) -> "WebAssertions":
        actual = self.page.inner_text(selector).strip()
        return self._assert(
            actual == expected,
            f"[WebAssertions] '{selector}' text mismatch.\n  Expected: '{expected}'\n  Actual: '{actual}'"
        )

    def page_has_text(self, expected: str) -> "WebAssertions":
        return self._assert(
            expected in self.page.content(),
            f"[WebAssertions] Page does not contain text: '{expected}'"
        )

    # ── Soft assertion context ────────────────────────────────────────────────

    def soft(self) -> "_SoftContext":
        return _SoftContext(self)

    # ── Allure helpers ────────────────────────────────────────────────────────

    def attach_screenshot(self, name: str = "screenshot") -> "WebAssertions":
        self._screenshot_to_allure(label=name)
        return self

    def attach_html(self, name: str = "page_html") -> "WebAssertions":
        try:
            allure.attach(
                self.page.content(),
                name=name,
                attachment_type=allure.attachment_type.HTML,
            )
        except Exception:
            pass
        return self


class _SoftContext:
    def __init__(self, wa: WebAssertions):
        self._wa = wa

    def __enter__(self) -> WebAssertions:
        self._wa._soft_mode = True
        self._wa._failures.clear()
        return self._wa

    def __exit__(self, *_):
        self._wa._soft_mode = False
        failures = self._wa._failures[:]
        self._wa._failures.clear()
        if failures:
            summary = "\n".join(f"  [{i+1}] {f}" for i, f in enumerate(failures))
            raise AssertionError(
                f"[WebAssertions] {len(failures)} soft assertion(s) failed:\n{summary}"
            )

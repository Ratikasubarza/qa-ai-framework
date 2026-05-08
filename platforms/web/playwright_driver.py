"""
Playwright Driver — web automation base driver.
Handles browser setup, teardown, and common page operations.
"""
import structlog
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import Optional
from config.settings import settings

logger = structlog.get_logger(__name__)

# Target environments
URLS = {
    "staging": "https://app-dev.thehono.com",
    "api":     "https://api-dev.thehono.com",
    "cms":     "https://cms-dev.thehono.com",
}


class PlaywrightDriver:
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless  = headless
        self.slow_mo   = slow_mo
        self._playwright = None
        self._browser:  Optional[Browser] = None
        self._context:  Optional[BrowserContext] = None
        self._page:     Optional[Page] = None

    def start(self, env: str = "staging") -> Page:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
        self._context = self._browser.new_context(
            base_url=URLS.get(env, URLS["staging"]),
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        self._page = self._context.new_page()
        logger.info("playwright_started", env=env, headless=self.headless)
        return self._page

    def stop(self):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("playwright_stopped")

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Driver not started. Call start() first.")
        return self._page

    def screenshot(self, name: str = "screenshot"):
        path = f"reports/allure/{name}.png"
        self._page.screenshot(path=path)
        logger.info("screenshot_saved", path=path)
        return path

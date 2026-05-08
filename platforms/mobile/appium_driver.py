"""
Appium Driver — Android mobile automation driver.
Supports: Native Android, React Native, Flutter apps.
Requires: Appium server running + Android device/emulator connected.
"""
import structlog
from typing import Optional
from appium import webdriver
from appium.options.android.uiautomator2.base import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = structlog.get_logger(__name__)

# Default Appium server
APPIUM_HOST = "http://localhost:4723"


class AppiumDriver:
    def __init__(
        self,
        app_package:  str,
        app_activity: str,
        device_name:  str = "emulator-5554",
        platform_version: str = "12.0",
        apk_path:     str | None = None,
        appium_host:  str = APPIUM_HOST,
        no_reset:     bool = True,
    ):
        self.app_package      = app_package
        self.app_activity     = app_activity
        self.device_name      = device_name
        self.platform_version = platform_version
        self.apk_path         = apk_path
        self.appium_host      = appium_host
        self.no_reset         = no_reset
        self.driver: Optional[webdriver.Remote] = None

    def start(self) -> webdriver.Remote:
        """Start Appium session."""
        options = UiAutomator2Options()
        options.platform_name         = "Android"
        options.platform_version      = self.platform_version
        options.device_name           = self.device_name
        options.app_package           = self.app_package
        options.app_activity          = self.app_activity
        options.no_reset              = self.no_reset
        options.auto_grant_permissions = True

        if self.apk_path:
            options.app = self.apk_path

        # Performance optimizations
        options.new_command_timeout   = 300
        options.set_capability('appium:pauseAfterAction', 500)
        options.android_install_timeout = 90000

        self.driver = webdriver.Remote(
            command_executor=self.appium_host,
            options=options,
        )
        logger.info(
            "appium_started",
            device=self.device_name,
            app=self.app_package,
        )
        return self.driver

    def stop(self):
        if self.driver:
            self.driver.quit()
            logger.info("appium_stopped")

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()

    # ── Element helpers ───────────────────────────────────────────────

    def find(self, by: str, value: str, timeout: int = 10):
        """Wait for element and return it."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            self.screenshot(f"find_failed_{value[:20]}")
            raise AssertionError(f"Element not found: [{by}] {value}")

    def find_by_id(self, resource_id: str, timeout: int = 10):
        return self.find(AppiumBy.ID, f"{self.app_package}:id/{resource_id}", timeout)

    def find_by_accessibility(self, label: str, timeout: int = 10):
        return self.find(AppiumBy.ACCESSIBILITY_ID, label, timeout)

    def find_by_text(self, text: str, timeout: int = 10):
        return self.find(AppiumBy.ANDROID_UIAUTOMATOR,
                         f'new UiSelector().text("{text}")', timeout)

    def find_by_xpath(self, xpath: str, timeout: int = 10):
        return self.find(AppiumBy.XPATH, xpath, timeout)

    def tap(self, by: str, value: str, timeout: int = 10):
        el = self.find(by, value, timeout)
        el.click()
        logger.debug("tap", element=value[:40])

    def type_text(self, by: str, value: str, text: str, timeout: int = 10):
        el = self.find(by, value, timeout)
        el.clear()
        el.send_keys(text)
        logger.debug("type_text", element=value[:40], text=text[:20])

    def screenshot(self, name: str = "screenshot"):
        path = f"reports/debug_logs/mobile_{name}.png"
        if self.driver:
            self.driver.save_screenshot(path)
            logger.info("screenshot_saved", path=path)
        return path

    def get_page_source(self) -> str:
        return self.driver.page_source if self.driver else ""

    def scroll_down(self):
        size   = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.8)
        end_y   = int(size["height"] * 0.2)
        self.driver.swipe(start_x, start_y, start_x, end_y, 800)

    def scroll_up(self):
        size    = self.driver.get_window_size()
        start_x = size["width"] // 2
        start_y = int(size["height"] * 0.2)
        end_y   = int(size["height"] * 0.8)
        self.driver.swipe(start_x, start_y, start_x, end_y, 800)

    def is_element_present(self, by: str, value: str, timeout: int = 5) -> bool:
        try:
            self.find(by, value, timeout)
            return True
        except AssertionError:
            return False

    def back(self):
        self.driver.back()

    def hide_keyboard(self):
        try:
            self.driver.hide_keyboard()
        except Exception:
            pass

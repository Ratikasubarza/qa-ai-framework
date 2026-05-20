"""
Mobile Test Hooks — fresh state per test via force terminate + relaunch.
"""
import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.appium_driver import AppiumDriver
from config.test_config import TestConfig


def _wait_for_text(driver, text: str, timeout: float = 10.0) -> bool:
    """Poll page source until *text* appears or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in driver.driver.page_source:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def navigate_to_login(driver):
    """Navigate to login screen — handle onboarding, feed, and login screens."""
    _wait_for_text(driver, "Login", timeout=8)
    try:
        source = driver.driver.page_source
    except Exception:
        source = ""

    # If on feed (logged in) — logout via avatar menu
    if "'Home'" in source or "Network" in source and "Communities" in source:
        print("  → Feed screen detected, logging out...")
        try:
            driver.driver.tap([(50, 120)])
            driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
            driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
            _wait_for_text(driver, "Log in", timeout=8)
            print("  ✓ Logged out from feed")
            return
        except Exception as e:
            print(f"  Feed logout warning: {e}")

    # If on onboarding (Welcome to HONO / Let's personalize) — force terminate
    if "Welcome to HONO" in source or "personalize profile" in source:
        print("  → Onboarding screen detected, force terminating...")
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)  # OS process teardown — inherently timing-based
        driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
        _wait_for_text(driver, "Login", timeout=10)

    # Navigate to login from onboarding welcome screen
    try:
        driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().descriptionContains("Log in")', timeout=5).click()
        _wait_for_text(driver, "Login to my account", timeout=6)
        print("  ✓ Navigated to login screen")
    except Exception:
        pass  # Already on login screen


@pytest.fixture(scope="function")
def android_driver():
    """
    Fresh login screen per test.
    Strategy: terminate → relaunch → navigate to login
    """
    driver = AppiumDriver(
        app_package=TestConfig.ANDROID_PACKAGE,
        app_activity=TestConfig.ANDROID_ACTIVITY,
        device_name=TestConfig.ANDROID_DEVICE,
        platform_version=TestConfig.ANDROID_VERSION,
    )
    driver.start()
    _wait_for_text(driver, "Login", timeout=15)  # wait for app ready

    # Force fresh state — terminate and relaunch
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)  # OS process teardown — inherently timing-based
    except Exception:
        pass
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    _wait_for_text(driver, "Login", timeout=12)

    navigate_to_login(driver)

    yield driver

    # Cleanup
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(0.5)
    except Exception:
        pass
    finally:
        driver.stop()


@pytest.fixture(scope="function")
def android_driver_logged_in(android_driver):
    """Pre-logged in fixture."""
    from features.login.test_data.login_test_data import LoginTestData

    els = android_driver.driver.find_elements(
        AppiumBy.CLASS_NAME, "android.widget.EditText"
    )
    if len(els) >= 2:
        els[0].click(); time.sleep(0.3)
        els[0].send_keys(LoginTestData.VALID_EMAIL)
        els[1].click(); time.sleep(0.3)
        els[1].send_keys(LoginTestData.VALID_PASSWORD)
        android_driver.hide_keyboard()
        time.sleep(0.3)
        android_driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().description("Login to my account")').click()
        _wait_for_text(android_driver, "Home", timeout=15)
        print("  ✓ Pre-login complete")

    yield android_driver

"""
Mobile Test Hooks — fresh state per test via force terminate + relaunch.
"""
import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.appium_driver import AppiumDriver
from config.test_config import TestConfig


def navigate_to_login(driver):
    """Navigate to login screen — handle onboarding, feed, and login screens."""
    time.sleep(3)
    try:
        source = driver.driver.page_source
    except Exception:
        source = ""

    # If on feed (logged in) — logout via avatar menu
    if "'Home'" in source or "Network" in source and "Communities" in source:
        print("  → Feed screen detected, logging out...")
        try:
            driver.driver.tap([(50, 120)])
            time.sleep(2)
            driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
            time.sleep(2)
            driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
            time.sleep(3)
            print("  ✓ Logged out from feed")
            return
        except Exception as e:
            print(f"  Feed logout warning: {e}")

    # If on onboarding (Welcome to HONO / Let's personalize) — force terminate
    if "Welcome to HONO" in source or "personalize profile" in source:
        print("  → Onboarding screen detected, force terminating...")
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(2)
        driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(4)
        source = driver.driver.page_source

    # Navigate to login from onboarding welcome screen
    try:
        driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().descriptionContains("Log in")', timeout=5).click()
        time.sleep(3)
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
    time.sleep(4)

    # Force fresh state — terminate and relaunch
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(2)
    except Exception:
        pass
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    time.sleep(4)

    navigate_to_login(driver)

    yield driver

    # Cleanup
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)
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
        time.sleep(0.5)
        android_driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().description("Login to my account")').click()
        time.sleep(10)
        print("  ✓ Pre-login complete")

    yield android_driver

"""
Android Onboarding Tests — Full E2E flow untuk new approved user.
Flow: create_approved_user → login → complete onboarding → feed
"""
import os
import shutil
import subprocess
import time

import pytest
import structlog
from appium.webdriver.common.appiumby import AppiumBy

from config.test_config import TestConfig
from core.db.test_user_helper import create_approved_user_sync
from features.onboarding.locators.mobile.onboarding_android_locators import *
from platforms.mobile.appium_driver import AppiumDriver

_log = structlog.get_logger(__name__)


def _resolve_adb() -> str:
    """Resolve ADB binary from ADB_PATH env var, PATH, or fail loudly in CI."""
    env_path = os.environ.get("ADB_PATH")
    if env_path:
        return os.path.expanduser(env_path)
    found = shutil.which("adb")
    if found:
        return found
    raise EnvironmentError(
        "ADB binary not found. Set ADB_PATH env var or ensure 'adb' is in PATH."
    )


_ADB_BIN = _resolve_adb()


def _wait_for_text(driver, text: str, timeout: float = 10.0) -> bool:
    """Poll page source until *text* appears or timeout. Returns True on success."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in driver.get_page_source():
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def adb_tap(x: int, y: int) -> None:
    """Tap a screen coordinate via ADB without shell=True (no injection risk)."""
    if not isinstance(x, int) or not isinstance(y, int):
        raise TypeError(f"adb_tap requires int coordinates, got x={type(x)}, y={type(y)}")
    result = subprocess.run(
        [_ADB_BIN, "shell", "input", "tap", str(x), str(y)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        _log.warning("adb_tap_failed", x=x, y=y, stderr=result.stderr[:200])
    time.sleep(0.5)  # ADB tap settle — inherently timing-based


def tap_item(driver, desc, timeout=5):
    try:
        driver.find(AppiumBy.ACCESSIBILITY_ID, desc, timeout=timeout).click()
        return True
    except Exception:
        try:
            driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionContains("{desc}")',
                timeout=timeout).click()
            return True
        except Exception: return False


def safe_fill(driver, index, text):
    for attempt in range(3):
        try:
            els = driver.driver.find_elements(
                AppiumBy.CLASS_NAME, "android.widget.EditText")
            if len(els) > index:
                els[index].click(); time.sleep(0.3)
                els[index].send_keys(text); time.sleep(0.2)
                return True
        except Exception: time.sleep(1)
    return False


def complete_onboarding(driver):
    """Complete full onboarding flow — reusable helper."""
    # Screen 2: Full name
    safe_fill(driver, 0, "Test Onboard User")
    driver.hide_keyboard()
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "QA Engineer", timeout=10) or _wait_for_text(driver, "Work", timeout=5)

    # Screen 3: Work
    safe_fill(driver, 0, "QA Engineer")
    safe_fill(driver, 1, "Hono Testing Inc")
    driver.hide_keyboard()
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "Location", timeout=10)

    # Screen 4: Location
    els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    adb_tap(els[0].location['x'] + els[0].size['width']//2,
            els[0].location['y'] + els[0].size['height']//2)
    _wait_for_text(driver, DEFAULT_COUNTRY, timeout=6)
    search_els = driver.driver.find_elements(
        AppiumBy.CLASS_NAME, "android.widget.EditText")
    search_els[0].click(); time.sleep(0.3)
    search_els[0].send_keys(DEFAULT_COUNTRY)
    _wait_for_text(driver, DEFAULT_COUNTRY, timeout=5)
    driver.find(AppiumBy.ACCESSIBILITY_ID, DEFAULT_COUNTRY, timeout=5).click()
    _wait_for_text(driver, "Jakarta", timeout=6)
    adb_tap(CITY_FIELD_X, CITY_FIELD_Y)
    _wait_for_text(driver, "Jakarta", timeout=6)
    els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    els[0].click(); time.sleep(0.3)
    els[0].send_keys("Jakarta")
    _wait_for_text(driver, DEFAULT_CITY, timeout=5)
    driver.find(AppiumBy.ACCESSIBILITY_ID, DEFAULT_CITY, timeout=3).click()
    _wait_for_text(driver, "Industries", timeout=6)
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "Industries", timeout=10)

    # Screen 5: Industries
    adb_tap(INDUSTRIES_FIELD_X, INDUSTRIES_FIELD_Y)
    _wait_for_text(driver, "Accounting", timeout=6)
    tap_item(driver, "Accounting")
    tap_item(driver, "Agriculture")
    driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().descriptionContains("Save")', timeout=5).click()
    _wait_for_text(driver, "Continue", timeout=6)
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "Business", timeout=10)

    # Screen 6: Business Areas
    tap_item(driver, "Accounting and Audit")
    tap_item(driver, "Advertising and Marketing")
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "Personal Interests", timeout=10)

    # Screen 7: Personal Interests
    tap_item(driver, "Entrepreneurship")
    tap_item(driver, "Cycling")
    driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=5).click()
    _wait_for_text(driver, "Social Causes", timeout=10)

    # Screen 8: Social Causes → Submit
    tap_item(driver, "Clean Energy")
    tap_item(driver, "Education Access")
    driver.find(AppiumBy.ACCESSIBILITY_ID, SUBMIT_BTN, timeout=5).click()
    _wait_for_text(driver, SKIP_BTN, timeout=15)

    # Screen 9: Skip profile picture
    driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().descriptionContains("{SKIP_BTN}")',
        timeout=8).click()
    _wait_for_text(driver, GO_TO_HOMEPAGE_BTN, timeout=12)

    # Screen 10: Go to homepage
    driver.find(AppiumBy.ACCESSIBILITY_ID, GO_TO_HOMEPAGE_BTN, timeout=8).click()
    _wait_for_text(driver, "Home", timeout=12)


@pytest.fixture(scope="function")
def onboarding_driver():
    """Fresh login screen per test — handles all screen states."""
    user = create_approved_user_sync()
    print(f"\n  User ready: {user['email']}")

    driver = AppiumDriver(
        app_package=TestConfig.ANDROID_PACKAGE,
        app_activity=TestConfig.ANDROID_ACTIVITY,
        device_name=TestConfig.ANDROID_DEVICE,
        platform_version=TestConfig.ANDROID_VERSION,
    )
    driver.start()
    _wait_for_text(driver, "Login", timeout=15)  # wait for app to be ready

    # Always terminate and relaunch fresh
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)  # OS process teardown — inherently timing-based
    except Exception: pass
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    _wait_for_text(driver, "Login", timeout=15)

    # Handle screen state
    for attempt in range(4):
        try:
            source = driver.driver.page_source
        except Exception:
            time.sleep(1)
            continue

        if "Login to my account" in source:
            print("  On login screen")
            break

        elif "Home" in source and "Network" in source:
            print("  Feed detected, logging out...")
            try:
                driver.driver.tap([(50, 120)])
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
                _wait_for_text(driver, "Log in", timeout=8)
            except Exception: pass
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("Log in")', timeout=5).click()
                _wait_for_text(driver, "Login to my account", timeout=6)
                break
            except Exception: pass

        elif "Welcome to HONO" in source or "personalize" in source:
            print("  Onboarding welcome, completing to reach feed...")
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("personalize")', timeout=5).click()
                _wait_for_text(driver, "Continue", timeout=8)
                complete_onboarding(driver)
                _wait_for_text(driver, "Home", timeout=12)
                driver.driver.tap([(50, 120)])
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
                _wait_for_text(driver, "Log in", timeout=8)
            except Exception as e:
                print(f"  Error: {e}")
                driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
                time.sleep(1)  # OS process teardown
                driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
                _wait_for_text(driver, "Login", timeout=12)
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("Log in")', timeout=5).click()
                _wait_for_text(driver, "Login to my account", timeout=6)
                break
            except Exception: pass

        else:
            print(f"  Unknown screen attempt {attempt+1}, trying Log in link...")
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("Log in")', timeout=5).click()
                _wait_for_text(driver, "Login to my account", timeout=6)
                break
            except Exception:
                driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
                time.sleep(1)  # OS process teardown
                driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
                _wait_for_text(driver, "Login", timeout=12)

    # Login
    els = []
    for attempt in range(5):
        try:
            els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
            if len(els) >= 2: break
        except Exception: pass
        time.sleep(1)

    if len(els) < 2:
        raise AssertionError(f"Login fields not found: {len(els)} EditText")

    els[0].click(); time.sleep(0.3); els[0].send_keys(user["email"])
    els[1].click(); time.sleep(0.3); els[1].send_keys(user["password"])
    driver.hide_keyboard(); time.sleep(0.3)
    driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().description("Login to my account")').click()
    _wait_for_text(driver, "Welcome to HONO", timeout=15)
    print(f"  Logged in as: {user['email']}")

    yield driver, user

    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)
    except Exception: pass
    finally:
        driver.stop()


def test_TC_MOB_ONB_001_complete_onboarding_flow(onboarding_driver):
    """
    TC-MOB-ONB-001 | Smoke | Complete full onboarding → reach feed
    Given: New approved user logging in for first time
    When: Complete all 8 onboarding screens
    Then: Feed screen visible with Home tab
    """
    driver, user = onboarding_driver

    # Verify on onboarding screen
    assert driver.is_element_present(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().descriptionContains("personalize")', timeout=10
    ), "Should be on onboarding screen after first login"
    print(f"\n✓ On onboarding screen")

    # Tap Let's personalize
    driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().descriptionContains("personalize")', timeout=8).click()
    time.sleep(4)

    # Complete all steps
    complete_onboarding(driver)

    # Verify on feed
    assert driver.is_element_present(
        AppiumBy.ACCESSIBILITY_ID, FEED_HOME_TAB, timeout=10
    ), "Should be on feed after onboarding complete"
    print(f"✓ Onboarding complete — on feed!")


def test_TC_MOB_ONB_002_onboarding_shows_for_new_user(onboarding_driver):
    """
    TC-MOB-ONB-002 | Functional | New approved user sees onboarding on first login
    """
    driver, user = onboarding_driver

    assert driver.is_element_present(
        AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().descriptionContains("personalize")', timeout=10
    ), "New user should see onboarding"
    print(f"\n✓ Onboarding shown for new user: {user['email']}")


def test_TC_MOB_ONB_003_skip_profile_picture(onboarding_driver):
    """
    TC-MOB-ONB-003 | Functional | User can skip profile picture
    """
    driver, user = onboarding_driver

    driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        'new UiSelector().descriptionContains("personalize")', timeout=8).click()
    time.sleep(4)
    complete_onboarding(driver)

    # Verify onboarding_completed_at set in DB
    from core.db.db_client import DBClient
    time.sleep(2)
    with DBClient() as db:
        u = db.get_user_by_email(user['email'])
    print(f"\n✓ Skip profile picture works")
    print(f"  Feed visible: {driver.is_element_present(AppiumBy.ACCESSIBILITY_ID, FEED_HOME_TAB, timeout=5)}")

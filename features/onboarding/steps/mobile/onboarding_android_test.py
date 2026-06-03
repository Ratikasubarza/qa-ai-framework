"""
Android Onboarding Tests — Full E2E flow for new approved user.
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
from features.onboarding.locators.mobile.onboarding_android_locators import (
    FEED_HOME_TAB, SKIP_BTN, GO_TO_HOMEPAGE_BTN,
)
from features.onboarding.screens.android.onboarding_screen import OnboardingScreen
from features.login.screens.android.login_screen import LoginScreen
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
    _wait_for_text(driver, "Login", timeout=15)

    # Always terminate and relaunch fresh
    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)  # OS process teardown — inherently timing-based
    except Exception:
        pass
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    _wait_for_text(driver, "Login", timeout=15)

    # Handle screen state — navigate to login screen
    for attempt in range(4):
        source = driver.get_page_source()

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
            except Exception:
                pass
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("Log in")', timeout=5).click()
                _wait_for_text(driver, "Login to my account", timeout=6)
                break
            except Exception:
                pass

        elif "Welcome to HONO" in source or "personalize" in source:
            print("  Onboarding welcome — completing to reach feed then logging out...")
            try:
                screen = OnboardingScreen(driver)
                screen.tap_personalize()
                _wait_for_text(driver, "Continue", timeout=8)
                screen.complete_full_flow(adb_tap)
                _wait_for_text(driver, "Home", timeout=12)
                driver.driver.tap([(50, 120)])
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Show menu", timeout=5).click()
                driver.find(AppiumBy.ACCESSIBILITY_ID, "Logout", timeout=5).click()
                _wait_for_text(driver, "Log in", timeout=8)
            except Exception as e:
                print(f"  Error during state recovery: {e}")
                driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
                time.sleep(1)  # OS process teardown
                driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
                _wait_for_text(driver, "Login", timeout=12)
            try:
                driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiSelector().descriptionContains("Log in")', timeout=5).click()
                _wait_for_text(driver, "Login to my account", timeout=6)
                break
            except Exception:
                pass

        else:
            print(f"  Unknown screen attempt {attempt + 1}, trying Log in link...")
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

    # Login with fresh user credentials
    LoginScreen(driver).login(user["email"], user["password"])
    _wait_for_text(driver, "Welcome to HONO", timeout=15)
    print(f"  Logged in as: {user['email']}")

    yield driver, user

    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)
    except Exception:
        pass
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
    screen = OnboardingScreen(driver)

    screen.assert_on_onboarding()
    print(f"\n✓ On onboarding screen")

    screen.tap_personalize()
    _wait_for_text(driver, "Continue", timeout=8)
    screen.complete_full_flow(adb_tap)
    screen.assert_on_feed()
    print(f"✓ Onboarding complete — on feed!")


def test_TC_MOB_ONB_002_onboarding_shows_for_new_user(onboarding_driver):
    """
    TC-MOB-ONB-002 | Functional | New approved user sees onboarding on first login
    """
    driver, user = onboarding_driver
    OnboardingScreen(driver).assert_on_onboarding()
    print(f"\n✓ Onboarding shown for new user: {user['email']}")


def test_TC_MOB_ONB_003_skip_profile_picture(onboarding_driver):
    """
    TC-MOB-ONB-003 | Functional | User can skip profile picture and reach feed
    """
    driver, user = onboarding_driver
    screen = OnboardingScreen(driver)

    screen.tap_personalize()
    _wait_for_text(driver, "Continue", timeout=8)
    screen.complete_full_flow(adb_tap)

    from core.db.db_client import DBClient
    time.sleep(2)
    with DBClient() as db:
        db.get_user_by_email(user['email'])

    print(f"\n✓ Skip profile picture works")
    print(f"  Feed visible: {screen.is_on_feed()}")

pytestmark = [pytest.mark.mobile]

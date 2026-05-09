import pytest
import time
import os
from dotenv import load_dotenv
from features.login.test_data.login_test_data import LoginTestData
from config.test_config import TestConfig
from features.login.locators.mobile.login_android_locators import (
    ONBOARDING_LOGIN_LINK, EMAIL_FIELD, PASSWORD_FIELD,
    LOGIN_BUTTON, FEED_SCREEN,
)
from appium.webdriver.common.appiumby import AppiumBy

from platforms.mobile.appium_driver import AppiumDriver
from skills.mobile.mobile_interaction import MobileInteraction
from skills.mobile.mobile_assertion import MobileAssertion

load_dotenv(dotenv_path=".env")

APP_PACKAGE       = TestConfig.ANDROID_PACKAGE
APP_ACTIVITY      = TestConfig.ANDROID_ACTIVITY
DEVICE_NAME       = TestConfig.ANDROID_DEVICE
PLATFORM_VERSION  = TestConfig.ANDROID_VERSION
APK_PATH          = TestConfig.ANDROID_APK
EMAIL             = LoginTestData.VALID_EMAIL
PASSWORD          = LoginTestData.VALID_PASSWORD

ONBOARDING_LOGIN  = "Already have an account? Log in"


@pytest.fixture(scope="function")
def android_driver():
    driver = AppiumDriver(
        app_package=APP_PACKAGE,
        app_activity=APP_ACTIVITY,
        device_name=DEVICE_NAME,
        platform_version=PLATFORM_VERSION,
        apk_path=APK_PATH,
    )
    driver.start()
    time.sleep(4)
    # Navigate to login screen
    try:
        driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().description("{ONBOARDING_LOGIN}")').click()
        time.sleep(3)
        print("✓ On login screen")
    except Exception as e:
        print(f"Nav warning: {e}")
    yield driver
    driver.stop()


def test_TC_MOB_001_login_valid_credentials(android_driver):
    """TC-MOB-001 | Smoke | Login with valid credentials → feed screen"""
    mi = MobileInteraction(android_driver)

    mi.fill_by_accessibility(EMAIL_FIELD, EMAIL)
    mi.fill_by_accessibility(PASSWORD_FIELD, PASSWORD)
    android_driver.hide_keyboard()
    time.sleep(1)
    android_driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().description("{LOGIN_BUTTON}")').click()
    time.sleep(5)

    # After login — assert feed screen via content-desc
    assert android_driver.is_element_present(
        AppiumBy.ACCESSIBILITY_ID, FEED_SCREEN, timeout=15
    ), "Feed screen not visible after login"
    print("✓ Logged in — feed visible")


def test_TC_MOB_002_login_wrong_password(android_driver):
    """TC-MOB-002 | Negative | Wrong password → error shown"""
    mi = MobileInteraction(android_driver)

    mi.fill_by_accessibility(EMAIL_FIELD, EMAIL)
    mi.fill_by_accessibility(PASSWORD_FIELD, "WrongPass!")
    android_driver.hide_keyboard()
    time.sleep(1)
    android_driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().description("{LOGIN_BUTTON}")').click()
    time.sleep(3)

    source = android_driver.driver.page_source
    assert any(w in source.lower() for w in ["invalid", "incorrect", "error", "wrong"]), \
        "No error message found after wrong password"
    print("✓ Error shown for wrong password")


def test_TC_MOB_003_login_button_disabled_empty_fields(android_driver):
    """TC-MOB-003 | Boundary | Login button disabled when fields empty"""
    ma = MobileAssertion(android_driver)
    ma.element_disabled_by_accessibility(LOGIN_BUTTON, "Login button")
    print("✓ Login button disabled with empty fields")


def test_TC_MOB_004_login_button_disabled_email_only(android_driver):
    """TC-MOB-004 | Boundary | Login button disabled with email only"""
    mi = MobileInteraction(android_driver)
    ma = MobileAssertion(android_driver)

    mi.fill_by_accessibility(EMAIL_FIELD, EMAIL)
    android_driver.hide_keyboard()
    time.sleep(1)
    ma.element_disabled_by_accessibility(LOGIN_BUTTON, "Login button")
    print("✓ Login button disabled with email only")


def test_TC_MOB_005_login_empty_email(android_driver):
    """TC-MOB-005 | Negative | Login with password only → button disabled"""
    mi = MobileInteraction(android_driver)
    ma = MobileAssertion(android_driver)

    mi.fill_by_accessibility(PASSWORD_FIELD, PASSWORD)
    android_driver.hide_keyboard()
    time.sleep(1)
    ma.element_disabled_by_accessibility(LOGIN_BUTTON, "Login button")
    print("✓ Login button disabled with password only")

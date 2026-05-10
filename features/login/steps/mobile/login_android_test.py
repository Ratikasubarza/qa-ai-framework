"""
Android Login Tests — Hono Flutter App
Uses EditText by index for Flutter compatibility.
"""
import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy
from skills.mobile.mobile_interaction import MobileInteraction
from skills.mobile.mobile_assertion import MobileAssertion
from features.login.test_data.login_test_data import LoginTestData
from features.login.locators.mobile.login_android_locators import (
    LOGIN_BUTTON, FEED_SCREEN,
)
from config.test_config import TestConfig


def fill_login_form(android_driver, email=None, password=None):
    """Fill login form using EditText index — Flutter compatible."""
    els = android_driver.driver.find_elements(
        AppiumBy.CLASS_NAME, "android.widget.EditText"
    )
    if email is not None and len(els) >= 1:
        els[0].click()
        time.sleep(0.3)
        els[0].send_keys(email)
    if password is not None and len(els) >= 2:
        els[1].click()
        time.sleep(0.3)
        els[1].send_keys(password)
    android_driver.hide_keyboard()
    time.sleep(0.5)


def test_TC_MOB_001_login_valid_credentials(android_driver):
    """TC-MOB-001 | Smoke | Login with valid credentials → feed screen"""
    fill_login_form(android_driver, LoginTestData.VALID_EMAIL, LoginTestData.VALID_PASSWORD)
    android_driver.find(AppiumBy.ANDROID_UIAUTOMATOR,
        f'new UiSelector().description("{LOGIN_BUTTON}")').click()
    time.sleep(8)
    assert android_driver.is_element_present(
        AppiumBy.ACCESSIBILITY_ID, FEED_SCREEN, timeout=10
    ), "Feed screen not visible after login"
    print("✓ Login success — feed visible")


def test_TC_MOB_002_login_wrong_password(android_driver):
    """TC-MOB-002 | Negative | Wrong password shows error"""
    fill_login_form(android_driver, LoginTestData.VALID_EMAIL, "WrongPass!")
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
    fill_login_form(android_driver, email=LoginTestData.VALID_EMAIL)
    ma = MobileAssertion(android_driver)
    ma.element_disabled_by_accessibility(LOGIN_BUTTON, "Login button")
    print("✓ Login button disabled with email only")


def test_TC_MOB_005_login_empty_email(android_driver):
    """TC-MOB-005 | Negative | Login button disabled with password only"""
    fill_login_form(android_driver, password=LoginTestData.VALID_PASSWORD)
    ma = MobileAssertion(android_driver)
    ma.element_disabled_by_accessibility(LOGIN_BUTTON, "Login button")
    print("✓ Login button disabled with password only")

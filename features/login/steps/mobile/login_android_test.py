"""
Android Login Tests — Hono Flutter App
Uses LoginScreen screen object for all interactions.
"""
import pytest
from appium.webdriver.common.appiumby import AppiumBy
from features.login.screens.android.login_screen import LoginScreen
from features.login.test_data.login_test_data import LoginTestData
from features.login.locators.mobile.login_android_locators import (
    LOGIN_BUTTON, FEED_SCREEN,
)

pytestmark = [pytest.mark.mobile]


def test_TC_MOB_001_login_valid_credentials(android_driver):
    """TC-MOB-001 | Smoke | Login with valid credentials → feed screen"""
    LoginScreen(android_driver).login(
        LoginTestData.VALID_EMAIL, LoginTestData.VALID_PASSWORD
    ).assert_login_success()


def test_TC_MOB_002_login_wrong_password(android_driver):
    """TC-MOB-002 | Negative | Wrong password shows error"""
    LoginScreen(android_driver).login(
        LoginTestData.VALID_EMAIL, "WrongPass!"
    ).assert_login_failed()


def test_TC_MOB_003_login_button_disabled_empty_fields(android_driver):
    """TC-MOB-003 | Boundary | Login button disabled when fields empty"""
    LoginScreen(android_driver).assert_button_disabled()


def test_TC_MOB_004_login_button_disabled_email_only(android_driver):
    """TC-MOB-004 | Boundary | Login button disabled with email only"""
    LoginScreen(android_driver).enter_email(LoginTestData.VALID_EMAIL).assert_button_disabled()


def test_TC_MOB_005_login_empty_email(android_driver):
    """TC-MOB-005 | Negative | Login button disabled with password only"""
    LoginScreen(android_driver).enter_password(LoginTestData.VALID_PASSWORD).assert_button_disabled()

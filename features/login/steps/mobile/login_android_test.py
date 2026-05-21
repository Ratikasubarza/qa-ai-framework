"""Login Android Tests — Hono Flutter App"""
import allure
import pytest

from features.login.screens.android.login_screen import LoginScreen
from features.login.test_data.login_test_data import LoginTestData

pytestmark = [
    allure.feature("Login"),
    allure.suite("Android"),
]


@pytest.mark.smoke
@pytest.mark.mobile
def test_TC_MOB_001_login_valid_credentials(android_driver):
    """TC-MOB-001 | Smoke | Valid credentials → feed screen"""
    (
        LoginScreen(android_driver)
        .ensure_on_login_screen()
        .login(LoginTestData.VALID_EMAIL, LoginTestData.VALID_PASSWORD)
        .assert_login_success()
    )


@pytest.mark.negative
@pytest.mark.mobile
def test_TC_MOB_002_login_wrong_password(android_driver):
    """TC-MOB-002 | Negative | Wrong password shows error message"""
    (
        LoginScreen(android_driver)
        .ensure_on_login_screen()
        .login(LoginTestData.VALID_EMAIL, LoginTestData.WRONG_PASSWORD)
        .assert_login_failed()
    )


@pytest.mark.mobile
def test_TC_MOB_003_login_button_disabled_empty_fields(android_driver):
    """TC-MOB-003 | Boundary | Login button disabled when all fields empty"""
    LoginScreen(android_driver).ensure_on_login_screen().assert_button_disabled()


@pytest.mark.mobile
def test_TC_MOB_004_login_button_disabled_email_only(android_driver):
    """TC-MOB-004 | Boundary | Login button disabled with only email filled"""
    (
        LoginScreen(android_driver)
        .ensure_on_login_screen()
        .enter_email(LoginTestData.VALID_EMAIL)
        .assert_button_disabled()
    )


@pytest.mark.mobile
def test_TC_MOB_005_login_button_disabled_password_only(android_driver):
    """TC-MOB-005 | Boundary | Login button disabled with only password filled"""
    (
        LoginScreen(android_driver)
        .ensure_on_login_screen()
        .enter_password(LoginTestData.VALID_PASSWORD)
        .assert_button_disabled()
    )

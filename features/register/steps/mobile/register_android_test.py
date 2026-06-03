"""
Android Register Tests — Hono Flutter App
POST /v1/users/register equivalent on mobile.
"""
import asyncio
import os
import time

import httpx
import pytest
from appium.webdriver.common.appiumby import AppiumBy

from config.test_config import TestConfig, APIEndpoints
from features.register.locators.mobile.register_android_locators import (
    JOIN_COMMUNITY_BTN, APPLY_NOW_BTN, VERIFY_EMAIL_SCREEN,
)
from features.register.screens.android.register_screen import RegisterScreen
from features.register.test_data.register_android_test_data import RegisterAndroidTestData

pytestmark = [pytest.mark.mobile]


def _wait_for_text(driver, text: str, timeout: float = 10.0) -> bool:
    """Poll page source until *text* appears or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if text in driver.get_page_source():
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="function")
def register_driver():
    """Fresh app on register screen per test."""
    from platforms.mobile.appium_driver import AppiumDriver

    driver = AppiumDriver(
        app_package=TestConfig.ANDROID_PACKAGE,
        app_activity=TestConfig.ANDROID_ACTIVITY,
        device_name=TestConfig.ANDROID_DEVICE,
        platform_version=TestConfig.ANDROID_VERSION,
    )
    driver.start()
    _wait_for_text(driver, "Login", timeout=15)
    driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
    time.sleep(1)  # OS process teardown — inherently timing-based
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    _wait_for_text(driver, "Login", timeout=12)

    # Navigate to register screen
    try:
        RegisterScreen(driver).tap_join_community()
        _wait_for_text(driver, "Apply", timeout=8)
        print("  ✓ On register screen")
    except Exception as e:
        print(f"  Navigation warning: {e}")

    yield driver

    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(0.5)
    except Exception:
        pass
    finally:
        driver.stop()


def test_TC_MOB_REG_001_register_valid_data(register_driver):
    """
    TC-MOB-REG-001 | Smoke | Register with valid data → verify email screen
    Note: May skip if Resend daily email quota is reached
    """
    async def _check_quota():
        async with httpx.AsyncClient(
            base_url=os.getenv("HONO_API_URL"),
            headers={"x-api-key": os.getenv("HONO_API_KEY")},
            timeout=10,
        ) as c:
            r = await c.post(APIEndpoints.REGISTER, json={
                "fullname": "quota check",
                "email": f"quotacheck+{int(time.time())}@mailinator.com",
                "phone_number": "811111111",
                "phone_country_code": "ID",
                "linkedin": "https://linkedin.com/in/quotacheck",
            })
            return r.status_code, r.json().get("message", "")

    status, msg = asyncio.get_event_loop().run_until_complete(_check_quota())
    if status == 500 and "email sending quota" in msg:
        pytest.skip("Resend daily email quota reached — run tomorrow")

    payload = RegisterAndroidTestData.valid_payload()
    screen = RegisterScreen(register_driver)
    screen.fill_form(
        fullname=payload["fullname"],
        email=payload["email"],
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    ).tap_apply()

    _wait_for_text(register_driver, VERIFY_EMAIL_SCREEN, timeout=12)
    screen.assert_on_verify_email_screen()
    print(f"\n✓ Register success — verify email screen shown")
    print(f"  Email: {payload['email']}")


def test_TC_MOB_REG_002_apply_button_disabled_empty_form(register_driver):
    """
    TC-MOB-REG-002 | Boundary | Apply button disabled when form empty
    """
    RegisterScreen(register_driver).assert_apply_button_disabled()
    print("\n✓ Apply button disabled with empty form")


def test_TC_MOB_REG_003_apply_button_disabled_partial_form(register_driver):
    """
    TC-MOB-REG-003 | Boundary | Apply button disabled with partial data (name + email only)
    """
    payload = RegisterAndroidTestData.valid_payload()
    (
        RegisterScreen(register_driver)
        .fill_form(fullname=payload["fullname"], email=payload["email"])
        .assert_apply_button_disabled()
    )
    print("\n✓ Apply button disabled with partial form")


def test_TC_MOB_REG_004_register_invalid_email(register_driver):
    """
    TC-MOB-REG-004 | Negative | Invalid email format does not proceed to verify screen
    """
    payload = RegisterAndroidTestData.valid_payload()
    screen = RegisterScreen(register_driver)
    screen.fill_form(
        fullname=payload["fullname"],
        email=RegisterAndroidTestData.INVALID_EMAIL,
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    )
    if screen.is_apply_button_enabled():
        screen.tap_apply()
        _wait_for_text(register_driver, "error", timeout=5)
        screen.assert_not_on_verify_email_screen()
    print("\n✓ Invalid email handled correctly")


def test_TC_MOB_REG_005_duplicate_email_shows_error(register_driver):
    """
    TC-MOB-REG-005 | Negative | Duplicate email shows error
    """
    from features.login.test_data.login_test_data import LoginTestData

    payload = RegisterAndroidTestData.valid_payload()
    screen = RegisterScreen(register_driver)
    screen.fill_form(
        fullname=payload["fullname"],
        email=LoginTestData.VALID_EMAIL,  # Already registered
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    ).tap_apply()

    _wait_for_text(register_driver, VERIFY_EMAIL_SCREEN, timeout=8)
    source = register_driver.get_page_source()
    assert VERIFY_EMAIL_SCREEN not in source or \
           any(w in source.lower() for w in ["error", "already", "exist", "duplicate"]), \
        "Duplicate email should show error"
    print("\n✓ Duplicate email handled")

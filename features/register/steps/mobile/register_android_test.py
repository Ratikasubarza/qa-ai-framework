"""
Android Register Tests — Hono Flutter App
POST /v1/users/register equivalent on mobile.
"""
import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy
from features.register.test_data.register_android_test_data import RegisterAndroidTestData
from features.register.locators.mobile.register_android_locators import (
    JOIN_COMMUNITY_BTN, APPLY_NOW_BTN,
    VERIFY_EMAIL_SCREEN, OPEN_EMAIL_BTN,
    FULLNAME_INDEX, EMAIL_INDEX, PHONE_INDEX, LINKEDIN_INDEX,
)
from config.test_config import TestConfig


def fill_register_form(driver, fullname=None, email=None, phone=None, linkedin=None):
    """Fill register form using EditText index."""
    els = driver.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
    
    if fullname is not None and len(els) > FULLNAME_INDEX:
        els[FULLNAME_INDEX].click(); time.sleep(0.3)
        els[FULLNAME_INDEX].send_keys(fullname)
    
    if email is not None and len(els) > EMAIL_INDEX:
        els[EMAIL_INDEX].click(); time.sleep(0.3)
        els[EMAIL_INDEX].send_keys(email)
    
    if phone is not None and len(els) > PHONE_INDEX:
        els[PHONE_INDEX].click(); time.sleep(0.3)
        els[PHONE_INDEX].send_keys(phone)
    
    if linkedin is not None and len(els) > LINKEDIN_INDEX:
        els[LINKEDIN_INDEX].click(); time.sleep(0.3)
        els[LINKEDIN_INDEX].send_keys(linkedin)
    
    driver.hide_keyboard()
    time.sleep(0.5)


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
    time.sleep(4)
    driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
    time.sleep(2)
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    time.sleep(4)

    # Navigate to register screen
    try:
        driver.find(AppiumBy.ACCESSIBILITY_ID, JOIN_COMMUNITY_BTN, timeout=5).click()
        time.sleep(3)
        print("  ✓ On register screen")
    except Exception as e:
        print(f"  Navigation warning: {e}")

    yield driver

    try:
        driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
        time.sleep(1)
    except Exception:
        pass
    finally:
        driver.stop()


def test_TC_MOB_REG_001_register_valid_data(register_driver):
    """
    TC-MOB-REG-001 | Smoke | Register with valid data → verify email screen
    """
    payload = RegisterAndroidTestData.valid_payload()
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=payload["email"],
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    )
    register_driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN).click()
    time.sleep(5)

    assert register_driver.is_element_present(
        AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=10
    ), "Verify email screen not shown after register"
    print(f"\n✓ Register success — verify email screen shown")
    print(f"  Email: {payload['email']}")


def test_TC_MOB_REG_002_apply_button_disabled_empty_form(register_driver):
    """
    TC-MOB-REG-002 | Boundary | Apply button disabled when form empty
    """
    from skills.mobile.mobile_assertion import MobileAssertion
    ma = MobileAssertion(register_driver)
    ma.element_disabled_by_accessibility(APPLY_NOW_BTN, "Apply now button")
    print("\n✓ Apply button disabled with empty form")


def test_TC_MOB_REG_003_apply_button_disabled_partial_form(register_driver):
    """
    TC-MOB-REG-003 | Boundary | Apply button disabled with partial data
    """
    from skills.mobile.mobile_assertion import MobileAssertion
    payload = RegisterAndroidTestData.valid_payload()

    # Fill only name and email — missing phone and linkedin
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=payload["email"],
    )
    ma = MobileAssertion(register_driver)
    ma.element_disabled_by_accessibility(APPLY_NOW_BTN, "Apply now button")
    print("\n✓ Apply button disabled with partial form")


def test_TC_MOB_REG_004_register_invalid_email(register_driver):
    """
    TC-MOB-REG-004 | Negative | Invalid email format blocked
    """
    payload = RegisterAndroidTestData.valid_payload()
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=RegisterAndroidTestData.INVALID_EMAIL,
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    )
    # Apply button should be disabled or error shown
    el = register_driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN)
    if el.is_enabled():
        register_driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN).click()
        time.sleep(3)
        # Should show error or stay on register screen
        assert not register_driver.is_element_present(
            AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=3
        ), "Should not proceed with invalid email"
    print("\n✓ Invalid email handled correctly")


def test_TC_MOB_REG_005_duplicate_email_shows_error(register_driver):
    """
    TC-MOB-REG-005 | Negative | Duplicate email shows error
    """
    from features.login.test_data.login_test_data import LoginTestData

    payload = RegisterAndroidTestData.valid_payload()
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=LoginTestData.VALID_EMAIL,  # Already registered
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    )
    register_driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN).click()
    time.sleep(5)

    # Should NOT show verify email screen
    source = register_driver.driver.page_source
    assert VERIFY_EMAIL_SCREEN not in source or \
           any(w in source.lower() for w in ["error", "already", "exist", "duplicate"]), \
        "Duplicate email should show error"
    print("\n✓ Duplicate email handled")

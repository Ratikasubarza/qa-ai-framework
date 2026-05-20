"""
Android Register Tests — Hono Flutter App
POST /v1/users/register equivalent on mobile.
"""
import pytest
import time
from appium.webdriver.common.appiumby import AppiumBy


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
from features.register.test_data.register_android_test_data import RegisterAndroidTestData
from features.register.locators.mobile.register_android_locators import (
    JOIN_COMMUNITY_BTN, APPLY_NOW_BTN,
    VERIFY_EMAIL_SCREEN, OPEN_EMAIL_BTN,
    FULLNAME_INDEX, EMAIL_INDEX, PHONE_INDEX, LINKEDIN_INDEX,
)
from config.test_config import TestConfig, APIEndpoints


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
    _wait_for_text(driver, "Login", timeout=15)
    driver.driver.terminate_app(TestConfig.ANDROID_PACKAGE)
    time.sleep(1)  # OS process teardown — inherently timing-based
    driver.driver.activate_app(TestConfig.ANDROID_PACKAGE)
    _wait_for_text(driver, "Login", timeout=12)

    # Navigate to register screen
    try:
        driver.find(AppiumBy.ACCESSIBILITY_ID, JOIN_COMMUNITY_BTN, timeout=5).click()
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
    import httpx, os
    # Pre-check email quota
    import asyncio
    async def check_quota():
        async with httpx.AsyncClient(
            base_url=os.getenv("HONO_API_URL"),
            headers={"x-api-key": os.getenv("HONO_API_KEY")},
            timeout=10
        ) as c:
            r = await c.post(APIEndpoints.REGISTER, json={
                "fullname": "quota check",
                "email": f"quotacheck+{int(__import__('time').time())}@mailinator.com",
                "phone_number": "811111111",
                "phone_country_code": "ID",
                "linkedin": "https://linkedin.com/in/quotacheck"
            })
            return r.status_code, r.json().get("message", "")
    status, msg = asyncio.get_event_loop().run_until_complete(check_quota())
    if status == 500 and "email sending quota" in msg:
        import pytest
        pytest.skip(f"Resend daily email quota reached — run tomorrow")

    payload = RegisterAndroidTestData.valid_payload()
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=payload["email"],
        phone=payload["phone"],
        linkedin=payload["linkedin"],
    )
    register_driver.find(AppiumBy.ACCESSIBILITY_ID, APPLY_NOW_BTN).click()
    _wait_for_text(register_driver, VERIFY_EMAIL_SCREEN, timeout=12)

    assert register_driver.is_element_present(
        AppiumBy.ACCESSIBILITY_ID, VERIFY_EMAIL_SCREEN, timeout=10
    ), "Verify email screen not shown after register"
    print(f"\n✓ Register success — verify email screen shown")
    print(f"  Email: {payload['email']}")


def test_TC_MOB_REG_002_apply_button_disabled_empty_form(register_driver):
    """
    TC-MOB-REG-002 | Boundary | Apply button disabled when form empty
    """
    from skills.assertions.mobile_assertions import MobileAssertions
    MobileAssertions(register_driver).element_disabled_by_accessibility(APPLY_NOW_BTN, "Apply now button")
    print("\n✓ Apply button disabled with empty form")


def test_TC_MOB_REG_003_apply_button_disabled_partial_form(register_driver):
    """
    TC-MOB-REG-003 | Boundary | Apply button disabled with partial data
    """
    from skills.assertions.mobile_assertions import MobileAssertions
    payload = RegisterAndroidTestData.valid_payload()

    # Fill only name and email — missing phone and linkedin
    fill_register_form(
        register_driver,
        fullname=payload["fullname"],
        email=payload["email"],
    )
    MobileAssertions(register_driver).element_disabled_by_accessibility(APPLY_NOW_BTN, "Apply now button")
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
        _wait_for_text(register_driver, "error", timeout=5) or time.sleep(2)
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
    _wait_for_text(register_driver, VERIFY_EMAIL_SCREEN, timeout=8) or time.sleep(3)

    # Should NOT show verify email screen
    source = register_driver.driver.page_source
    assert VERIFY_EMAIL_SCREEN not in source or \
           any(w in source.lower() for w in ["error", "already", "exist", "duplicate"]), \
        "Duplicate email should show error"
    print("\n✓ Duplicate email handled")

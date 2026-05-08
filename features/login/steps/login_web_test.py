"""
Login Web Tests — with Self-Healing Locator integration.
If a locator breaks, SelfHealer automatically tries to find a working alternative.
Target: app-dev.thehono.com/login
"""
import os
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page

from skills.base.element_interaction import ElementInteraction
from skills.base.wait_strategy import WaitStrategy
from skills.base.assertion_helper import AssertionHelper
from core.self_healer import self_healer
from features.login.locators.login_locators import (
    EMAIL_FIELD, PASSWORD_FIELD, LOGIN_BUTTON,
    ELEMENT_DESCRIPTIONS, LOCATOR_REGISTRY,
)

load_dotenv(dotenv_path=".env")

EMAIL    = os.getenv("STAGING_EMAIL",    "testingHonoA@mailinator.com")
PASSWORD = os.getenv("STAGING_PASSWORD", "")
BASE_URL = "https://app-dev.thehono.com"
LOCATORS_FILE = "features/login/locators/login_locators.py"


def safe_interact(page: Page, locator: str, element_name: str, action: str, value: str = ""):
    """
    Wrapper that auto-heals broken locators.
    If element not found, triggers self-healing pipeline.
    """
    ei   = ElementInteraction(page)
    ws   = WaitStrategy(page)

    try:
        ws.for_element(locator, timeout=8000)
    except AssertionError:
        # Locator broken — trigger self-healing
        result = self_healer.heal(
            page=page,
            feature="login",
            element=element_name,
            broken_locator=locator,
            locators_file=LOCATORS_FILE,
        )
        if result.healed:
            # Use healed locator
            locator = result.applied
            ws.for_element(locator, timeout=5000)
        else:
            pytest.fail(
                f"Self-healing failed for '{element_name}'. "
                f"Tried {len(result.candidates)} candidates. "
                f"Manual fix required."
            )

    if action == "fill":
        ei.fill(locator, value, element_name)
    elif action == "click":
        ei.click(locator, element_name)





# ── Tests ─────────────────────────────────────────────────────────────

def _go_to_login(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_selector(EMAIL_FIELD, timeout=15000)


def test_TC_WEB_001_login_button_disabled_when_empty(page: Page):
    """
    TC-WEB-001 | Boundary | Login button disabled when fields empty
    Given: Login page loaded
    When: No input provided
    Then: Login button is disabled
    """
    _go_to_login(page)
    # Snapshot locators before test
    self_healer._create_snapshot("login", LOCATORS_FILE)

    assertion = AssertionHelper(page)
    assertion.element_disabled(LOGIN_BUTTON, "Login button")


def test_TC_WEB_002_login_button_disabled_email_only(page: Page):
    """
    TC-WEB-002 | Boundary | Login button disabled with email only
    Given: Login page loaded
    When: Only email filled, password empty
    Then: Login button remains disabled
    """
    _go_to_login(page)
    safe_interact(page, EMAIL_FIELD, "EMAIL_FIELD", "fill", EMAIL)
    AssertionHelper(page).element_disabled(LOGIN_BUTTON, "Login button")


def test_TC_WEB_003_login_button_enabled_both_fields(page: Page):
    """
    TC-WEB-003 | Smoke | Login button enabled when both fields filled
    Given: Login page loaded
    When: Email and password filled
    Then: Login button is enabled
    """
    _go_to_login(page)
    safe_interact(page, EMAIL_FIELD,    "EMAIL_FIELD",    "fill", EMAIL)
    safe_interact(page, PASSWORD_FIELD, "PASSWORD_FIELD", "fill", PASSWORD)
    AssertionHelper(page).element_enabled(LOGIN_BUTTON, "Login button")


def test_TC_WEB_004_sql_injection_blocked(page: Page):
    """
    TC-WEB-004 | Security | SQL injection blocked by frontend validation
    Given: Login page loaded
    When: SQL injection string entered as email
    Then: Login button stays disabled (invalid email format)
    """
    _go_to_login(page)
    malicious = "'; DROP TABLE users;--"
    safe_interact(page, EMAIL_FIELD,    "EMAIL_FIELD",    "fill", malicious)
    safe_interact(page, PASSWORD_FIELD, "PASSWORD_FIELD", "fill", "AnyPass123!")
    AssertionHelper(page).element_disabled(LOGIN_BUTTON, "Login button")


def test_TC_WEB_005_self_healing_demo(page: Page):
    """
    TC-WEB-005 | Self-Healing Demo | Simulate broken locator + auto-heal
    Given: Login page loaded
    When: A deliberately wrong locator is used
    Then: Self-healer finds correct locator automatically
    """
    _go_to_login(page)
    broken_locator = 'input[name="email"]'  # wrong — app uses type not name

    result = self_healer.heal(
        page=page,
        feature="login",
        element="EMAIL_FIELD",
        broken_locator=broken_locator,
        locators_file=LOCATORS_FILE,
    )

    assert result.healed, (
        f"Self-healing failed. Candidates tried: {len(result.candidates)}\n"
        f"Candidates: {[c.get('locator') for c in result.candidates]}"
    )
    print(f"\n✓ Self-healed to: {result.applied}")
    print(f"  Candidates tried: {len(result.candidates)}")

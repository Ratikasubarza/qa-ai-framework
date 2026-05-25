"""
Feature-level fixtures for User Settings API tests.

Fixture chain:
    registered_user → auth_token → authenticated_client  (from shared_fixtures plugin)
    restore_settings_after_module  — autouse, module-scoped, captures and restores all
                                     settings state around the module to prevent staging
                                     DB pollution across runs (per NOTE 3 requirement).
"""
import pytest
import structlog

from config.test_config import APIEndpoints

logger = structlog.get_logger(__name__)


# ── restore_settings_after_module ─────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
async def restore_settings_after_module(authenticated_client):
    """
    CRITICAL: Captures all toggle and option settings before the module runs,
    then restores every value in teardown. Prevents persistent staging DB state
    from leaking between test runs and CI reruns.
    autouse=True — applied automatically to every test in this module.
    """
    # ── Capture current state ─────────────────────────────────────────────────
    toggle_personal_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "PERSONAL"}
    )
    toggle_notification_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "NOTIFICATION"}
    )
    option_audience_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "AUDIENCE"}
    )
    option_message_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "MESSAGE"}
    )

    original_toggles_personal = toggle_personal_resp.json().get("data", [])
    original_toggles_notification = toggle_notification_resp.json().get("data", [])
    original_audience = option_audience_resp.json().get("data", {})
    original_message = option_message_resp.json().get("data", {})

    logger.info(
        "settings_captured",
        personal_keys=[t.get("key") for t in original_toggles_personal],
        notification_keys=[t.get("key") for t in original_toggles_notification],
    )

    yield

    # ── Restore original state ────────────────────────────────────────────────
    for toggle in original_toggles_personal:
        try:
            await authenticated_client.put(
                APIEndpoints.SETTINGS_TOGGLE,
                json={"section": "PERSONAL", "key": toggle["key"], "value": toggle["value"]},
            )
        except Exception:
            pass

    for toggle in original_toggles_notification:
        try:
            await authenticated_client.put(
                APIEndpoints.SETTINGS_TOGGLE,
                json={"section": "NOTIFICATION", "key": toggle["key"], "value": toggle["value"]},
            )
        except Exception:
            pass

    if original_audience.get("key"):
        try:
            await authenticated_client.put(
                APIEndpoints.SETTINGS_OPTION,
                json={
                    "section": "AUDIENCE",
                    "key": original_audience["key"],
                    "value": original_audience["value"],
                },
            )
        except Exception:
            pass

    if original_message.get("key"):
        try:
            await authenticated_client.put(
                APIEndpoints.SETTINGS_OPTION,
                json={
                    "section": "MESSAGE",
                    "key": original_message["key"],
                    "value": original_message["value"],
                },
            )
        except Exception:
            pass

    logger.info("settings_restored")

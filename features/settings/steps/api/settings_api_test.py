"""Settings API Tests — toggle and option preferences."""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints

pytestmark = [allure.feature("Settings"), allure.suite("API")]


# ── GET /v1/settings/toggle ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_001_get_toggle_settings_notification(settings_token):
    """TC-SETS-001 | Smoke | Get NOTIFICATION toggle settings returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_TOGGLE,
            params={"section": "NOTIFICATION"},
            auth_token=settings_token,
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert isinstance(body.get("data"), list)


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_002_get_toggle_settings_personal(settings_token):
    """TC-SETS-002 | Functional | Get PERSONAL toggle settings returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_TOGGLE,
            params={"section": "PERSONAL"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_003_get_toggle_settings_no_token():
    """TC-SETS-003 | Security | Toggle settings without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_TOGGLE,
            params={"section": "NOTIFICATION"},
        )
    SchemaValidator(response).status(401)


# ── PUT /v1/settings/toggle ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_004_update_toggle_setting_valid(settings_token):
    """TC-SETS-004 | Smoke | Update toggle setting returns 200"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_TOGGLE,
            json={"section": "NOTIFICATION", "key": "repost", "value": True},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_005_update_toggle_invalid_key(settings_token):
    """TC-SETS-005 | Negative | Update toggle with invalid key returns 400"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_TOGGLE,
            json={"section": "NOTIFICATION", "key": "invalid_key", "value": True},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_006_update_toggle_no_token():
    """TC-SETS-006 | Security | Update toggle without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_TOGGLE,
            json={"key": "repost", "value": True},
        )
    SchemaValidator(response).status(401)


# ── GET /v1/settings/option ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_007_get_option_settings_message(settings_token):
    """TC-SETS-007 | Smoke | Get MESSAGE option setting returns 200 with key/value"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_OPTION,
            params={"section": "MESSAGE"},
            auth_token=settings_token,
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert body.get("code") == "OK"
    assert isinstance(data, dict)
    assert data.get("key") == "message_preference"
    assert data.get("value") in {"NO_ONE", "VERIFIED_USER", "EVERYONE"}


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_008_get_option_settings_audience(settings_token):
    """TC-SETS-008 | Functional | Get AUDIENCE option setting returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_OPTION,
            params={"section": "AUDIENCE"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status(200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_009_get_option_settings_no_token():
    """TC-SETS-009 | Security | Get option settings without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_OPTION,
            params={"section": "MESSAGE"},
        )
    SchemaValidator(response).status(401)


# ── PUT /v1/settings/option ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_010_update_option_message_preference(settings_token):
    """TC-SETS-010 | Smoke | Update message_preference to NO_ONE returns 200"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "MESSAGE", "key": "message_preference", "value": "NO_ONE"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_011_update_option_invalid_value(settings_token):
    """TC-SETS-011 | Negative | Update option with invalid value returns 400"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "AUDIENCE", "key": "tagging_preference", "value": "INVALID_VALUE"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_012_update_option_no_token():
    """TC-SETS-012 | Security | Update option without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "MESSAGE", "key": "message_preference", "value": "EVERYONE"},
        )
    SchemaValidator(response).status(401)


# ── Additional section-based regressions ──────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_013_get_message_preference(settings_token):
    """TC-SETS-013 | Smoke | Get MESSAGE option preference returns 200 with enum value"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_OPTION,
            params={"section": "MESSAGE"},
            auth_token=settings_token,
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert data.get("key") == "message_preference"
    assert data.get("value") in {"NO_ONE", "VERIFIED_USER", "EVERYONE"}


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_014_get_message_preference_no_token():
    """TC-SETS-014 | Security | Get MESSAGE option preference without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_OPTION,
            params={"section": "MESSAGE"},
        )
    SchemaValidator(response).status(401)


# ── PUT /v1/settings/option (MESSAGE) ─────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_015_update_message_preference(settings_token):
    """TC-SETS-015 | Smoke | Update message_preference to NO_ONE returns 200"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "MESSAGE", "key": "message_preference", "value": "NO_ONE"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_016_update_message_preference_invalid(settings_token):
    """TC-SETS-016 | Negative | Invalid message_preference value returns 400"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "MESSAGE", "key": "message_preference", "value": "INVALID_VALUE"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(400, 422)


# ── GET /v1/settings/toggle (NOTIFICATION) ────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_017_get_notification_preferences(settings_token):
    """TC-SETS-017 | Smoke | Get NOTIFICATION toggle preferences returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_TOGGLE,
            params={"section": "NOTIFICATION"},
            auth_token=settings_token,
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", [])
    assert isinstance(data, list)
    keys = {item.get("key") for item in data if isinstance(item, dict)}
    assert "mention_replies" in keys


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_018_get_notif_preferences_no_token():
    """TC-SETS-018 | Security | Get NOTIFICATION toggle preferences without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.SETTINGS_TOGGLE,
            params={"section": "NOTIFICATION"},
        )
    SchemaValidator(response).status(401)


# ── PUT /v1/settings/toggle and /v1/settings/option ──────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_019_update_notification_preferences(settings_token):
    """TC-SETS-019 | Smoke | Update NOTIFICATION toggle preference returns 200"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_TOGGLE,
            json={"section": "NOTIFICATION", "key": "mention_replies", "value": False},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(200, 201)


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_SETS_020_update_audience_option_preference(settings_token):
    """TC-SETS-020 | Smoke | Update AUDIENCE option preference returns 200"""
    async with HonoAPIClient() as client:
        response = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "AUDIENCE", "key": "tagging_preference", "value": "FOLLOWERS_ONLY"},
            auth_token=settings_token,
        )
    SchemaValidator(response).status_in(200, 201)

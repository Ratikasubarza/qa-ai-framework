"""User Settings API Tests — toggle and option preferences."""
import pytest
import allure

from config.test_config import APIEndpoints
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [
    allure.feature("User Settings"),
    allure.suite("API"),
]


# ── GET /v1/settings/toggle ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_001_get_toggle_settings_personal(authenticated_client):
    """TC-ST-001 | Smoke | GET PERSONAL toggle settings returns 200 with show_email and show_phone keys"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "PERSONAL"}
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .attach_to_report("toggle_personal"))

    data = resp.json()["data"]
    assert isinstance(data, list), "PERSONAL toggle data should be a list"
    keys = [item["key"] for item in data]
    assert "show_email" in keys, "Missing key: show_email"
    assert "show_phone" in keys, "Missing key: show_phone"
    for item in data:
        assert "key" in item and "label" in item and "value" in item
        assert isinstance(item["value"], bool), (
            f"Toggle value must be bool, got {type(item['value'])}"
        )


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_002_get_toggle_settings_notification(authenticated_client):
    """TC-ST-002 | Smoke | GET NOTIFICATION toggle settings returns 200 with all 7 required keys"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "NOTIFICATION"}
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .attach_to_report("toggle_notification"))

    data = resp.json()["data"]
    keys = {item["key"] for item in data}
    required = {
        "mention_replies", "repost", "reaction", "tag",
        "new_followers", "direct_message", "message_reaction",
    }
    missing = required - keys
    assert not missing, f"NOTIFICATION section missing keys: {missing}"


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_003_get_toggle_settings_invalid_section(authenticated_client):
    """TC-ST-003 | Negative | GET toggle with invalid section returns 422"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "INVALID_SECTION"}
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_004_get_toggle_settings_missing_section(authenticated_client):
    """TC-ST-004 | Negative | GET toggle with missing section param returns 422"""
    resp = await authenticated_client.get(APIEndpoints.SETTINGS_TOGGLE)
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_005_get_toggle_settings_no_auth():
    """TC-ST-005 | Security | GET toggle without auth token returns 401"""
    async with HonoAPIClient() as client:
        resp = await client.get(
            APIEndpoints.SETTINGS_TOGGLE, params={"section": "NOTIFICATION"}
        )
    SchemaValidator(resp).status(401)


# ── PUT /v1/settings/toggle ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_006_update_toggle_show_email(authenticated_client):
    """TC-ST-006 | Smoke | PUT show_email=False returns 200 — restore_settings_after_module handles teardown"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "PERSONAL", "key": "show_email", "value": False},
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .body_contains_error("Data saved")
        .attach_to_report("toggle_update_show_email"))


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_007_update_toggle_notification_mention_replies(authenticated_client):
    """TC-ST-007 | Smoke | PUT mention_replies=False returns 200"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "NOTIFICATION", "key": "mention_replies", "value": False},
    )
    SchemaValidator(resp).status(200).code_equals("OK")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_008_update_toggle_verify_persists(authenticated_client):
    """TC-ST-008 | Boundary | PUT show_phone=False then GET — verify value is persisted"""
    await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "PERSONAL", "key": "show_phone", "value": False},
    )
    get_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_TOGGLE, params={"section": "PERSONAL"}
    )
    data = get_resp.json()["data"]
    show_phone = next((i for i in data if i["key"] == "show_phone"), None)
    assert show_phone is not None, "show_phone key not found in PERSONAL toggle response"
    assert show_phone["value"] is False, (
        f"Expected show_phone=False after PUT, got {show_phone['value']}"
    )


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_009_update_toggle_invalid_key(authenticated_client):
    """TC-ST-009 | Negative | PUT toggle with invalid key returns 400 or 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "NOTIFICATION", "key": "invalid_key_xyz", "value": True},
    )
    (SchemaValidator(resp)
        .status_in(400, 422)
        .attach_to_report("toggle_invalid_key"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_010_update_toggle_non_bool_value(authenticated_client):
    """TC-ST-010 | Negative | PUT toggle with string value instead of bool returns 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "NOTIFICATION", "key": "repost", "value": "true"},
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_011_update_toggle_missing_key_field(authenticated_client):
    """TC-ST-011 | Negative | PUT toggle with missing key field returns 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_TOGGLE,
        json={"section": "NOTIFICATION", "value": True},
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_012_update_toggle_no_auth():
    """TC-ST-012 | Security | PUT toggle without auth token returns 401"""
    async with HonoAPIClient() as client:
        resp = await client.put(
            APIEndpoints.SETTINGS_TOGGLE,
            json={"section": "PERSONAL", "key": "show_email", "value": False},
        )
    SchemaValidator(resp).status(401)


# ── GET /v1/settings/option ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_013_get_option_settings_audience(authenticated_client):
    """TC-ST-013 | Smoke | GET AUDIENCE option returns 200 with tagging_preference and valid enum value"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "AUDIENCE"}
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .attach_to_report("option_audience"))

    data = resp.json()["data"]
    assert data["key"] == "tagging_preference"
    assert data["value"] in ("NO_ONE", "FOLLOWERS_ONLY", "EVERYONE")
    if "options" in data:
        option_values = {o["value"] for o in data["options"]}
        assert option_values == {"NO_ONE", "FOLLOWERS_ONLY", "EVERYONE"}
        for opt in data["options"]:
            assert "value" in opt and "label" in opt


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_014_get_option_settings_message(authenticated_client):
    """TC-ST-014 | Smoke | GET MESSAGE option returns 200 with message_preference and valid enum value"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "MESSAGE"}
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .attach_to_report("option_message"))

    data = resp.json()["data"]
    assert data["key"] == "message_preference"
    assert data["value"] in ("NO_ONE", "VERIFIED_USER", "EVERYONE")
    if "options" in data:
        option_values = {o["value"] for o in data["options"]}
        assert option_values == {"NO_ONE", "VERIFIED_USER", "EVERYONE"}


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_015_get_option_settings_options_schema(authenticated_client):
    """TC-ST-015 | Smoke | Every option item in MESSAGE section has 'value' and 'label' string fields"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "MESSAGE"}
    )
    SchemaValidator(resp).status(200)
    data = resp.json()["data"]
    if "options" in data:
        for opt in data["options"]:
            assert "value" in opt, f"Option missing 'value': {opt}"
            assert "label" in opt, f"Option missing 'label': {opt}"
            assert isinstance(opt["value"], str)
            assert isinstance(opt["label"], str)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_016_get_option_settings_invalid_section(authenticated_client):
    """TC-ST-016 | Negative | GET option with invalid section returns 422"""
    resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "INVALID"}
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_017_get_option_settings_no_auth():
    """TC-ST-017 | Security | GET option without auth token returns 401"""
    async with HonoAPIClient() as client:
        resp = await client.get(
            APIEndpoints.SETTINGS_OPTION, params={"section": "MESSAGE"}
        )
    SchemaValidator(resp).status(401)


# ── PUT /v1/settings/option ───────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_018_update_option_message_preference_no_one(authenticated_client):
    """TC-ST-018 | Smoke | PUT message_preference=NO_ONE returns 200 — restore_settings_after_module handles teardown"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"section": "MESSAGE", "key": "message_preference", "value": "NO_ONE"},
    )
    (SchemaValidator(resp)
        .status(200)
        .code_equals("OK")
        .body_contains_error("Data saved")
        .attach_to_report("option_update_message_no_one"))


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_019_update_option_tagging_preference_followers_only(authenticated_client):
    """TC-ST-019 | Smoke | PUT tagging_preference=FOLLOWERS_ONLY returns 200"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"section": "AUDIENCE", "key": "tagging_preference", "value": "FOLLOWERS_ONLY"},
    )
    SchemaValidator(resp).status(200).code_equals("OK")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_020_update_option_verify_persists(authenticated_client):
    """TC-ST-020 | Boundary | PUT message_preference=VERIFIED_USER then GET — verify value is persisted"""
    await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"section": "MESSAGE", "key": "message_preference", "value": "VERIFIED_USER"},
    )
    get_resp = await authenticated_client.get(
        APIEndpoints.SETTINGS_OPTION, params={"section": "MESSAGE"}
    )
    assert get_resp.json()["data"]["value"] == "VERIFIED_USER", (
        "Option setting not persisted after PUT"
    )


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_021_update_option_invalid_enum_value(authenticated_client):
    """TC-ST-021 | Negative | PUT tagging_preference with invalid enum value returns 400 or 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"section": "AUDIENCE", "key": "tagging_preference", "value": "INVALID_VALUE"},
    )
    (SchemaValidator(resp)
        .status_in(400, 422)
        .attach_to_report("option_invalid_value"))
    if resp.status_code == 400:
        message = resp.json().get("message", "")
        assert any(v in message for v in ("NO_ONE", "FOLLOWERS_ONLY", "EVERYONE")), (
            f"400 error message should list valid options, got: {message}"
        )


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_022_update_option_invalid_key(authenticated_client):
    """TC-ST-022 | Negative | PUT option with invalid key returns 400 or 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"section": "MESSAGE", "key": "invalid_key_xyz", "value": "NO_ONE"},
    )
    SchemaValidator(resp).status_in(400, 422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_023_update_option_missing_required_fields(authenticated_client):
    """TC-ST-023 | Negative | PUT option with missing section and value fields returns 422"""
    resp = await authenticated_client.put(
        APIEndpoints.SETTINGS_OPTION,
        json={"key": "message_preference"},
    )
    SchemaValidator(resp).status(422)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_ST_024_update_option_no_auth():
    """TC-ST-024 | Security | PUT option without auth token returns 401"""
    async with HonoAPIClient() as client:
        resp = await client.put(
            APIEndpoints.SETTINGS_OPTION,
            json={"section": "MESSAGE", "key": "message_preference", "value": "NO_ONE"},
        )
    SchemaValidator(resp).status(401)

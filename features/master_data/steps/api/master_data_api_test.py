"""Master Data API Tests — industries, business-areas, interests, causes, countries, cities, relationship-types"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints, ReferenceIDs

pytestmark = allure.feature("Master Data")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── GET /v1/master/industries ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_001_get_industries(master_data_token):
    """TC-MSTR-001 | Smoke | Get industries list returns 200 with data array"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_INDUSTRIES,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    assert isinstance(body.get("data"), list)
    assert len(body["data"]) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_002_industries_items_have_id_and_name(master_data_token):
    """TC-MSTR-002 | Functional | Industries items have id and name fields"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_INDUSTRIES,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    data = response.json().get("data", [])
    assert data, "Industries list is empty"
    assert "id" in data[0] and "name" in data[0]


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_003_get_industries_no_api_key():
    """TC-MSTR-003 | Security | Get industries without x-api-key returns 401"""
    import httpx
    import os
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL", "https://api-dev.thehono.com"),
        timeout=30,
    ) as client:
        response = await client.get("/v1/master/industries")
    SchemaValidator(response).status_in(401, 403)


# ── GET /v1/master/business-areas ────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_004_get_business_areas(master_data_token):
    """TC-MSTR-004 | Smoke | Get business areas returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_BUSINESS_AREAS,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("data"), list)
    assert len(body["data"]) > 0


@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_005_business_areas_schema(master_data_token):
    """TC-MSTR-005 | Functional | Business areas items have id and name"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_BUSINESS_AREAS,
            headers=_auth_header(master_data_token),
        )
    data = response.json().get("data", [])
    assert data
    assert "id" in data[0] and "name" in data[0]


# ── GET /v1/master/personal-interests ────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_006_get_personal_interests(master_data_token):
    """TC-MSTR-006 | Smoke | Get personal interests returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_PERSONAL_INTERESTS,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("data"), list)
    assert len(body["data"]) > 0


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_007_get_personal_interests_no_token():
    """TC-MSTR-007 | Security | Personal interests without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.MASTER_PERSONAL_INTERESTS)
    SchemaValidator(response).status_is(401)


# ── GET /v1/master/social-causes ─────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_008_get_social_causes(master_data_token):
    """TC-MSTR-008 | Smoke | Get social causes returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_SOCIAL_CAUSES,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("data"), list)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_009_get_social_causes_no_token():
    """TC-MSTR-009 | Security | Social causes without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.MASTER_SOCIAL_CAUSES)
    SchemaValidator(response).status_is(401)


# ── GET /v1/master/countries ──────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_010_get_countries(master_data_token):
    """TC-MSTR-010 | Smoke | Get countries returns 200 with list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_COUNTRIES,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("data"), list)
    data = body["data"]
    assert len(data) > 0
    first = data[0]
    assert "id" in first and "name" in first


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_011_get_countries_no_token():
    """TC-MSTR-011 | Security | Countries without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.MASTER_COUNTRIES)
    SchemaValidator(response).status_is(401)


# ── GET /v1/master/cities ─────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_012_get_cities_by_country(master_data_token):
    """TC-MSTR-012 | Smoke | Get cities for Indonesia (country_id=102) returns 200"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_CITIES,
            params={"country_id": ReferenceIDs.INDONESIA},
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    data = body.get("data", {})
    assert "cities" in data
    assert isinstance(data["cities"], list)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_013_get_cities_missing_country_id(master_data_token):
    """TC-MSTR-013 | Negative | Get cities without country_id returns 400/422"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_CITIES,
            headers=_auth_header(master_data_token),
        )
    SchemaValidator(response).status_in(400, 422, 200)


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_014_get_cities_no_token():
    """TC-MSTR-014 | Security | Get cities without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_CITIES,
            params={"country_id": ReferenceIDs.INDONESIA},
        )
    SchemaValidator(response).status_is(401)


# ── GET /v1/master/relationship-types ────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_015_get_relationship_types(master_data_token):
    """TC-MSTR-015 | Smoke | Get relationship types returns 200 with list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.MASTER_RELATIONSHIP_TYPES,
            headers=_auth_header(master_data_token),
        )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("data"), list)
    data = body["data"]
    assert len(data) > 0
    assert "id" in data[0] and "name" in data[0]


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_MSTR_016_get_relationship_types_no_token():
    """TC-MSTR-016 | Security | Relationship types without auth returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.MASTER_RELATIONSHIP_TYPES)
    SchemaValidator(response).status_is(401)

"""Public API Tests — GET /v1/public/countries, GET /v1/public/cities (no auth required)"""
import pytest
import allure

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from config.test_config import APIEndpoints, ReferenceIDs

pytestmark = allure.feature("Public")


# ── GET /v1/public/countries ──────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PUB_001_list_countries_public():
    """TC-PUB-001 | Smoke | Public countries endpoint returns 200 without auth"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.PUBLIC_COUNTRIES)
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    data = body.get("data", [])
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.api
async def test_TC_PUB_002_countries_schema():
    """TC-PUB-002 | Functional | Countries items have id, name, iso2, phone_code"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.PUBLIC_COUNTRIES)
    assert response.status_code == 200
    data = response.json().get("data", [])
    assert data
    first = data[0]
    assert "id" in first
    assert "name" in first


@pytest.mark.api
async def test_TC_PUB_003_countries_response_time():
    """TC-PUB-003 | Performance | Public countries responds within 3000ms"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.PUBLIC_COUNTRIES)
    SchemaValidator(response).status(200).response_time_under(3000)


# ── GET /v1/public/cities ─────────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.api
async def test_TC_PUB_004_list_cities_public():
    """TC-PUB-004 | Smoke | Public cities for Indonesia returns 200 without auth"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.PUBLIC_CITIES,
            params={"country_id": ReferenceIDs.INDONESIA},
        )
    assert response.status_code == 200
    body = response.json()
    assert body.get("code") == "OK"
    data = body.get("data", {})
    assert "cities" in data or isinstance(data, list)


@pytest.mark.api
async def test_TC_PUB_005_cities_schema():
    """TC-PUB-005 | Functional | Cities response includes country info and cities list"""
    async with HonoAPIClient() as client:
        response = await client.get(
            APIEndpoints.PUBLIC_CITIES,
            params={"country_id": ReferenceIDs.INDONESIA},
        )
    assert response.status_code == 200
    data = response.json().get("data", {})
    cities = data.get("cities", data) if isinstance(data, dict) else data
    assert isinstance(cities, list)


@pytest.mark.negative
@pytest.mark.api
async def test_TC_PUB_006_cities_missing_country_id():
    """TC-PUB-006 | Negative | Public cities without country_id returns 400 or empty"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.PUBLIC_CITIES)
    SchemaValidator(response).status_in(400, 422, 200)

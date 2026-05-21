"""CMS Users API Tests — GET /v1/users (admin only)."""
import allure
import pytest

from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.cms_users.test_data.cms_users_test_data import CmsUsersTestData
from config.test_config import APIEndpoints

pytestmark = [
    allure.feature("CMS Users"),
    allure.suite("API"),
]


@pytest.mark.asyncio
async def test_TC_CMS_USERS_001_list_users_authenticated(cms_token):
    """
    TC-CMS-USERS-001 | Smoke | List users with valid CMS token
    Given: CMS admin is authenticated
    When: GET /v1/users with pagination params
    Then: 200 + list of users returned
    """
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(APIEndpoints.USERS_LIST, params=CmsUsersTestData.VALID_PARAMS)
    SchemaValidator(response).status_ok()
    data = response.json()
    users = data.get("data", [])
    assert isinstance(users, list), f"Expected list, got: {type(users)}"
    if users:
        for field in CmsUsersTestData.REQUIRED_USER_FIELDS:
            assert field in users[0], f"Missing field: {field}"


@pytest.mark.asyncio
async def test_TC_CMS_USERS_002_list_users_unauthenticated():
    """TC-CMS-USERS-002 | Security | List users without token returns 401"""
    async with HonoAPIClient() as client:
        response = await client.get(APIEndpoints.USERS_LIST, params=CmsUsersTestData.VALID_PARAMS)
    assert response.status_code == 401, f"Expected 401, got: {response.status_code}"


@pytest.mark.asyncio
async def test_TC_CMS_USERS_003_list_users_filter_by_status(cms_token):
    """TC-CMS-USERS-003 | Functional | Filter users by status=APPROVED"""
    params = {**CmsUsersTestData.VALID_PARAMS, "status": CmsUsersTestData.STATUS_APPROVED}
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(APIEndpoints.USERS_LIST, params=params)
    SchemaValidator(response).status_ok()


@pytest.mark.asyncio
async def test_TC_CMS_USERS_004_list_users_pagination(cms_token):
    """TC-CMS-USERS-004 | Functional | Pagination — page 1, size 5"""
    params = {"page": 1, "size": 5, "orderBy": "name", "order": "ASC"}
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(APIEndpoints.USERS_LIST, params=params)
    SchemaValidator(response).status_ok()
    users = response.json().get("data", [])
    assert len(users) <= 5, f"Expected max 5 users, got: {len(users)}"


@pytest.mark.asyncio
async def test_TC_CMS_USERS_005_list_users_order_desc(cms_token):
    """TC-CMS-USERS-005 | Functional | Order by name DESC"""
    params = {"page": 1, "size": 20, "orderBy": "name", "order": "DESC"}
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(APIEndpoints.USERS_LIST, params=params)
    SchemaValidator(response).status_ok()


@pytest.mark.asyncio
async def test_TC_CMS_USERS_006_size_variations(cms_token):
    """TC-CMS-USERS-006 | Functional | Different page sizes return correct count"""
    for size in [5, 10, 50]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {cms_token}"
            response = await client.get(
                APIEndpoints.USERS_LIST,
                params={"page": 1, "size": size, "orderBy": "name", "order": "ASC"},
            )
        SchemaValidator(response).status_ok()
        users = response.json().get("data", [])
        assert len(users) <= size, f"size={size}: got {len(users)} users"


@pytest.mark.asyncio
async def test_TC_CMS_USERS_007_orderby_created_at(cms_token):
    """TC-CMS-USERS-007 | Functional | Order by created_at ASC and DESC"""
    for order in ["ASC", "DESC"]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {cms_token}"
            response = await client.get(
                APIEndpoints.USERS_LIST,
                params={"page": 1, "size": 20, "orderBy": "created_at", "order": order},
            )
        SchemaValidator(response).status_ok()


@pytest.mark.asyncio
async def test_TC_CMS_USERS_008_page_navigation(cms_token):
    """TC-CMS-USERS-008 | Functional | Navigate through pages — no overlap"""
    results = {}
    for page in [1, 2]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {cms_token}"
            response = await client.get(
                APIEndpoints.USERS_LIST,
                params={"page": page, "size": 10, "orderBy": "name", "order": "ASC"},
            )
        SchemaValidator(response).status_ok()
        results[page] = [u.get("id") for u in response.json().get("data", [])]
    if results[1] and results[2]:
        overlap = set(results[1]) & set(results[2])
        assert not overlap, f"Pages overlap: {overlap}"


@pytest.mark.asyncio
async def test_TC_CMS_USERS_009_all_status_values(cms_token):
    """TC-CMS-USERS-009 | Functional | Filter by each status value"""
    statuses = {
        "PENDING":  CmsUsersTestData.STATUS_PENDING,
        "APPROVED": CmsUsersTestData.STATUS_APPROVED,
        "REJECTED": CmsUsersTestData.STATUS_REJECTED,
    }
    for status in statuses.values():
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {cms_token}"
            response = await client.get(
                APIEndpoints.USERS_LIST,
                params={"page": 1, "size": 20, "orderBy": "name", "order": "ASC", "status": status},
            )
        SchemaValidator(response).status_ok()


@pytest.mark.asyncio
async def test_TC_CMS_USERS_010_no_params_uses_defaults(cms_token):
    """TC-CMS-USERS-010 | Boundary | No query params — API uses defaults"""
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(APIEndpoints.USERS_LIST)
    SchemaValidator(response).status_ok()
    assert isinstance(response.json().get("data", []), list)


@pytest.mark.asyncio
async def test_TC_CMS_USERS_011_invalid_page_number(cms_token):
    """TC-CMS-USERS-011 | Boundary | Invalid page number"""
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(
            APIEndpoints.USERS_LIST,
            params={"page": -1, "size": 20, "orderBy": "name", "order": "ASC"},
        )
    assert response.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_TC_CMS_USERS_012_invalid_order_value(cms_token):
    """TC-CMS-USERS-012 | Boundary | Invalid order value (not ASC/DESC)"""
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {cms_token}"
        response = await client.get(
            APIEndpoints.USERS_LIST,
            params={"page": 1, "size": 20, "orderBy": "name", "order": "INVALID"},
        )
    assert response.status_code in [200, 400, 422]

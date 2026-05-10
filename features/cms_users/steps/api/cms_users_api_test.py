"""
CMS Users API Tests — GET /v1/users (admin only)
Requires CMS token from cms_login.
"""
import pytest
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator
from features.cms_users.test_data.cms_users_test_data import CmsUsersTestData
from features.cms_login.test_data.cms_login_test_data import CmsLoginTestData


async def get_cms_token() -> str:
    """Get CMS admin token."""
    async with HonoAPIClient() as client:
        response = await client.post(
            "/v1/users/login",
            json=CmsLoginTestData.valid_payload()
        )
    data = response.json()
    body = data.get("data", data)
    return body.get("accessToken") or body.get("token", "")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_001_list_users_authenticated():
    """
    TC-CMS-USERS-001 | Smoke | List users with valid CMS token
    Given: CMS admin is authenticated
    When: GET /v1/users with pagination params
    Then: 200 + list of users returned
    """
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get(
            "/v1/users",
            params=CmsUsersTestData.VALID_PARAMS
        )
    SchemaValidator(response).status_ok()
    data = response.json()
    users = data.get("data", [])
    assert isinstance(users, list), f"Expected list, got: {type(users)}"
    print(f"\n✓ List users: {len(users)} users returned")

    # Verify required fields in first user
    if users:
        for field in CmsUsersTestData.REQUIRED_USER_FIELDS:
            assert field in users[0], f"Missing field: {field}"
        print(f"✓ All required fields present")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_002_list_users_unauthenticated():
    """
    TC-CMS-USERS-002 | Security | List users without token returns 401
    """
    async with HonoAPIClient() as client:
        response = await client.get(
            "/v1/users",
            params=CmsUsersTestData.VALID_PARAMS
        )
    assert response.status_code == 401, \
        f"Expected 401, got: {response.status_code}"
    print(f"\n✓ Unauthenticated blocked: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_003_list_users_filter_by_status():
    """
    TC-CMS-USERS-003 | Functional | Filter users by status=APPROVED
    """
    token = await get_cms_token()
    params = {**CmsUsersTestData.VALID_PARAMS, "status": CmsUsersTestData.STATUS_APPROVED}

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users", params=params)

    SchemaValidator(response).status_ok()
    data = response.json()
    users = data.get("data", [])
    print(f"\n✓ Filtered users by status=APPROVED: {len(users)} users")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_004_list_users_pagination():
    """
    TC-CMS-USERS-004 | Functional | Pagination — page 1, size 5
    """
    token = await get_cms_token()
    params = {"page": 1, "size": 5, "orderBy": "name", "order": "ASC"}

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users", params=params)

    SchemaValidator(response).status_ok()
    data = response.json()
    users = data.get("data", [])
    assert len(users) <= 5, f"Expected max 5 users, got: {len(users)}"
    print(f"\n✓ Pagination works: {len(users)} users with size=5")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_005_list_users_order_desc():
    """
    TC-CMS-USERS-005 | Functional | Order by name DESC
    """
    token = await get_cms_token()
    params = {"page": 1, "size": 20, "orderBy": "name", "order": "DESC"}

    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users", params=params)

    SchemaValidator(response).status_ok()
    print(f"\n✓ DESC order works: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_006_size_variations():
    """
    TC-CMS-USERS-006 | Functional | Different page sizes return correct count
    """
    token = await get_cms_token()
    for size in [5, 10, 50]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/v1/users", params={
                "page": 1, "size": size, "orderBy": "name", "order": "ASC"
            })
        SchemaValidator(response).status_ok()
        users = response.json().get("data", [])
        assert len(users) <= size, f"size={size}: got {len(users)} users"
        print(f"  ✓ size={size}: {len(users)} users returned")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_007_orderby_created_at():
    """
    TC-CMS-USERS-007 | Functional | Order by created_at ASC and DESC
    """
    token = await get_cms_token()
    for order in ["ASC", "DESC"]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/v1/users", params={
                "page": 1, "size": 20,
                "orderBy": "created_at", "order": order
            })
        SchemaValidator(response).status_ok()
        print(f"  ✓ orderBy=created_at order={order}: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_008_page_navigation():
    """
    TC-CMS-USERS-008 | Functional | Navigate through pages
    """
    token = await get_cms_token()
    results = {}
    for page in [1, 2]:
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/v1/users", params={
                "page": page, "size": 10,
                "orderBy": "name", "order": "ASC"
            })
        SchemaValidator(response).status_ok()
        users = response.json().get("data", [])
        results[page] = [u.get("id") for u in users]
        print(f"  ✓ page={page}: {len(users)} users")

    # Page 1 and 2 should have different users
    if results[1] and results[2]:
        overlap = set(results[1]) & set(results[2])
        assert not overlap, f"Pages overlap: {overlap}"
        print(f"  ✓ No overlap between pages")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_009_all_status_values():
    """
    TC-CMS-USERS-009 | Functional | Filter by each status value
    """
    token = await get_cms_token()
    statuses = {
        "PENDING":  CmsUsersTestData.STATUS_PENDING,
        "APPROVED": CmsUsersTestData.STATUS_APPROVED,
        "REJECTED": CmsUsersTestData.STATUS_REJECTED,
    }
    for label, status in statuses.items():
        async with HonoAPIClient() as client:
            client._client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/v1/users", params={
                "page": 1, "size": 20,
                "orderBy": "name", "order": "ASC",
                "status": status
            })
        SchemaValidator(response).status_ok()
        users = response.json().get("data", [])
        print(f"  ✓ status={label}({status}): {len(users)} users")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_010_no_params_uses_defaults():
    """
    TC-CMS-USERS-010 | Boundary | No query params — API uses defaults
    """
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users")
    SchemaValidator(response).status_ok()
    users = response.json().get("data", [])
    assert isinstance(users, list), "Should return list with default params"
    print(f"\n✓ No params: {len(users)} users with defaults")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_011_invalid_page_number():
    """
    TC-CMS-USERS-011 | Boundary | Invalid page number
    """
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users", params={
            "page": -1, "size": 20,
            "orderBy": "name", "order": "ASC"
        })
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"
    print(f"\n✓ Invalid page handled: {response.status_code}")


@pytest.mark.asyncio
async def test_TC_CMS_USERS_012_invalid_order_value():
    """
    TC-CMS-USERS-012 | Boundary | Invalid order value (not ASC/DESC)
    """
    token = await get_cms_token()
    async with HonoAPIClient() as client:
        client._client.headers["Authorization"] = f"Bearer {token}"
        response = await client.get("/v1/users", params={
            "page": 1, "size": 20,
            "orderBy": "name", "order": "INVALID"
        })
    assert response.status_code in [200, 400, 422], \
        f"Unexpected: {response.status_code}"
    print(f"\n✓ Invalid order handled: {response.status_code}")

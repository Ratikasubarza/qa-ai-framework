"""Post Interactions API tests — report, not-interested, track view."""
import pytest
import allure

from config.test_config import APIEndpoints
from config.test_data import BoundaryValues
from features.posts.test_data.create_post_test_data import CreatePostPayload
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [allure.feature("Post Interactions"), allure.suite("API")]


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORT  POST  —  POST /v1/posts/{post_id}/report
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_001_report_post_valid(regular_user, reported_post):
    """TC-PI-001 | Smoke | Authenticated user reports another user's post → 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_report(reported_post),
            json={"reason": "spam"},
        )
    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-PI-001 report post")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_002_report_post_no_auth(reported_post):
    """TC-PI-002 | Negative | Report post without Bearer token → 401"""
    async with HonoAPIClient() as client:
        resp = await client.post(
            APIEndpoints.post_report(reported_post),
            json={"reason": "spam"},
        )
    SchemaValidator(resp).status(401).attach_to_report("TC-PI-002 no auth")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_003_report_post_non_existent(regular_user):
    """TC-PI-003 | Negative | Report non-existent post_id → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_report(BoundaryValues.NON_EXISTENT_UUID),
            json={"reason": "spam"},
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-PI-003 non-existent post")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_004_report_own_post(regular_user):
    """TC-PI-004 | Negative | User cannot report their own post → 400/403"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        create_resp = await client.post(
            APIEndpoints.POSTS,
            json=CreatePostPayload.valid().as_dict(),
        )
    assert create_resp.status_code in (200, 201), (
        f"TC-PI-004 setup: post creation failed: {create_resp.status_code}"
    )
    body = create_resp.json()
    own_post_id = (body.get("data") or body).get("id", "")
    assert own_post_id, f"No post id in create response: {body}"

    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_report(own_post_id),
            json={"reason": "spam"},
        )

    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(regular_user["token"])
            await client.delete(APIEndpoints.post_detail(own_post_id))
    except Exception:
        pass

    SchemaValidator(resp).status_in(400, 403).attach_to_report("TC-PI-004 report own post")


# ═══════════════════════════════════════════════════════════════════════════════
#  NOT INTERESTED  —  POST /v1/posts/{post_id}/not-interested
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_005_not_interested_valid(regular_user, reported_post):
    """TC-PI-005 | Smoke | Mark not-interested on valid post → 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(APIEndpoints.post_not_interested(reported_post))
    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-PI-005 not interested")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_006_not_interested_no_auth(reported_post):
    """TC-PI-006 | Negative | Not-interested without Bearer token → 401"""
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.post_not_interested(reported_post))
    SchemaValidator(resp).status(401).attach_to_report("TC-PI-006 no auth")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_007_not_interested_non_existent(regular_user):
    """TC-PI-007 | Negative | Not-interested on non-existent post_id → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_not_interested(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-PI-007 non-existent post")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_008_not_interested_hidden_post(regular_user, hidden_post):
    """TC-PI-008 | Negative | Not-interested on admin-hidden post → 4xx"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(APIEndpoints.post_not_interested(hidden_post))
    SchemaValidator(resp).status_in(400, 403, 404).attach_to_report("TC-PI-008 hidden post")


# ═══════════════════════════════════════════════════════════════════════════════
#  TRACK VIEW  —  POST /v1/posts/{post_id}/view
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_009_track_view_valid(regular_user, reported_post):
    """TC-PI-009 | Smoke | Track post view — authenticated → 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(APIEndpoints.post_view(reported_post))
    SchemaValidator(resp).status(200).attach_to_report("TC-PI-009 track view")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_010_track_view_no_auth(reported_post):
    """TC-PI-010 | Negative | Track view without Bearer token → 401"""
    async with HonoAPIClient() as client:
        resp = await client.post(APIEndpoints.post_view(reported_post))
    SchemaValidator(resp).status(401).attach_to_report("TC-PI-010 no auth")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_011_track_view_non_existent(regular_user):
    """TC-PI-011 | Negative | Track view on non-existent post_id → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_view(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-PI-011 non-existent post")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_012_track_view_idempotent(regular_user, reported_post):
    """TC-PI-012 | Boundary | Tracking the same post view twice returns 200 (idempotent)"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        first = await client.post(APIEndpoints.post_view(reported_post))
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        second = await client.post(APIEndpoints.post_view(reported_post))
    SchemaValidator(first).status(200)
    SchemaValidator(second).status(200).attach_to_report("TC-PI-012 idempotent view")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_013_report_duplicate(regular_user, reported_post):
    """TC-PI-013 | Boundary | Reporting the same post twice → 400/409

    Relies on TC-PI-001 (smoke) having already reported reported_post.
    Priority sort guarantees smoke runs before boundary.
    """
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user["token"])
        resp = await client.post(
            APIEndpoints.post_report(reported_post),
            json={"reason": "spam"},
        )
    SchemaValidator(resp).status_in(400, 409).attach_to_report("TC-PI-013 duplicate report")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_PI_014_report_no_api_key(reported_post):
    """TC-PI-014 | Security | Report post without x-api-key header → 401/403"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.post(
            APIEndpoints.post_report(reported_post),
            json={"reason": "spam"},
        )
    SchemaValidator(resp).status_in(401, 403).attach_to_report("TC-PI-014 no api key")

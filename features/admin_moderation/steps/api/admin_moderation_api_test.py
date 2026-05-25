"""Admin Moderation API tests — list reports, hide, dismiss, unhide."""
import pytest
import allure

from config.test_config import APIEndpoints
from config.test_data import BoundaryValues
from features.posts.test_data.create_post_test_data import CreatePostPayload
from platforms.api.httpx_client import HonoAPIClient
from skills.api.schema_validator import SchemaValidator

pytestmark = [allure.feature("Admin Moderation"), allure.suite("API")]

# ─── helpers ──────────────────────────────────────────────────────────────────

_REPORT_PAYLOAD = {"category": "SPAM"}


async def _create_post(owner_token: str) -> str:
    """Create a post as owner_token user; return post_id."""
    async with HonoAPIClient() as client:
        client.set_auth_token(owner_token)
        resp = await client.post(APIEndpoints.POSTS, json=CreatePostPayload.valid().as_dict())
    assert resp.status_code in (200, 201), (
        f"Inline post creation failed: {resp.status_code} — {resp.text[:200]}"
    )
    body = resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in create response: {body}"
    return post_id


async def _report_post(reporter_token: str, post_id: str) -> None:
    """Submit a report on post_id as reporter_token user."""
    async with HonoAPIClient() as client:
        client.set_auth_token(reporter_token)
        resp = await client.post(APIEndpoints.post_report(post_id), json=_REPORT_PAYLOAD)
    assert resp.status_code in (200, 201), (
        f"Inline report submission failed: {resp.status_code} — {resp.text[:200]}"
    )


async def _delete_post(owner_token: str, post_id: str) -> None:
    """Best-effort post deletion."""
    try:
        async with HonoAPIClient() as client:
            client.set_auth_token(owner_token)
            await client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  LIST REPORTED POSTS  —  GET /v1/admin/reports/posts
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_001_list_reported_posts_pending(admin_token, pending_reported_post):
    """TC-AM-001 | Smoke | GET reports?status=PENDING returns 200 with valid schema"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"page": 1, "per_page": 20, "status": "PENDING"},
        )
    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-AM-001 list pending")
    data = resp.json().get("data", [])
    if data:
        item = data[0]
        assert "report_id" in item or "id" in item, f"Missing id field in item: {item}"
        assert "status" in item, f"Missing status in item: {item}"
        assert "post" in item and "id" in item["post"], f"Missing post.id in item: {item}"


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_002_list_reported_posts_hidden(admin_token, hidden_reported_post):
    """TC-AM-002 | Smoke | GET reports?status=HIDDEN returns only hidden posts"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"status": "HIDDEN"},
        )
    SchemaValidator(resp).status(200).attach_to_report("TC-AM-002 list hidden")
    data = resp.json().get("data", [])
    for item in data:
        assert item.get("post", {}).get("is_hidden") is True, (
            f"Non-hidden post returned in HIDDEN filter: {item}"
        )


@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_003_list_reported_posts_dismissed(admin_token):
    """TC-AM-003 | Smoke | GET reports?status=DISMISSED returns 200"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"status": "DISMISSED"},
        )
    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-AM-003 list dismissed")


@pytest.mark.boundary
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_004_list_reported_posts_per_page_max(admin_token):
    """TC-AM-004 | Boundary | per_page=100 (max) returns 200 with ≤100 items"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"per_page": 100},
        )
    SchemaValidator(resp).status(200).attach_to_report("TC-AM-004 per_page=100")
    data = resp.json().get("data", [])
    assert len(data) <= 100, f"Received {len(data)} items, expected ≤100"


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_005_list_reported_posts_per_page_over_max(admin_token):
    """TC-AM-005 | Negative | per_page=101 (over max) → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"per_page": 101},
        )
    SchemaValidator(resp).status(422).attach_to_report("TC-AM-005 per_page=101")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_006_list_reported_posts_invalid_status(admin_token):
    """TC-AM-006 | Negative | Unknown status filter → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.get(
            APIEndpoints.ADMIN_REPORTS_POSTS,
            params={"status": "INVALID_STATUS"},
        )
    SchemaValidator(resp).status(422).attach_to_report("TC-AM-006 invalid status")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_007_list_reported_posts_no_api_key():
    """TC-AM-007 | Security | Missing x-api-key → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.get(APIEndpoints.ADMIN_REPORTS_POSTS)
    SchemaValidator(resp).status(401).attach_to_report("TC-AM-007 no api key")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_008_list_reported_posts_non_admin(regular_user_token):
    """TC-AM-008 | Security | Non-admin Bearer token → 403"""
    async with HonoAPIClient() as client:
        client.set_auth_token(regular_user_token)
        resp = await client.get(APIEndpoints.ADMIN_REPORTS_POSTS)
    SchemaValidator(resp).status(403).attach_to_report("TC-AM-008 non-admin")


# ═══════════════════════════════════════════════════════════════════════════════
#  HIDE POST  —  POST /v1/admin/reports/posts/{post_id}/hide
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_009_hide_post_success(admin_token, second_user_token, auth_token):
    """TC-AM-009 | Smoke | Admin hides a reported post → 200 + OK

    Creates an inline post (state-safe: does not mutate any shared fixture).
    """
    post_id = await _create_post(second_user_token)
    await _report_post(auth_token, post_id)

    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_hide(post_id))

    await _delete_post(second_user_token, post_id)

    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-AM-009 hide success")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_010_hide_post_already_hidden(admin_token, hidden_reported_post):
    """TC-AM-010 | Negative | Hide a post that is already hidden → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_hide(hidden_reported_post))
    (SchemaValidator(resp)
        .status(422)
        .code_equals("NOKUNPROC")
        .body_contains_error("already hidden")
        .attach_to_report("TC-AM-010 already hidden"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_011_hide_post_not_found(admin_token):
    """TC-AM-011 | Negative | Hide non-existent post → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(
            APIEndpoints.admin_reports_post_hide(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-AM-011 not found")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_012_hide_post_no_api_key(pending_reported_post):
    """TC-AM-012 | Security | Missing x-api-key on hide endpoint → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.post(APIEndpoints.admin_reports_post_hide(pending_reported_post))
    SchemaValidator(resp).status(401).attach_to_report("TC-AM-012 no api key")


# ═══════════════════════════════════════════════════════════════════════════════
#  DISMISS POST REPORTS  —  POST /v1/admin/reports/posts/{post_id}/dismiss
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_013_dismiss_post_reports_success(admin_token, second_user_token, auth_token):
    """TC-AM-013 | Smoke | Admin dismisses reports on a pending post → 200 + OK

    Creates an inline post (state-safe: does not mutate any shared fixture).
    """
    post_id = await _create_post(second_user_token)
    await _report_post(auth_token, post_id)

    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_dismiss(post_id))

    await _delete_post(second_user_token, post_id)

    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-AM-013 dismiss success")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_014_dismiss_reports_post_is_hidden(admin_token, hidden_reported_post):
    """TC-AM-014 | Negative | Dismiss reports on a hidden post → 422 (unhide first)"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_dismiss(hidden_reported_post))
    (SchemaValidator(resp)
        .status(422)
        .code_equals("NOKUNPROC")
        .body_contains_error("hidden")
        .attach_to_report("TC-AM-014 dismiss hidden post"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_015_dismiss_reports_no_pending_reports(admin_token, second_user_token):
    """TC-AM-015 | Negative | Dismiss reports on a post with no reports → 404/422"""
    post_id = await _create_post(second_user_token)

    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_dismiss(post_id))

    await _delete_post(second_user_token, post_id)

    SchemaValidator(resp).status_in(404, 422).attach_to_report("TC-AM-015 no pending reports")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_016_dismiss_reports_post_not_found(admin_token):
    """TC-AM-016 | Negative | Dismiss reports on non-existent post → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(
            APIEndpoints.admin_reports_post_dismiss(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-AM-016 not found")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_017_dismiss_reports_no_api_key(pending_reported_post):
    """TC-AM-017 | Security | Missing x-api-key on dismiss endpoint → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.post(APIEndpoints.admin_reports_post_dismiss(pending_reported_post))
    SchemaValidator(resp).status(401).attach_to_report("TC-AM-017 no api key")


# ═══════════════════════════════════════════════════════════════════════════════
#  UNHIDE POST  —  POST /v1/admin/reports/posts/{post_id}/unhide
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_018_unhide_post_success(admin_token, second_user_token, auth_token):
    """TC-AM-018 | Smoke | Admin unhides a hidden post → 200 + OK

    Creates an inline post, reports it, admin hides it, then unhides it.
    State-safe: does not mutate hidden_reported_post fixture.
    """
    post_id = await _create_post(second_user_token)
    await _report_post(auth_token, post_id)

    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        hide_resp = await client.post(APIEndpoints.admin_reports_post_hide(post_id))
    assert hide_resp.status_code in (200, 201), (
        f"TC-AM-018 setup: hide failed: {hide_resp.status_code}"
    )

    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_unhide(post_id))

    await _delete_post(second_user_token, post_id)

    SchemaValidator(resp).status(200).code_equals("OK").attach_to_report("TC-AM-018 unhide success")


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_019_unhide_post_not_hidden(admin_token, pending_reported_post):
    """TC-AM-019 | Negative | Unhide a post that is not currently hidden → 422"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(APIEndpoints.admin_reports_post_unhide(pending_reported_post))
    (SchemaValidator(resp)
        .status(422)
        .code_equals("NOKUNPROC")
        .body_contains_error("not hidden")
        .attach_to_report("TC-AM-019 not hidden"))


@pytest.mark.negative
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_020_unhide_post_not_found(admin_token):
    """TC-AM-020 | Negative | Unhide non-existent post → 404"""
    async with HonoAPIClient() as client:
        client.set_auth_token(admin_token)
        resp = await client.post(
            APIEndpoints.admin_reports_post_unhide(BoundaryValues.NON_EXISTENT_UUID)
        )
    SchemaValidator(resp).status(404).attach_to_report("TC-AM-020 not found")


@pytest.mark.security
@pytest.mark.api
@pytest.mark.asyncio
async def test_TC_AM_021_unhide_post_no_api_key(hidden_reported_post):
    """TC-AM-021 | Security | Missing x-api-key on unhide endpoint → 401"""
    async with HonoAPIClient.no_api_key() as client:
        resp = await client.post(APIEndpoints.admin_reports_post_unhide(hidden_reported_post))
    SchemaValidator(resp).status(401).attach_to_report("TC-AM-021 no api key")

"""Feature-level fixtures for Posts API tests.

Depends on shared auth chain from conftest.shared_fixtures (registered globally
via pytest_plugins in root conftest.py). Re-imported here to make dependencies explicit.
"""
import pytest
import structlog

from conftest_shared_fixtures import (  # noqa: F401 — re-export for pytest fixture discovery
    auth_token,
    authenticated_client,
    registered_user,
)
from config.test_config import APIEndpoints
from features.posts.test_data.create_post_test_data import CreatePostPayload

logger = structlog.get_logger(__name__)


# ── post_user ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def post_user(registered_user):
    """Alias — delegates to shared registered_user. No self-contained user creation."""
    return registered_user


# ── post_token ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def post_token(auth_token):
    """Alias — provides the module-scoped token for post tests."""
    return auth_token


# ── created_post_id ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def created_post_id(authenticated_client):
    """
    Creates a post shared across the entire module.
    Tests in this module must NOT delete this post — it is shared state.
    For delete-post tests, create a post inline within the test function.
    Teardown: best-effort DELETE after module completes.
    """
    resp = await authenticated_client.post(
        APIEndpoints.POSTS,
        json=CreatePostPayload.valid().as_dict(),
    )
    assert resp.status_code in (200, 201), (
        f"created_post_id fixture failed: {resp.status_code} — {resp.text[:200]}"
    )
    body = resp.json()
    post_id = (body.get("data") or body).get("id", "")
    assert post_id, f"No post id in response: {body}"

    logger.info("fixture_post_created", fixture="created_post_id", post_id=post_id)

    yield post_id

    try:
        await authenticated_client.delete(APIEndpoints.post_detail(post_id))
    except Exception:
        pass

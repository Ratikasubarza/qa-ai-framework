"""
Test User Helper — full lifecycle untuk E2E testing.
Register → Verify → Approve → Set password → Complete onboarding → Ready to login
"""
import asyncio
import pytest
import time
import os
import httpx
import structlog
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from core.db.db_client import DBClient

logger = structlog.get_logger(__name__)

TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", "TestPass123!")

def parse_json_response(resp: httpx.Response, action: str) -> dict:
    """
    Safely parse HTTP response as JSON with useful debugging info.
    Prevents raw JSONDecodeError without context.
    """
    content_type = resp.headers.get("content-type", "")
    body_preview = resp.text[:1000] if resp.text else "<empty body>"

    if resp.status_code >= 400:
        raise AssertionError(
            f"{action} failed. "
            f"Status={resp.status_code}, "
            f"Content-Type={content_type}, "
            f"Body={body_preview}"
        )

    if not resp.text.strip():
        raise AssertionError(
            f"{action} returned empty body. "
            f"Status={resp.status_code}, "
            f"Content-Type={content_type}"
        )

    if "application/json" not in content_type.lower():
        raise AssertionError(
            f"{action} response is not JSON. "
            f"Status={resp.status_code}, "
            f"Content-Type={content_type}, "
            f"Body={body_preview}"
        )

    try:
        return resp.json()
    except ValueError as exc:
        raise AssertionError(
            f"{action} returned invalid JSON. "
            f"Status={resp.status_code}, "
            f"Content-Type={content_type}, "
            f"Body={body_preview}"
        ) from exc


_TRANSIENT_CODES: frozenset[int] = frozenset({500, 502, 503, 504})
_USER_CREATION_MAX_RETRIES: int = 3
_USER_CREATION_BACKOFF: tuple[int, ...] = (2, 4)


async def _call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json: dict | None = None,
    headers: dict | None = None,
    step_name: str,
) -> httpx.Response:
    """HTTP request with exponential backoff on transient 5xx responses.

    4xx responses are returned immediately — they are deliberate API responses,
    not transient failures. Only 500/502/503/504 are retried.
    """
    resp: httpx.Response | None = None
    for attempt in range(1, _USER_CREATION_MAX_RETRIES + 1):
        resp = await client.request(method, path, json=json, headers=headers)
        if resp.status_code not in _TRANSIENT_CODES:
            return resp
        if attempt < _USER_CREATION_MAX_RETRIES:
            delay = _USER_CREATION_BACKOFF[min(attempt - 1, len(_USER_CREATION_BACKOFF) - 1)]
            logger.warning(
                "user_creation_retry",
                step=step_name,
                attempt=attempt,
                status=resp.status_code,
                delay_seconds=delay,
            )
            await asyncio.sleep(delay)
    return resp  # type: ignore[return-value]  # loop always executes ≥1 time


def _post_with_retry(client, path, *, json=None, headers=None, step_name):
    return _call_with_retry(client, "POST", path, json=json, headers=headers, step_name=step_name)


async def create_approved_user(
    fullname: str = None,
    suffix: str = None,
    password: str = None,
) -> dict:
    """
    Create a fully approved and onboarded test user ready to login.

    Returns:
        dict with email, password, user_id

    Flow:
        1. Register via API
        2. Set verified in DB
        3. Approve via CMS API (sets approved_at, approved_by, status=APPROVED)
        4. Override password in DB
        5. Login as new user + complete onboarding (sets onboarding_completed_at)
    """
    from config.test_data import TEST_EMAIL_DOMAIN
    ts = suffix or int(time.time())
    email = f"testonboard+{ts}@{TEST_EMAIL_DOMAIN}"
    phone = str(ts)[-8:]
    pwd = password or TEST_PASSWORD

    api_url = os.getenv("HONO_API_URL")
    api_key = os.getenv("HONO_API_KEY")

    if not api_url:
        raise EnvironmentError("HONO_API_URL must be set in .env")

    if not api_key:
        raise EnvironmentError("HONO_API_KEY must be set in .env")

    # Step 1: Register
    async with httpx.AsyncClient(
        base_url=api_url,
        headers={"x-api-key": api_key},
        timeout=30,
    ) as client:
        resp = await _post_with_retry(client, "/v1/users/register", json={
            "fullname": fullname or f"Test User {ts}",
            "email": email,
            "phone_number": f"81{phone}",
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/testuser{ts}",
        }, step_name="register")

    if resp.status_code == 500 and "email sending quota" in resp.text:
        raise pytest.skip.Exception("Resend daily email quota reached — skip test")

    register_data = parse_json_response(resp, "Register user")

    assert resp.status_code == 200, (
        f"Register failed. "
        f"Status={resp.status_code}, "
        f"Body={register_data}"
    )

    logger.info("test_user_registered", email=email)

    # Step 2: Set verified in DB — poll until row appears
    deadline = time.monotonic() + 5.0
    user = None

    while time.monotonic() < deadline:
        with DBClient() as db:
            user = db.get_user_by_email(email)

        if user:
            break

        time.sleep(0.3)

    assert user, f"User not found in DB after 5s: {email}"

    with DBClient() as db:
        db.set_verified(email)

    # Step 3: Get CMS token + approve
    async with httpx.AsyncClient(
        base_url=api_url,
        headers={"x-api-key": api_key},
        timeout=30,
    ) as client:
        _cms_email = os.getenv("CMS_EMAIL", "")
        _cms_password = os.getenv("CMS_PASSWORD", "")

        if not _cms_email or not _cms_password:
            raise EnvironmentError("CMS_EMAIL and CMS_PASSWORD must be set in .env")

        login_resp = await _post_with_retry(client, "/v1/users/login", json={
            "email": _cms_email,
            "password": _cms_password,
            "resource": "admin",
        }, step_name="cms_login")

        login_data = parse_json_response(login_resp, "CMS login")

        body = login_data.get("data", login_data)
        cms_token = body.get("accessToken") or body.get("token", "")

        assert cms_token, (
            f"CMS token empty. "
            f"Status={login_resp.status_code}, "
            f"Body={login_data}"
        )

        approve_resp = await _post_with_retry(
            client,
            f"/v1/users/{user['id']}/approve",
            headers={"Authorization": f"Bearer {cms_token}"},
            step_name="approve_user",
        )

    if approve_resp.status_code >= 400:
        raise AssertionError(
            f"Approve user failed. "
            f"Status={approve_resp.status_code}, "
            f"Content-Type={approve_resp.headers.get('content-type')}, "
            f"Body={approve_resp.text[:1000] if approve_resp.text else '<empty body>'}"
        )

    logger.info(
        "test_user_approved",
        email=email,
        status=approve_resp.status_code,
    )

    # Step 4: Override password — poll until approved status is persisted
    deadline = time.monotonic() + 5.0

    while time.monotonic() < deadline:
        with DBClient() as db:
            _u = db.get_user_by_email(email)

        if _u and _u.get("status") == "APPROVED":
            break

        time.sleep(0.3)

    with DBClient() as db:
        db.set_password(email, pwd)
        final_user = db.get_user_by_email(email)

    assert final_user, f"Final user not found in DB: {email}"

    # Step 5: Complete onboarding — login as new user, then PUT /v1/users/onboarding.
    # This sets onboarding_completed_at and all profile fields, making the user
    # indistinguishable from a real user who completed the flow.
    from skills.data.data_generator import DataGenerator

    async with httpx.AsyncClient(
        base_url=api_url,
        headers={"x-api-key": api_key},
        timeout=30,
    ) as client:
        user_login_resp = await _post_with_retry(client, "/v1/users/login", json={
            "email":    email,
            "password": pwd,
        }, step_name="new_user_login")
        user_login_data = parse_json_response(user_login_resp, "New user login for onboarding")
        user_body  = user_login_data.get("data", user_login_data)
        user_token = user_body.get("accessToken") or user_body.get("token", "")
        assert user_token, f"New user login token empty after approval: {user_login_data}"

        onboard_resp = await _call_with_retry(
            client, "PUT", "/v1/users/onboarding",
            json=DataGenerator.valid_onboarding_payload(),
            headers={"Authorization": f"Bearer {user_token}"},
            step_name="onboarding",
        )

    if onboard_resp.status_code >= 400:
        raise AssertionError(
            f"Onboarding step failed. "
            f"Status={onboard_resp.status_code}, "
            f"Body={onboard_resp.text[:500]}"
        )

    logger.info(
        "test_user_ready",
        email=email,
        status=final_user["status"],
        onboarding=onboard_resp.status_code,
    )

    return {
        "email":    email,
        "password": pwd,
        "user_id":  user["id"],
        "status":   final_user["status"],
        "fullname": fullname or f"Test User {ts}",
    }


def create_approved_user_sync(fullname=None, suffix=None, password=None) -> dict:
    """Sync wrapper for pytest fixtures.

    Runs create_approved_user() in a background thread when called from inside a
    running event loop (e.g. async fixtures, pytest-asyncio), falling back to
    asyncio.run() in the normal sync-fixture path.
    """
    import concurrent.futures

    try:
        asyncio.get_running_loop()
        # Already inside a running loop — dispatch to a new thread to avoid RuntimeError.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run, create_approved_user(fullname, suffix, password)
            ).result(timeout=120)  # 120s covers 3 retries × 4 steps × ~10s each
    except RuntimeError:
        return asyncio.run(create_approved_user(fullname, suffix, password))
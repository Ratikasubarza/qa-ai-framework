"""
Test User Helper — full lifecycle untuk E2E testing.
Register → Verify → Approve → Set password → Ready to login
"""
import asyncio
import time
import os
import httpx
import structlog
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")

from core.db.db_client import DBClient

logger = structlog.get_logger(__name__)

TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", "TestPass123!")


async def create_approved_user(
    fullname: str = None,
    suffix: str = None,
    password: str = None,
) -> dict:
    """
    Create a fully approved test user ready to login.
    
    Returns:
        dict with email, password, user_id
    
    Flow:
        1. Register via API
        2. set_verified in DB
        3. Approve via CMS API  
        4. Override password in DB
    """
    ts = suffix or int(time.time())
    email = f"testonboard+{ts}@mailinator.com"
    phone = str(ts)[-8:]
    pwd = password or TEST_PASSWORD

    # Step 1: Register
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        headers={"x-api-key": os.getenv("HONO_API_KEY")},
        timeout=30
    ) as client:
        resp = await client.post("/v1/users/register", json={
            "fullname": fullname or f"Test User {ts}",
            "email": email,
            "phone_number": f"81{phone}",
            "phone_country_code": "ID",
            "linkedin": f"https://linkedin.com/in/testuser{ts}"
        })
    assert resp.status_code == 200, f"Register failed: {resp.status_code}"
    logger.info("test_user_registered", email=email)

    # Step 2: Set verified in DB
    time.sleep(1)
    with DBClient() as db:
        user = db.get_user_by_email(email)
        assert user, f"User not found: {email}"
        db.set_verified(email)

    # Step 3: Get CMS token + approve
    async with httpx.AsyncClient(
        base_url=os.getenv("HONO_API_URL"),
        headers={"x-api-key": os.getenv("HONO_API_KEY")},
        timeout=30
    ) as client:
        # CMS login
        login_resp = await client.post("/v1/users/login", json={
            "email":    os.getenv("CMS_EMAIL", "ops@hono.app"),
            "password": os.getenv("CMS_PASSWORD", "password"),
            "resource": "admin"
        })
        login_data = login_resp.json()
        body = login_data.get("data", login_data)
        cms_token = body.get("accessToken") or body.get("token", "")
        assert cms_token, f"CMS token empty: {login_data}"

        # Approve user
        approve_resp = await client.post(
            f"/v1/users/{user['id']}/approve",
            headers={"Authorization": f"Bearer {cms_token}"}
        )
    logger.info("test_user_approved",
        email=email, status=approve_resp.status_code)

    # Step 4: Override password (system temp password → our test password)
    time.sleep(1)
    with DBClient() as db:
        db.set_password(email, pwd)
        final_user = db.get_user_by_email(email)

    logger.info("test_user_ready",
        email=email, status=final_user["status"])

    return {
        "email":    email,
        "password": pwd,
        "user_id":  user["id"],
        "status":   final_user["status"],
        "fullname": fullname or f"Test User {ts}",
    }


def create_approved_user_sync(fullname=None, suffix=None, password=None) -> dict:
    """Sync wrapper untuk pytest fixtures."""
    return asyncio.run(create_approved_user(fullname, suffix, password))

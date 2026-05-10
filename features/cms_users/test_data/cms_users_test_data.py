"""
CMS Users Test Data — test data untuk CMS user management endpoints.
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class CmsUsersTestData:
    # ── Pagination defaults ───────────────────────────────────────────
    DEFAULT_PAGE     = 1
    DEFAULT_SIZE     = 20
    DEFAULT_ORDER_BY = "name"
    DEFAULT_ORDER    = "ASC"

    # ── User status values ────────────────────────────────────────────
    STATUS_APPROVED  = 2
    STATUS_PENDING   = 1
    STATUS_REJECTED  = 3

    # ── Valid query params ────────────────────────────────────────────
    VALID_PARAMS = {
        "page":    1,
        "size":    20,
        "orderBy": "name",
        "order":   "ASC",
    }

    # ── Expected response fields ──────────────────────────────────────
    REQUIRED_USER_FIELDS = [
        "id", "name", "email",
        "phone_code", "phone_number",
        "social_accounts", "status",
    ]

    # ── Invalid params ────────────────────────────────────────────────
    INVALID_PAGE  = -1
    INVALID_SIZE  = 0
    INVALID_ORDER = "INVALID"

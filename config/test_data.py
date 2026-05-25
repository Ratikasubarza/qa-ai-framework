"""
Centralized boundary values and known test accounts.
Usage: from config.test_data import BoundaryValues, KnownAccounts
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class BoundaryValues:
    """All boundary/limit values used across test files."""

    # ── Name / text length ────────────────────────────────────────────
    MAX_NAME_LENGTH         = 500
    LONG_NAME_LENGTH        = 501    # one over max — used in boundary tests
    MAX_EMAIL_LENGTH        = 500
    LONG_EMAIL_LENGTH       = 501
    MAX_POST_CONTENT_LENGTH = 5000

    # ── Password ──────────────────────────────────────────────────────
    MIN_PASSWORD_LENGTH     = 8

    # ── Phone ─────────────────────────────────────────────────────────
    MIN_PHONE_DIGITS        = 3     # too short
    MAX_PHONE_DIGITS        = 21    # too long (boundary doc test)

    # ── Onboarding multi-selects ──────────────────────────────────────
    MIN_INDUSTRIES          = 1
    MAX_INDUSTRIES          = 2
    OVER_MAX_INDUSTRIES     = 3     # should be blocked per API spec

    MIN_SOCIAL_CAUSES       = 1
    MAX_SOCIAL_CAUSES       = 5

    MIN_BUSINESS_AREAS      = 1
    MAX_BUSINESS_AREAS      = 5

    MIN_INTERESTS           = 1
    MAX_INTERESTS           = 10

    # ── UUIDs ─────────────────────────────────────────────────────────
    NON_EXISTENT_UUID       = "00000000-0000-0000-0000-000000000000"

    # ── Response time SLA ─────────────────────────────────────────────
    MAX_RESPONSE_MS         = 3000


class KnownAccounts:
    """Pre-existing registered users on staging — used for duplicate/conflict tests."""

    EXISTING_EMAIL_A    = os.getenv("STAGING_EMAIL",         "testingHonoA@mailinator.com")  # Fallback for local dev only — must be set in CI/CD secrets
    EXISTING_PHONE_A    = os.getenv("TEST_KNOWN_PHONE_A",    "81234567104")                   # Fallback for local dev only — must be set in CI/CD secrets
    EXISTING_EMAIL_B    = os.getenv("TEST_KNOWN_EMAIL_B",    "testingHonoB@mailinator.com")   # Fallback for local dev only — must be set in CI/CD secrets
    EXISTING_PHONE_B    = os.getenv("TEST_KNOWN_PHONE_B",    "81234567105")                   # Fallback for local dev only — must be set in CI/CD secrets

    # ── CMS admin ─────────────────────────────────────────────────────
    CMS_EMAIL           = os.getenv("STAGING_CMS_EMAIL",    "")
    CMS_PASSWORD        = os.getenv("STAGING_CMS_PASSWORD", "")
    ADMIN_TOKEN         = os.getenv("TEST_ADMIN_TOKEN",     "")  # Pre-issued admin JWT — must be set in CI/CD secrets; never commit a real value

    # ── Staging user ──────────────────────────────────────────────────
    STAGING_EMAIL       = os.getenv("STAGING_EMAIL",    "")
    STAGING_PASSWORD    = os.getenv("STAGING_PASSWORD", "")

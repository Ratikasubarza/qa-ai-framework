"""
Login Test Data — single source of truth untuk semua test data login.
Update di sini, berlaku di semua test: web, API, Android.

CARA PAKAI:
  from features.login.test_data.login_test_data import LoginTestData
  email = LoginTestData.VALID_EMAIL
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class LoginTestData:
    # ── Valid credentials ──────────────────────────────────────────────
    VALID_EMAIL    = os.getenv("STAGING_EMAIL",    "testingHonoA@mailinator.com")
    VALID_PASSWORD = os.getenv("STAGING_PASSWORD", "")

    # ── Invalid credentials ────────────────────────────────────────────
    WRONG_PASSWORD     = "WrongPass123!"
    INVALID_EMAIL      = "bad-email"
    NONEXISTENT_EMAIL  = "notexist@mailinator.com"
    EMPTY_STRING       = ""

    # ── Security payloads ─────────────────────────────────────────────
    SQL_INJECTION      = "'; DROP TABLE users;--"
    XSS_PAYLOAD        = "<script>alert('xss')</script>"
    LONG_STRING        = "a" * 500

    # ── Expected results ──────────────────────────────────────────────
    EXPECTED_REDIRECT  = "/feed"
    ERROR_KEYWORDS     = ["invalid", "incorrect", "error", "wrong"]

    # ── Performance thresholds ────────────────────────────────────────
    MAX_RESPONSE_MS    = 3000

    # ── Gherkin Examples Tables ───────────────────────────────────────
    # Dipakai di Scenario Outline
    INVALID_EMAIL_CASES = [
        ("bad-email",          "invalid format"),
        ("",                   "empty email"),
        ("test@",              "incomplete domain"),
        (SQL_INJECTION,        "SQL injection"),
        (XSS_PAYLOAD,          "XSS payload"),
    ]

    INVALID_PASSWORD_CASES = [
        (VALID_EMAIL, WRONG_PASSWORD,     "wrong password"),
        (VALID_EMAIL, EMPTY_STRING,       "empty password"),
        (VALID_EMAIL, LONG_STRING[:50],   "too long password"),
    ]

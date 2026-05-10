"""
Register Test Data — single source of truth untuk semua test data register.
"""
import os
import time
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class RegisterTestData:
    # ── Valid registration data ────────────────────────────────────────
    @staticmethod
    def valid_payload(suffix: str = None) -> dict:
        """Generate unique valid registration payload."""
        ts = suffix or int(time.time())
        # Use last 9 digits of timestamp for unique phone number
        phone = str(ts)[-9:]
        return {
            "fullname":           f"Test User {ts}",
            "email":              f"testregister+{ts}@mailinator.com",
            "phone_number":       phone,
            "phone_country_code": "ID",
            "linkedin":           f"https://linkedin.com/in/testuser{ts}",
        }

    # ── Existing registered email ─────────────────────────────────────
    EXISTING_EMAIL = os.getenv("STAGING_EMAIL", "testingHonoA@mailinator.com")

    # ── Invalid payloads ──────────────────────────────────────────────
    INVALID_EMAIL_PAYLOAD = {
        "fullname":           "Test User",
        "email":              "not-an-email",
        "phone_number":       "8123456789",
        "phone_country_code": "ID",
        "linkedin":           "https://linkedin.com/in/test",
    }

    MISSING_FIELDS_PAYLOAD = {
        "email": "incomplete@mailinator.com"
    }

    EMPTY_PAYLOAD = {}

    # ── Phone country codes ───────────────────────────────────────────
    VALID_COUNTRY_CODE   = "ID"
    INVALID_COUNTRY_CODE = "XX"

    # ── Expected responses ────────────────────────────────────────────
    SUCCESS_CODE    = "OK"
    SUCCESS_MESSAGE = "Data saved"
    # ── Known registered users for duplicate tests ────────────────────
    EXISTING_EMAIL_A    = "testingHonoA@mailinator.com"
    EXISTING_PHONE_A    = "81234567104"
    EXISTING_EMAIL_B    = "testingHonoB@mailinator.com"
    EXISTING_PHONE_B    = "81234567105"

    # ── Security payloads ─────────────────────────────────────────────
    SQL_INJECTION_NAME  = "'; DROP TABLE users; --"
    XSS_NAME           = "<script>alert('xss')</script>"
    LONG_NAME          = "A" * 501

"""
Register Test Data — single source of truth untuk semua test data register.

Two interfaces:
  1. RegisterTestData (class methods) — legacy, backward compatible
  2. RegisterPayload  (dataclass)     — Builder pattern untuk test baru
"""
import os
import time
from dataclasses import dataclass, field
from dotenv import load_dotenv
from core.test_data.base_builder import PayloadBuilder

load_dotenv(dotenv_path=".env")


# ── Builder — for new tests ───────────────────────────────────────────────────

@dataclass
class RegisterPayload(PayloadBuilder):
    fullname:           str = field(default_factory=lambda: f"Test User {int(time.time())}")
    email:              str = field(default_factory=lambda: f"qa+{int(time.time())}@mailinator.com")
    phone_number:       str = field(default_factory=lambda: str(int(time.time()))[-9:])
    phone_country_code: str = "ID"
    linkedin:           str = "https://linkedin.com/in/Ratikasaubarza"

    # ── Named constructors for common cases ──────────────────────────────

    @classmethod
    def valid(cls) -> "RegisterPayload":
        return cls()

    @classmethod
    def with_invalid_email(cls) -> "RegisterPayload":
        return cls(email="not-an-email")

    @classmethod
    def with_sql_injection(cls) -> "RegisterPayload":
        return cls(fullname="'; DROP TABLE users; --")

    @classmethod
    def with_xss(cls) -> "RegisterPayload":
        return cls(fullname="<script>alert('xss')</script>")

    @classmethod
    def with_long_name(cls, length: int = 501) -> "RegisterPayload":
        return cls(fullname="A" * length)

    @classmethod
    def with_invalid_phone_code(cls) -> "RegisterPayload":
        return cls(phone_country_code="XX")


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

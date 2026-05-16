"""
Login Test Data — single source of truth untuk semua test data login.
Update di sini, berlaku di semua test: web, API, Android.

Two interfaces:
  1. LoginTestData  (class constants) — legacy, backward compatible
  2. LoginPayload   (dataclass)       — Builder pattern untuk test baru

CARA PAKAI:
  from features.login.test_data.login_test_data import LoginTestData, LoginPayload
  email = LoginTestData.VALID_EMAIL
  payload = LoginPayload.valid().as_dict()
  payload = LoginPayload.valid().with_field(password="wrong")
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from core.test_data.base_builder import PayloadBuilder

load_dotenv(dotenv_path=".env")


# ── Builder — for new tests ───────────────────────────────────────────────────

@dataclass
class LoginPayload(PayloadBuilder):
    email:    str = field(default_factory=lambda: os.getenv("STAGING_EMAIL", "testingHonoA@mailinator.com"))
    password: str = field(default_factory=lambda: os.getenv("STAGING_PASSWORD", ""))
    resource: str = ""

    def as_dict(self) -> dict:
        d = {"email": self.email, "password": self.password}
        if self.resource:
            d["resource"] = self.resource
        return d

    @classmethod
    def valid(cls) -> "LoginPayload":
        return cls()

    @classmethod
    def cms_admin(cls) -> "LoginPayload":
        return cls(resource="admin")

    @classmethod
    def with_wrong_password(cls) -> "LoginPayload":
        return cls(password="WrongPass123!")

    @classmethod
    def with_invalid_email(cls) -> "LoginPayload":
        return cls(email="bad-email")

    @classmethod
    def empty(cls) -> "LoginPayload":
        return cls(email="", password="")


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

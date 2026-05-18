"""
CMS Login Test Data — single source of truth untuk CMS Dashboard credentials.
CMS login berbeda dari app login karena membutuhkan field "resource": "admin".
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class CmsLoginTestData:
    # ── Valid CMS credentials ──────────────────────────────────────────
    VALID_EMAIL    = os.getenv("CMS_EMAIL",    "")
    VALID_PASSWORD = os.getenv("CMS_PASSWORD", "")
    RESOURCE       = "admin"

    if not VALID_EMAIL or not VALID_PASSWORD:
        raise EnvironmentError("CMS_EMAIL and CMS_PASSWORD must be set in .env")

    # ── Invalid credentials ────────────────────────────────────────────
    WRONG_PASSWORD     = "WrongPass123!"
    INVALID_EMAIL      = "bad-email"
    WRONG_RESOURCE     = "invalid_resource"
    EMPTY_STRING       = ""

    # ── Valid login payload ────────────────────────────────────────────
    @classmethod
    def valid_payload(cls) -> dict:
        return {
            "email":    cls.VALID_EMAIL,
            "password": cls.VALID_PASSWORD,
            "resource": cls.RESOURCE,
        }

    # ── Invalid payloads ──────────────────────────────────────────────
    @classmethod
    def wrong_password_payload(cls) -> dict:
        return {
            "email":    cls.VALID_EMAIL,
            "password": cls.WRONG_PASSWORD,
            "resource": cls.RESOURCE,
        }

    @classmethod
    def missing_resource_payload(cls) -> dict:
        return {
            "email":    cls.VALID_EMAIL,
            "password": cls.VALID_PASSWORD,
        }

    @classmethod
    def wrong_resource_payload(cls) -> dict:
        return {
            "email":    cls.VALID_EMAIL,
            "password": cls.VALID_PASSWORD,
            "resource": cls.WRONG_RESOURCE,
        }

    # ── Expected responses ────────────────────────────────────────────
    SUCCESS_TOKEN_KEY  = "accessToken"
    MAX_RESPONSE_MS    = 3000

"""Password change API test data.

Single source of truth for all password values used in users_password tests.
CURRENT_PASSWORD is derived from the same env var as test_user_helper so they
are always in sync — changing TEST_USER_PASSWORD in .env flows through everywhere.
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class UsersPasswordTestData:
    # Derived from the same env var as test_user_helper.py — never out of sync
    CURRENT_PASSWORD = os.getenv("TEST_USER_PASSWORD", "TestPass123!")
    NEW_PASSWORD = "NewTestPass456!"
    WRONG_CURRENT_PASSWORD = "WrongPass123!"

    # ── Payloads ───────────────────────────────────────────────────────

    @classmethod
    def valid_change_payload(cls) -> dict:
        return {
            "current_password": cls.CURRENT_PASSWORD,
            "new_password": cls.NEW_PASSWORD,
        }

    @classmethod
    def wrong_current_payload(cls) -> dict:
        return {
            "current_password": cls.WRONG_CURRENT_PASSWORD,
            "new_password": cls.NEW_PASSWORD,
        }

    @classmethod
    def missing_current_password_payload(cls) -> dict:
        return {"new_password": cls.NEW_PASSWORD}

    @classmethod
    def missing_new_password_payload(cls) -> dict:
        return {"current_password": cls.CURRENT_PASSWORD}

    # ── DB helpers ─────────────────────────────────────────────────────

    @classmethod
    def reset_password(cls, email: str) -> None:
        """Reset user password back to CURRENT_PASSWORD via DB.

        Call this in teardown after any test that successfully changes the
        password, so the DB stays consistent if the user is ever reused.
        """
        from core.db.db_client import DBClient
        with DBClient() as db:
            db.set_password(email, cls.CURRENT_PASSWORD)

    @classmethod
    def set_known_password(cls, email: str) -> None:
        """Force CURRENT_PASSWORD onto a user via DB — called by the fixture
        after create_approved_user so the password is always exactly what we
        expect, regardless of what the approval flow may have set.
        """
        from core.db.db_client import DBClient
        with DBClient() as db:
            db.set_password(email, cls.CURRENT_PASSWORD)

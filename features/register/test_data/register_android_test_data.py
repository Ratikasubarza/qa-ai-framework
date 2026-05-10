"""
Android Register Test Data.
"""
import time


class RegisterAndroidTestData:

    @staticmethod
    def valid_payload() -> dict:
        ts = int(time.time())
        phone = str(ts)[-8:]
        return {
            "fullname":  f"Test User {ts}",
            "email":     f"testmob+{ts}@mailinator.com",
            "phone":     f"81{phone}",
            "linkedin":  f"testuser{ts}",
        }

    # ── Invalid payloads ──────────────────────────────────────────────
    INVALID_EMAIL    = "not-an-email"
    EMPTY_STRING     = ""
    SHORT_NAME       = "A"

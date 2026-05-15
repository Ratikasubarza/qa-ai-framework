"""Email API test data and response contract helpers."""

import re


class UsersEmailTestData:
    EMAIL_PATH = "/v1/users/me/email"
    VERIFY_EMAIL_PATH = "/v1/users/verify-email"
    MAX_RESPONSE_MS = 3000

    SUCCESS_CODE = "OK"
    SAVED_MESSAGE = "Data saved"
    EMAIL_UPDATED_MESSAGE = "Email updated successfully"
    EXISTING_EMAIL_STATUS = 422
    EXISTING_EMAIL_CODE = "NOKUNPROC"
    EXISTING_EMAIL_MESSAGE = "email already exists"
    EXPIRED_STATUS = 410
    EXPIRED_CODE = "EXPIRED"
    EXPIRED_MESSAGE = "Verification link has expired"

    REQUIRED_BODY_KEYS = {"code", "message", "data"}

    @classmethod
    def unique_new_email(cls, current_email: str) -> str:
        match = re.search(r"\+(\d+)@", current_email)
        suffix = match.group(1) if match else "00000000"
        return f"testemailchange+{suffix}@mailinator.com"

    @classmethod
    def change_email_payload(cls, new_email: str) -> dict:
        return {"new_email": new_email}

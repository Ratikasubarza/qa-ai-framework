"""Account API test data and response contract helpers."""

import re


class UsersAccountTestData:
    ACCOUNT_PATH = "/v1/users/me/account"
    MAX_RESPONSE_MS = 3000

    REQUIRED_BODY_KEYS = {"code", "message", "data"}
    REQUIRED_CORE_DATA_KEYS = {
        "email",
        "phone_number",
        "phone_code",
        "phone_country_iso",
    }
    CONTRACT_NULLABLE_KEYS = {"phone_country_iso", "nationality"}
    REQUIRED_NATIONALITY_KEYS = {"id", "name", "iso2"}

    SUCCESS_CODE = "OK"
    SUCCESS_MESSAGE = "Data found"
    SAVED_MESSAGE = "Data saved"
    INVALID_PHONE_CODE_STATUS = 422
    INVALID_PHONE_CODE_RESPONSE_CODE = "NOKUNPROC"
    INVALID_PHONE_CODE_MESSAGE = "unknown country phone code"

    @classmethod
    def unique_phone_number(cls, email: str) -> str:
        match = re.search(r"\+(\d+)@", email)
        suffix = match.group(1)[-8:] if match else "00000000"
        return f"82{suffix}"

    @classmethod
    def valid_update_payload(cls, email: str) -> dict:
        return {
            "email": email,
            "phone_number": cls.unique_phone_number(email),
            "phone_code": "+62",
            "nationality_id": 101,
        }

    @classmethod
    def invalid_phone_code_payload(cls, email: str) -> dict:
        return {
            "email": email,
            "phone_number": "812345678",
            "phone_code": "XX",
        }

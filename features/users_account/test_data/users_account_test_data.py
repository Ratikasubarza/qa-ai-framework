"""Account API test data and response contract helpers."""


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

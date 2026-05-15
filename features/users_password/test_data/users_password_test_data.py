"""Password API test data.

All values are synthetic and safe to use with test-created users only.
"""


class UsersPasswordTestData:
    CURRENT_PASSWORD = "TestPass123!"
    NEW_PASSWORD = "NewTestPass456!"
    WRONG_CURRENT_PASSWORD = "WrongPass123!"

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
        return {
            "new_password": cls.NEW_PASSWORD,
        }

    @classmethod
    def missing_new_password_payload(cls) -> dict:
        return {
            "current_password": cls.CURRENT_PASSWORD,
        }

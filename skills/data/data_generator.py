"""
DataGenerator — shared test data generation.
Eliminates duplication across features/xxx/test_data/ files.
All boundary values reference BoundaryValues from config/test_data.py.
All reference IDs use ReferenceIDs from config/test_config.py.
"""
import time

from config.test_data import BoundaryValues
from config.test_config import ReferenceIDs


class DataGenerator:
    """
    Shared test data generation.
    Eliminates duplication across features/xxx/test_data/ files.
    All values reference BoundaryValues from config/test_data.py.
    """

    @staticmethod
    def unique_email(prefix: str = "test") -> str:
        """Generate a unique mailinator email: {prefix}+{timestamp}@mailinator.com"""
        return f"{prefix}+{int(time.time())}@mailinator.com"

    @staticmethod
    def unique_phone() -> str:
        """Valid Indonesian mobile number format — last 9 digits of timestamp."""
        return str(int(time.time()))[-9:]

    @staticmethod
    def unique_fullname() -> str:
        """Generate a unique test user fullname: Test User {timestamp}"""
        return f"Test User {int(time.time())}"

    @staticmethod
    def boundary_string(length: int, char: str = "A") -> str:
        """Generate a string of exact length for boundary tests."""
        return char * length

    @staticmethod
    def valid_register_payload(suffix=None) -> dict:
        """
        Complete valid registration payload using timestamp-based unique values.
        Uses BoundaryValues for any length constraints.
        Pass suffix to pin the timestamp (useful for create_approved_user flows).
        """
        ts = suffix or int(time.time())
        return {
            "fullname":           f"Test User {ts}",
            "email":              f"testregister+{ts}@mailinator.com",
            "phone_number":       str(ts)[-9:],
            "phone_country_code": "ID",
            "linkedin":           f"https://linkedin.com/in/testuser{ts}",
        }

    @staticmethod
    def valid_onboarding_payload() -> dict:
        """
        Complete valid onboarding payload.
        Uses ReferenceIDs from config/test_config.py for all IDs — never hardcoded.
        """
        return {
            "full_name":             "Test Onboard API",
            "current_role":          "QA Engineer",
            "company_organisation":  "Hono Testing Inc",
            "nationality_id":        ReferenceIDs.INDONESIA,
            "city_id":               ReferenceIDs.JAKARTA_PUSAT,
            "industry_ids":          [ReferenceIDs.INDUSTRY_ACCOUNTING, ReferenceIDs.INDUSTRY_ADVERTISING],
            "business_area_ids":     [ReferenceIDs.BUSINESS_ACCOUNTING, ReferenceIDs.BUSINESS_ADVERTISING],
            "personal_interest_ids": [ReferenceIDs.INTEREST_ADVENTURE, ReferenceIDs.INTEREST_ANIMATION],
            "social_cause_ids":      [ReferenceIDs.CAUSE_EDUCATION, ReferenceIDs.CAUSE_HEALTHCARE],
        }

    @staticmethod
    def invalid_email_variants() -> list[str]:
        """List of invalid email formats for negative tests."""
        return [
            "bad-email",
            "test@",
            "@missing-local.com",
            "missing-at.com",
            "spaces in@email.com",
            "double@@email.com",
            "",
        ]

    @staticmethod
    def invalid_phone_variants() -> list[str]:
        """List of invalid phone formats for negative tests, using BoundaryValues for lengths."""
        return [
            DataGenerator.boundary_string(BoundaryValues.MIN_PHONE_DIGITS, "1"),   # too short
            DataGenerator.boundary_string(BoundaryValues.MAX_PHONE_DIGITS, "1"),   # too long
            "abcdefghi",   # non-numeric
            "",            # empty
        ]

    @staticmethod
    def sql_injection_strings() -> list[str]:
        """Known SQL injection patterns for security tests."""
        return [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "\" OR \"1\"=\"1",
            "1; SELECT * FROM users",
            "' UNION SELECT NULL--",
        ]

    @staticmethod
    def xss_strings() -> list[str]:
        """Known XSS patterns for security tests."""
        return [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
            "';alert('xss')//",
        ]

"""
Onboarding API Test Data — PUT /v1/users/onboarding
Reference IDs from hono_dev database.
"""


class OnboardingTestData:
    # ── Country & City ────────────────────────────────────────────────
    INDONESIA_ID        = 102
    JAKARTA_PUSAT_ID    = 154470
    JAKARTA_SELATAN_ID  = 154471

    # ── Industries (id: name) ─────────────────────────────────────────
    INDUSTRY_ACCOUNTING = 1   # Accounting
    INDUSTRY_ADVERTISING = 2  # Advertising & Marketing
    INDUSTRY_AEROSPACE  = 3   # Aerospace & Defense

    # ── Business Areas ────────────────────────────────────────────────
    BUSINESS_ACCOUNTING = 1   # Accounting and Audit
    BUSINESS_ADVERTISING = 2  # Advertising and Marketing

    # ── Personal Interests ────────────────────────────────────────────
    INTEREST_ADVENTURE  = 1   # Adventure Travel
    INTEREST_ANIMATION  = 2   # Animation and Motion Graphics

    # ── Social Causes ─────────────────────────────────────────────────
    CAUSE_EDUCATION     = 1   # Accessible Education
    CAUSE_HEALTHCARE    = 2   # Affordable Healthcare

    # ── Valid payload ─────────────────────────────────────────────────
    @classmethod
    def valid_payload(cls) -> dict:
        return {
            "full_name":             "Test Onboard API",
            "current_role":          "QA Engineer",
            "company_organisation":  "Hono Testing Inc",
            "nationality_id":        cls.INDONESIA_ID,
            "city_id":               cls.JAKARTA_PUSAT_ID,
            "industry_ids":          [cls.INDUSTRY_ACCOUNTING, cls.INDUSTRY_ADVERTISING],
            "business_area_ids":     [cls.BUSINESS_ACCOUNTING, cls.BUSINESS_ADVERTISING],
            "personal_interest_ids": [cls.INTEREST_ADVENTURE, cls.INTEREST_ANIMATION],
            "social_cause_ids":      [cls.CAUSE_EDUCATION, cls.CAUSE_HEALTHCARE],
        }

    # ── Edge case payloads ────────────────────────────────────────────
    @classmethod
    def minimal_payload(cls) -> dict:
        """Minimum required fields only."""
        return {
            "full_name":             "Minimal User",
            "current_role":          "Engineer",
            "company_organisation":  "Test Corp",
            "nationality_id":        cls.INDONESIA_ID,
            "city_id":               cls.JAKARTA_PUSAT_ID,
            "industry_ids":          [cls.INDUSTRY_ACCOUNTING],
            "business_area_ids":     [cls.BUSINESS_ACCOUNTING],
            "personal_interest_ids": [cls.INTEREST_ADVENTURE],
            "social_cause_ids":      [cls.CAUSE_EDUCATION],
        }

    @classmethod
    def max_industries_payload(cls) -> dict:
        """Max 2 industries."""
        p = cls.valid_payload()
        p["industry_ids"] = [1, 2]
        return p

    @classmethod
    def over_max_industries_payload(cls) -> dict:
        """Over max — 3 industries (should be blocked)."""
        p = cls.valid_payload()
        p["industry_ids"] = [1, 2, 3]
        return p

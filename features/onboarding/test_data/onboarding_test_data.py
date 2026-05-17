"""
Onboarding API Test Data — PUT /v1/users/onboarding
Reference IDs from hono_dev database via ReferenceIDs config.
"""
from config.test_config import ReferenceIDs
from skills.data.data_generator import DataGenerator


class OnboardingTestData:
    # ── Country & City — aliases to ReferenceIDs (single source of truth) ────
    INDONESIA_ID        = ReferenceIDs.INDONESIA
    JAKARTA_PUSAT_ID    = ReferenceIDs.JAKARTA_PUSAT
    JAKARTA_SELATAN_ID  = ReferenceIDs.JAKARTA_SELATAN

    # ── Industries ────────────────────────────────────────────────────
    INDUSTRY_ACCOUNTING  = ReferenceIDs.INDUSTRY_ACCOUNTING
    INDUSTRY_ADVERTISING = ReferenceIDs.INDUSTRY_ADVERTISING
    INDUSTRY_AEROSPACE   = ReferenceIDs.INDUSTRY_AEROSPACE

    # ── Business Areas ────────────────────────────────────────────────
    BUSINESS_ACCOUNTING  = ReferenceIDs.BUSINESS_ACCOUNTING
    BUSINESS_ADVERTISING = ReferenceIDs.BUSINESS_ADVERTISING

    # ── Personal Interests ────────────────────────────────────────────
    INTEREST_ADVENTURE  = ReferenceIDs.INTEREST_ADVENTURE
    INTEREST_ANIMATION  = ReferenceIDs.INTEREST_ANIMATION

    # ── Social Causes ─────────────────────────────────────────────────
    CAUSE_EDUCATION  = ReferenceIDs.CAUSE_EDUCATION
    CAUSE_HEALTHCARE = ReferenceIDs.CAUSE_HEALTHCARE

    # ── Valid payload ─────────────────────────────────────────────────
    @classmethod
    def valid_payload(cls) -> dict:
        """Complete valid onboarding payload. Delegates to DataGenerator."""
        return DataGenerator.valid_onboarding_payload()

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
        p["industry_ids"] = [cls.INDUSTRY_ACCOUNTING, cls.INDUSTRY_ADVERTISING]
        return p

    @classmethod
    def over_max_industries_payload(cls) -> dict:
        """Over max — 3 industries (should be blocked by API)."""
        p = cls.valid_payload()
        p["industry_ids"] = [cls.INDUSTRY_ACCOUNTING, cls.INDUSTRY_ADVERTISING, cls.INDUSTRY_AEROSPACE]
        return p

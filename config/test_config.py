"""
Centralized Test Configuration — single source of truth untuk semua URLs dan config.
Usage: from config.test_config import TestConfig, APIEndpoints, Timeouts, ReferenceIDs
"""
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")


class TestConfig:
    # ── Web URLs ──────────────────────────────────────────────────────
    WEB_APP_URL     = os.getenv("WEB_APP_URL",     "https://app-dev.thehono.com")
    CMS_URL         = os.getenv("CMS_URL",          "https://cms-dev.thehono.com")

    # ── API URLs ──────────────────────────────────────────────────────
    API_URL         = os.getenv("HONO_API_URL",     "https://api-dev.thehono.com")
    API_KEY         = os.getenv("HONO_API_KEY",     "")

    # ── Mobile ────────────────────────────────────────────────────────
    ANDROID_PACKAGE  = os.getenv("ANDROID_APP_PACKAGE",  "app.thehono.development")
    ANDROID_ACTIVITY = os.getenv("ANDROID_APP_ACTIVITY", "com.example.hono_app.MainActivity")
    ANDROID_DEVICE   = os.getenv("ANDROID_DEVICE_NAME",  "")
    ANDROID_VERSION  = os.getenv("ANDROID_PLATFORM_VERSION", "12.0")
    ANDROID_APK      = os.getenv("ANDROID_APK_PATH",     None)

    # ── Timeouts ──────────────────────────────────────────────────────
    DEFAULT_TIMEOUT  = 10000   # ms — Playwright
    API_TIMEOUT      = 30      # seconds — httpx
    MOBILE_TIMEOUT   = 10      # seconds — Appium

    # ── Environment ───────────────────────────────────────────────────
    ENV              = os.getenv("TEST_ENV", "staging")  # staging | production

    # ── Locator file paths ────────────────────────────────────────────
    LOGIN_LOCATORS_WEB     = "features/login/locators/web/login_web_locators.py"
    LOGIN_LOCATORS_MOBILE  = "features/login/locators/mobile/login_android_locators.py"

    @classmethod
    def get_base_url(cls, platform: str = "web") -> str:
        mapping = {
            "web":     cls.WEB_APP_URL,
            "cms":     cls.CMS_URL,
            "api":     cls.API_URL,
        }
        return mapping.get(platform, cls.WEB_APP_URL)


class APIEndpoints:
    """All /v1/ paths used across test files — never hardcode these in test files."""

    # ── Auth ──────────────────────────────────────────────────────────
    LOGIN           = "/v1/users/login"
    REGISTER        = "/v1/users/register"

    # ── User self ─────────────────────────────────────────────────────
    ME              = "/v1/users/me"
    ME_ACCOUNT      = "/v1/users/me/account"
    ME_EMAIL        = "/v1/users/me/email"
    ME_PASSWORD     = "/v1/users/me/password"
    ONBOARDING      = "/v1/users/onboarding"
    VERIFY_EMAIL    = "/v1/users/verify-email"

    # ── CMS ───────────────────────────────────────────────────────────
    USERS_LIST      = "/v1/users"

    @staticmethod
    def approve(user_id: str) -> str:
        return f"/v1/users/{user_id}/approve"

    @staticmethod
    def reject(user_id: str) -> str:
        return f"/v1/users/{user_id}/reject"

    # ── Content ───────────────────────────────────────────────────────
    POSTS           = "/v1/posts"
    SEARCH_POSTS    = "/v1/search/posts"


class Timeouts:
    """All timeout values in one place — seconds for httpx/Appium, ms for Playwright."""

    API_REQUEST     = 30      # seconds — httpx requests
    API_SLA_MS      = 3000    # ms — max acceptable API response time
    PAGE_LOAD       = 10      # seconds — Playwright page.goto
    PAGE_LOAD_MS    = 10000   # ms — Playwright selector waits
    ANIMATION       = 3       # seconds — wait after UI transitions
    APPIUM_IMPLICIT = 8       # seconds — Appium implicit wait
    POLLING         = 2       # seconds — short polling loop delay
    LOGIN_WAIT      = 8       # seconds — after login before asserting feed


class ReferenceIDs:
    """Country/city/industry IDs from hono_dev database — from OnboardingTestData."""

    # ── Country (nationality_id) ──────────────────────────────────────
    INDONESIA           = 102

    # ── City (city_id) ────────────────────────────────────────────────
    JAKARTA_PUSAT       = 154470
    JAKARTA_SELATAN     = 154471

    # ── Industries (industry_ids) ─────────────────────────────────────
    INDUSTRY_ACCOUNTING     = 1
    INDUSTRY_ADVERTISING    = 2
    INDUSTRY_AEROSPACE      = 3

    # ── Business Areas (business_area_ids) ────────────────────────────
    BUSINESS_ACCOUNTING     = 1
    BUSINESS_ADVERTISING    = 2

    # ── Personal Interests (personal_interest_ids) ────────────────────
    INTEREST_ADVENTURE      = 1
    INTEREST_ANIMATION      = 2

    # ── Social Causes (social_cause_ids) ──────────────────────────────
    CAUSE_EDUCATION         = 1
    CAUSE_HEALTHCARE        = 2

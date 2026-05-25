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

    # ── Token / Auth flow ─────────────────────────────────────────────────
    AUTH_REFRESH            = "/v1/auth/refresh"
    AUTH_FORGOT_PASSWORD    = "/v1/auth/forgot-password"
    AUTH_RESET_PASSWORD     = "/v1/auth/reset-password"
    AUTH_VALIDATE_RESET     = "/v1/auth/reset-password/validate"
    AUTH_RESEND_EMAIL_VERIF = "/v1/auth/email/verification"

    # ── User self (extended) ──────────────────────────────────────────────
    ME_DEACTIVATE    = "/v1/users/me/deactivate"
    MENTIONABLE      = "/v1/users/mentionable"

    # ── Feed ─────────────────────────────────────────────────────────────
    FEED             = "/v1/feed"
    TOPICS           = "/v1/topics"

    # ── Content ───────────────────────────────────────────────────────────
    POSTS            = "/v1/posts"
    MEDIA_UPLOAD     = "/v1/media/upload"
    SEARCH_POSTS     = "/v1/search/posts"
    SEARCH_USERS     = "/v1/search/users"
    SEARCH_TYPEAHEAD = "/v1/search/typeahead"

    # ── Network ───────────────────────────────────────────────────────────
    NETWORK_FOLLOWERS   = "/v1/network/followers"
    NETWORK_FOLLOWING   = "/v1/network/following"
    NETWORK_SUGGESTIONS = "/v1/network/suggestions"

    # ── Privacy / Social ─────────────────────────────────────────────────
    SETTINGS_ACCOUNTS_BLOCK  = "/v1/settings/accounts/block"
    SETTINGS_ACCOUNTS_MUTE   = "/v1/settings/accounts/mute"
    SETTINGS_ACCOUNT_COUNTS  = "/v1/settings/account/counts"
    SETTINGS_ACCOUNT_LIST    = "/v1/settings/account/list"

    # ── Settings ─────────────────────────────────────────────────────────
    SETTINGS_TOGGLE       = "/v1/settings/toggle"
    SETTINGS_OPTION       = "/v1/settings/option"
    SETTINGS_MSG_PREFERENCE = "/v1/settings/message-preference"
    SETTINGS_NOTIF_PREFS  = "/v1/settings/notification-preferences"

    # ── Master data ───────────────────────────────────────────────────────
    MASTER_INDUSTRIES         = "/v1/master/industries"
    MASTER_BUSINESS_AREAS     = "/v1/master/business-areas"
    MASTER_PERSONAL_INTERESTS = "/v1/master/personal-interests"
    MASTER_SOCIAL_CAUSES      = "/v1/master/social-causes"
    MASTER_COUNTRIES          = "/v1/master/countries"
    MASTER_CITIES             = "/v1/master/cities"
    MASTER_RELATIONSHIP_TYPES = "/v1/master/relationship-types"

    # ── Reports ───────────────────────────────────────────────────────────
    REPORTS          = "/v1/reports"

    # ── Public (no auth) ─────────────────────────────────────────────────
    PUBLIC_COUNTRIES = "/v1/public/countries"
    PUBLIC_CITIES    = "/v1/public/cities"

    # ── App config ────────────────────────────────────────────────────────
    APP_CONFIG       = "/v1/app-config"

    # ── Path-based static helpers ─────────────────────────────────────────

    @staticmethod
    def post_detail(post_id: str) -> str:
        return f"/v1/posts/{post_id}"

    @staticmethod
    def post_visibility(post_id: str) -> str:
        return f"/v1/posts/{post_id}/visibility"

    @staticmethod
    def post_not_interested(post_id: str) -> str:
        return f"/v1/posts/{post_id}/not-interested"

    @staticmethod
    def post_report(post_id: str) -> str:
        return f"/v1/posts/{post_id}/report"

    @staticmethod
    def post_hide(post_id: str) -> str:
        return f"/v1/posts/{post_id}/hide"

    @staticmethod
    def post_view(post_id: str) -> str:
        return f"/v1/posts/{post_id}/view"

    # ── Admin Moderation ─────────────────────────────────────────────────────
    ADMIN_REPORTS_POSTS = "/v1/admin/reports/posts"

    @staticmethod
    def admin_reports_post_hide(post_id: str) -> str:
        return f"/v1/admin/reports/posts/{post_id}/hide"

    @staticmethod
    def admin_reports_post_unhide(post_id: str) -> str:
        return f"/v1/admin/reports/posts/{post_id}/unhide"

    @staticmethod
    def admin_reports_post_dismiss(post_id: str) -> str:
        return f"/v1/admin/reports/posts/{post_id}/dismiss"

    # ── Search history ────────────────────────────────────────────────────────
    SEARCH_RECENT = "/v1/search/recent"

    @staticmethod
    def search_recent_delete(entry_id: str) -> str:
        return f"/v1/search/recent/{entry_id}"

    @staticmethod
    def user_posts(user_id: str) -> str:
        return f"/v1/users/{user_id}/posts"

    @staticmethod
    def user_media(user_id: str) -> str:
        return f"/v1/users/{user_id}/media"

    @staticmethod
    def user_follow(user_id: str) -> str:
        return f"/v1/users/{user_id}/follow"

    @staticmethod
    def user_mute_by_id(user_id: str) -> str:
        return f"/v1/users/{user_id}/mute"

    @staticmethod
    def storage_presign(key: str) -> str:
        return f"/v1/storage/presign/{key}"


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

    # ── Topics (topic_ids) — verified from Dev environment ───────────
    TOPIC_PODCASTING            = 119
    TOPIC_CAREER                = 121
    TOPIC_LEADERSHIP            = 125
    TOPIC_SOCIAL                = 1
    TOPIC_COMMUNITY_ENGAGEMENT  = 5

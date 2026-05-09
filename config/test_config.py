"""
Centralized Test Configuration — single source of truth untuk semua URLs dan config.
Usage: from config.test_config import TestConfig

Tidak perlu lagi hardcode URL di setiap test file.
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
        """Get base URL by platform."""
        mapping = {
            "web":     cls.WEB_APP_URL,
            "cms":     cls.CMS_URL,
            "api":     cls.API_URL,
        }
        return mapping.get(platform, cls.WEB_APP_URL)

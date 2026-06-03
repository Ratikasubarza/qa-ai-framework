"""
OnboardingScreen — Android screen object for the Hono 10-step onboarding flow.

Encapsulates all driver interactions for every onboarding screen.
The location screen requires ADB coordinate taps (Flutter picker limitations);
those are passed in as a callable so the screen object stays driver-only.

Usage:
    screen = OnboardingScreen(driver)
    screen.tap_personalize()
    screen.enter_fullname("Jane Doe").hide_keyboard().tap_continue()
    screen.assert_on_feed()
"""
from appium.webdriver.common.appiumby import AppiumBy
from platforms.mobile.screens.base_mobile_screen import BaseMobileScreen
from features.onboarding.locators.mobile.onboarding_android_locators import (
    FULLNAME_INDEX,
    ROLE_INDEX, COMPANY_INDEX,
    DEFAULT_COUNTRY, DEFAULT_CITY,
    COUNTRY_FIELD_X, COUNTRY_FIELD_Y,
    CITY_FIELD_X, CITY_FIELD_Y,
    INDUSTRIES_FIELD_X, INDUSTRIES_FIELD_Y,
    SUBMIT_BTN, SKIP_BTN, GO_TO_HOMEPAGE_BTN,
    PERSONALIZE_BTN, FEED_HOME_TAB,
)


class OnboardingScreen(BaseMobileScreen):

    # ── Screen 1: Welcome ─────────────────────────────────────────────────────

    def tap_personalize(self) -> "OnboardingScreen":
        self.driver.find(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().descriptionContains("{PERSONALIZE_BTN}")',
            timeout=8,
        ).click()
        return self

    def is_on_onboarding(self) -> bool:
        return PERSONALIZE_BTN in self.get_page_source()

    # ── Screen 2: Full Name ───────────────────────────────────────────────────

    def enter_fullname(self, name: str) -> "OnboardingScreen":
        self.fill_by_index(FULLNAME_INDEX, name, description="Full name field")
        return self

    # ── Screen 3: Work ────────────────────────────────────────────────────────

    def enter_role(self, role: str) -> "OnboardingScreen":
        self.fill_by_index(ROLE_INDEX, role, description="Role field")
        return self

    def enter_company(self, company: str) -> "OnboardingScreen":
        self.fill_by_index(COMPANY_INDEX, company, description="Company field")
        return self

    # ── Screen 4: Location (requires adb_tap for Flutter picker) ─────────────

    def enter_search_field(self, text: str) -> "OnboardingScreen":
        """Type into the first visible EditText — used for country/city picker search."""
        self.fill_by_index(0, text, description="Search field")
        return self

    def tap_country(self, country: str = DEFAULT_COUNTRY) -> "OnboardingScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, country, timeout=5).click()
        return self

    def tap_city(self, city: str = DEFAULT_CITY) -> "OnboardingScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, city, timeout=3).click()
        return self

    # ── Screen 5–8: Multi-select pickers ─────────────────────────────────────

    def tap_item_by_desc(self, desc: str, timeout: int = 5) -> "OnboardingScreen":
        """Tap any item by accessibility ID, falling back to descriptionContains."""
        try:
            self.driver.find(AppiumBy.ACCESSIBILITY_ID, desc, timeout=timeout).click()
        except Exception:
            self.driver.find(
                AppiumBy.ANDROID_UIAUTOMATOR,
                f'new UiSelector().descriptionContains("{desc}")',
                timeout=timeout,
            ).click()
        return self

    def tap_save(self, timeout: int = 5) -> "OnboardingScreen":
        self.driver.find(
            AppiumBy.ANDROID_UIAUTOMATOR,
            'new UiSelector().descriptionContains("Save")',
            timeout=timeout,
        ).click()
        return self

    # ── Navigation buttons (shared across screens) ────────────────────────────

    def tap_continue(self, timeout: int = 5) -> "OnboardingScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, "Continue", timeout=timeout).click()
        return self

    def tap_submit(self, timeout: int = 5) -> "OnboardingScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, SUBMIT_BTN, timeout=timeout).click()
        return self

    def tap_skip(self, timeout: int = 8) -> "OnboardingScreen":
        self.driver.find(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().descriptionContains("{SKIP_BTN}")',
            timeout=timeout,
        ).click()
        return self

    def tap_go_to_homepage(self, timeout: int = 8) -> "OnboardingScreen":
        self.driver.find(AppiumBy.ACCESSIBILITY_ID, GO_TO_HOMEPAGE_BTN, timeout=timeout).click()
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def is_on_feed(self) -> bool:
        return self.driver.is_element_present(AppiumBy.ACCESSIBILITY_ID, FEED_HOME_TAB, timeout=5)

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_on_onboarding(self) -> "OnboardingScreen":
        assert self.driver.is_element_present(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiSelector().descriptionContains("{PERSONALIZE_BTN}")',
            timeout=10,
        ), "Expected onboarding welcome screen but not found"
        return self

    def assert_on_feed(self) -> "OnboardingScreen":
        assert self.driver.is_element_present(
            AppiumBy.ACCESSIBILITY_ID, FEED_HOME_TAB, timeout=10
        ), "Expected feed screen (Home tab) after onboarding but not found"
        return self

    # ── Full flow helper ─────────────────────────────────────────────────────

    def complete_full_flow(self, adb_tap) -> "OnboardingScreen":
        """
        Complete all 8 onboarding data screens through to feed.
        adb_tap: callable(x, y) — required for Flutter coordinate pickers.
        """
        from features.onboarding.locators.mobile.onboarding_android_locators import (
            DEFAULT_COUNTRY, DEFAULT_CITY,
            COUNTRY_FIELD_X, COUNTRY_FIELD_Y,
            CITY_FIELD_X, CITY_FIELD_Y,
            INDUSTRIES_FIELD_X, INDUSTRIES_FIELD_Y,
        )

        # Screen 2: Full name
        self.enter_fullname("Test Onboard User").hide_keyboard().tap_continue()
        self.wait_for_text_in_source("QA Engineer") or self.wait_for_text_in_source("Work")

        # Screen 3: Work
        self.enter_role("QA Engineer").enter_company("Hono Testing Inc").hide_keyboard().tap_continue()
        self.wait_for_text_in_source("Location")

        # Screen 4: Location — Flutter picker requires coordinate tap via ADB
        adb_tap(COUNTRY_FIELD_X, COUNTRY_FIELD_Y)
        self.wait_for_text_in_source(DEFAULT_COUNTRY)
        self.enter_search_field(DEFAULT_COUNTRY)
        self.wait_for_text_in_source(DEFAULT_COUNTRY)
        self.tap_country(DEFAULT_COUNTRY)
        self.wait_for_text_in_source("Jakarta")
        adb_tap(CITY_FIELD_X, CITY_FIELD_Y)
        self.wait_for_text_in_source("Jakarta")
        self.enter_search_field("Jakarta")
        self.wait_for_text_in_source(DEFAULT_CITY)
        self.tap_city(DEFAULT_CITY)
        self.wait_for_text_in_source("Industries")
        self.tap_continue()
        self.wait_for_text_in_source("Industries")

        # Screen 5: Industries
        adb_tap(INDUSTRIES_FIELD_X, INDUSTRIES_FIELD_Y)
        self.wait_for_text_in_source("Accounting")
        self.tap_item_by_desc("Accounting").tap_item_by_desc("Agriculture")
        self.tap_save()
        self.wait_for_text_in_source("Continue")
        self.tap_continue()
        self.wait_for_text_in_source("Business")

        # Screen 6: Business Areas
        (
            self.tap_item_by_desc("Accounting and Audit")
            .tap_item_by_desc("Advertising and Marketing")
            .tap_continue()
        )
        self.wait_for_text_in_source("Personal Interests")

        # Screen 7: Personal Interests
        self.tap_item_by_desc("Entrepreneurship").tap_item_by_desc("Cycling").tap_continue()
        self.wait_for_text_in_source("Social Causes")

        # Screen 8: Social Causes → Submit
        self.tap_item_by_desc("Clean Energy").tap_item_by_desc("Education Access").tap_submit()
        self.wait_for_text_in_source("Skip")

        # Screen 9: Skip profile picture
        self.tap_skip()
        self.wait_for_text_in_source(GO_TO_HOMEPAGE_BTN)

        # Screen 10: Go to homepage
        self.tap_go_to_homepage()
        self.wait_for_text_in_source("Home")

        return self

"""
FeedPage — Page Object for the Hono feed with topic filters.

Usage:
    feed = FeedPage(page).open()
    feed.select_topic("Technology")
    feed.assert_posts_visible()
    feed.assert_each_post_has_tag("Technology")
"""
from playwright.sync_api import Page
from platforms.web.pages.base_page import BasePage
from features.feed_search_and_filter.locators.web.feed_web_locators import (
    FEED_URL, TOPIC_BUTTON, FILTER_BUTTON,
    POST, POST_TAG, EMPTY_STATE,
    TOPIC_SEARCH_INPUT, TOPIC_SEARCH_SUBMIT,
)


class FeedPage(BasePage):
    URL = FEED_URL

    def __init__(self, page: Page):
        super().__init__(page)

    # ── Navigation ────────────────────────────────────────────────────────────

    def open(self) -> "FeedPage":
        self.goto()
        return self

    # ── Actions ───────────────────────────────────────────────────────────────

    def select_topic(self, topic: str) -> "FeedPage":
        self.click(TOPIC_BUTTON(topic), description=f"Topic filter: {topic}")
        return self

    def select_filter(self, filter_name: str) -> "FeedPage":
        self.click(FILTER_BUTTON(filter_name), description=f"Filter: {filter_name}")
        return self

    def search_topic(self, query: str) -> "FeedPage":
        self.fill(TOPIC_SEARCH_INPUT, query, description="Topic search input")
        self.click(TOPIC_SEARCH_SUBMIT, description="Topic search submit")
        return self

    def rapid_click_filter(self, filter_name: str, times: int) -> "FeedPage":
        for _ in range(times):
            self.page.locator(FILTER_BUTTON(filter_name)).click()
        return self

    def focus_filter_and_press(self, filter_name: str, key: str) -> "FeedPage":
        self.page.locator(FILTER_BUTTON(filter_name)).focus()
        self.page.keyboard.press(key)
        return self

    # ── State queries ─────────────────────────────────────────────────────────

    def get_post_count(self) -> int:
        return self.page.locator(POST).count()

    def get_post_tag_text(self, index: int) -> str:
        return (
            self.page.locator(POST).nth(index).locator(POST_TAG).text_content() or ""
        )

    def is_empty_state_visible(self) -> bool:
        return self.is_visible(EMPTY_STATE)

    def get_empty_state_text(self) -> str:
        if self.is_empty_state_visible():
            return self.get_text(EMPTY_STATE)
        return ""

    def is_filter_active(self, filter_name: str) -> bool:
        return self.page.locator(FILTER_BUTTON(filter_name)).is_checked()

    # ── Assertions ────────────────────────────────────────────────────────────

    def assert_posts_visible(self) -> "FeedPage":
        self.wait_for(POST)
        return self

    def assert_post_count_greater_than(self, minimum: int, message: str = "") -> "FeedPage":
        count = self.get_post_count()
        assert count > minimum, message or f"Expected more than {minimum} posts, got {count}"
        return self

    def assert_each_post_has_tag(self, tag: str) -> "FeedPage":
        count = self.get_post_count()
        for i in range(count):
            text = self.get_post_tag_text(i)
            assert tag in text, f"Post {i} tag '{text}' does not contain '{tag}'"
        return self

    def assert_empty_state_contains(self, text: str) -> "FeedPage":
        self.wait_for(EMPTY_STATE)
        actual = self.get_empty_state_text()
        assert text in actual, f"Empty state message '{actual}' does not contain '{text}'"
        return self

    def assert_filter_active(self, filter_name: str) -> "FeedPage":
        assert self.is_filter_active(filter_name), (
            f"Filter '{filter_name}' is not active after reload"
        )
        return self

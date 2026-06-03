"""
Feed Search & Filter Web Tests — Hono feed topic filter scenarios.
Target: app-dev.thehono.com/feed
"""
import allure
import pytest
from playwright.sync_api import Page

from features.feed_search_and_filter.pages.web.feed_page import FeedPage

pytestmark = [allure.feature("Feed Search and Filter"), allure.suite("Web")]


@pytest.mark.parametrize("topic", ["Technology"])
def test_TC_FEED_001_technology_filter(page: Page, topic: str):
    """
    TC-FEED-001 | E2E | Selecting Technology topic shows only Technology posts
    """
    (
        FeedPage(page).open()
        .select_topic(topic)
        .assert_posts_visible()
        .assert_post_count_greater_than(0, f"Expected at least one {topic} post")
        .assert_each_post_has_tag(topic)
    )


def test_TC_FEED_002_heart_topic_instant_update(page: Page):
    """
    TC-FEED-002 | Smoke | Selecting Heart topic updates feed without page reload
    """
    feed = FeedPage(page).open()
    initial_url = page.url
    (
        feed.select_filter("Heart")
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No Heart posts found")
        .assert_each_post_has_tag("Heart")
    )
    assert page.url == initial_url, "Page reloaded after selecting Heart filter"


def test_TC_FEED_003_all_topics_filter(page: Page):
    """
    TC-FEED-003 | E2E | Selecting All Topics shows all posts
    """
    (
        FeedPage(page).open()
        .select_filter("All Topics")
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No posts found after selecting All Topics")
    )


def test_TC_FEED_004_travel_empty_state(page: Page):
    """
    TC-FEED-004 | Regression | Travel topic with no posts shows empty state UI
    """
    (
        FeedPage(page).open()
        .select_filter("Travel")
        .assert_empty_state_contains("No posts available")
    )


def test_TC_FEED_005_sports_filter_persistence(page: Page):
    """
    TC-FEED-005 | E2E | Sports filter remains active after page refresh
    """
    feed = FeedPage(page).open().select_filter("Sports")
    feed.page.reload()
    (
        feed.assert_filter_active("Sports")
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No Sports posts after refresh")
        .assert_each_post_has_tag("Sports")
    )


def test_TC_FEED_006_injection_attempt_blocked(page: Page):
    """
    TC-FEED-006 | Negative | XSS injection in topic search does not execute script
    """
    (
        FeedPage(page).open()
        .search_topic("<script>alert(1)</script>")
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No posts after injection attempt")
    )
    assert not page.is_visible('text=1'), "Alert dialog appeared after injection — XSS not blocked"


def test_TC_FEED_007_art_topic_rapid_clicks(page: Page):
    """
    TC-FEED-007 | Regression | Rapid clicks on Art topic updates feed without crash
    """
    (
        FeedPage(page).open()
        .rapid_click_filter("Art", times=10)
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No Art posts after rapid clicks")
        .assert_each_post_has_tag("Art")
    )


def test_TC_FEED_008_science_keyboard_navigation(page: Page):
    """
    TC-FEED-008 | Regression | Keyboard navigation to Science topic updates feed
    """
    (
        FeedPage(page).open()
        .focus_filter_and_press("Science", "Enter")
        .assert_posts_visible()
        .assert_post_count_greater_than(0, "No Science posts after keyboard navigation")
        .assert_each_post_has_tag("Science")
    )

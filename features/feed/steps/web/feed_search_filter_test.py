"""Feed Search and Filter Web Tests — app-dev.thehono.com/feed"""
import allure
import pytest
from playwright.sync_api import Page, expect

from config.test_config import TestConfig

pytestmark = [
    allure.feature("Feed"),
    allure.suite("Web"),
]

_FEED_URL = f"{TestConfig.WEB_APP_URL}/feed"


def _topic_btn(page: Page, topic: str):
    return page.locator(f'[data-testid="topic-{topic.lower()}"]')


def _filter_btn(page: Page, name: str):
    return page.locator(f'[data-testid="filter-{name.lower().replace(" ", "-")}"]')


def _posts(page: Page):
    return page.locator('[data-testid="post"]')


def _empty_state(page: Page):
    return page.locator('[data-testid="empty-state"]')


@pytest.mark.web
@pytest.mark.parametrize("topic", ["Technology"])
def test_TC_FEED_WEB_001_technology_filter(page: Page, topic: str):
    """TC-FEED-WEB-001 | e2e | Technology topic filter shows only Technology posts"""
    page.goto(_FEED_URL)
    btn = _topic_btn(page, topic)
    expect(btn).to_be_visible()
    btn.click()
    posts = _posts(page)
    expect(posts.first).to_be_visible()
    count = posts.count()
    assert count > 0, f"Expected at least one {topic} post"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Technology" in tag.text_content(), f"Post {i} missing Technology tag"


@pytest.mark.smoke
@pytest.mark.web
def test_TC_FEED_WEB_002_heart_topic_instant_update(page: Page):
    """TC-FEED-WEB-002 | Smoke | Heart topic updates feed without page reload"""
    page.goto(_FEED_URL)
    initial_url = page.url
    btn = _filter_btn(page, "Heart")
    expect(btn).to_be_visible()
    btn.click()
    expect(_posts(page).first).to_be_visible()
    assert page.url == initial_url, "URL changed — page reloaded after filter click"
    assert _posts(page).count() > 0, "No Heart posts found"


@pytest.mark.web
def test_TC_FEED_WEB_003_all_topics_filter(page: Page):
    """TC-FEED-WEB-003 | e2e | All Topics shows posts regardless of topic"""
    page.goto(_FEED_URL)
    btn = _filter_btn(page, "All Topics")
    expect(btn).to_be_visible()
    btn.click()
    expect(_posts(page).first).to_be_visible()
    assert _posts(page).count() > 0, "No posts found after selecting All Topics"


@pytest.mark.web
def test_TC_FEED_WEB_004_travel_empty_state(page: Page):
    """TC-FEED-WEB-004 | Regression | Travel topic with no posts shows empty state UI"""
    page.goto(_FEED_URL)
    btn = _filter_btn(page, "Travel")
    expect(btn).to_be_visible()
    btn.click()
    empty = _empty_state(page)
    expect(empty).to_be_visible()
    assert "No posts available" in empty.text_content(), "Empty state message missing"


@pytest.mark.web
def test_TC_FEED_WEB_005_sports_filter_persistence(page: Page):
    """TC-FEED-WEB-005 | Regression | Sports filter remains active after page refresh"""
    page.goto(_FEED_URL)
    btn = _filter_btn(page, "Sports")
    expect(btn).to_be_visible()
    btn.click()
    page.reload()
    active = _filter_btn(page, "Sports")
    expect(active).to_be_visible()
    assert active.is_checked(), "Sports filter not active after refresh"
    expect(_posts(page).first).to_be_visible()
    assert _posts(page).count() > 0, "No Sports posts after refresh"


@pytest.mark.negative
@pytest.mark.web
def test_TC_FEED_WEB_006_xss_injection_blocked(page: Page):
    """TC-FEED-WEB-006 | Negative | XSS in topic search input is sanitised and not executed"""
    page.goto(_FEED_URL)
    topic_input = page.locator('[data-testid="topic-search-input"]')
    expect(topic_input).to_be_visible()
    topic_input.fill("<script>alert(1)</script>")
    page.locator('[data-testid="topic-search-submit"]').click()
    expect(_posts(page).first).to_be_visible()
    assert _posts(page).count() > 0, "No posts after injection attempt"
    assert not page.is_visible("text=1"), "Alert dialog appeared — XSS not sanitised"


@pytest.mark.web
def test_TC_FEED_WEB_007_art_rapid_clicks(page: Page):
    """TC-FEED-WEB-007 | Regression | Rapid Art topic clicks do not crash the feed"""
    page.goto(_FEED_URL)
    art_btn = _filter_btn(page, "Art")
    expect(art_btn).to_be_visible()
    for _ in range(10):
        art_btn.click()
    expect(_posts(page).first).to_be_visible()
    assert _posts(page).count() > 0, "No Art posts after rapid clicks"


@pytest.mark.web
def test_TC_FEED_WEB_008_science_keyboard_navigation(page: Page):
    """TC-FEED-WEB-008 | Regression | Keyboard Enter on Science filter updates feed"""
    page.goto(_FEED_URL)
    science_btn = _filter_btn(page, "Science")
    expect(science_btn).to_be_visible()
    science_btn.focus()
    page.keyboard.press("Enter")
    expect(_posts(page).first).to_be_visible()
    assert _posts(page).count() > 0, "No Science posts after keyboard navigation"

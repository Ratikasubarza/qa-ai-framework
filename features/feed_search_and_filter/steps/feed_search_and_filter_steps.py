import pytest
from playwright.sync_api import Page, expect

import allure

pytestmark = [allure.feature("Feed Search and Filter"), allure.suite("Web")]


def _topic_button(page: Page, topic: str):
    return page.locator(f'[data-testid="topic-{topic.lower()}"]')


def _filter_button(page: Page, filter_name: str):
    return page.locator(f'[data-testid="filter-{filter_name.lower()}"]')


def _post_locator(page: Page):
    return page.locator('[data-testid="post"]')


def _empty_state_locator(page: Page):
    return page.locator('[data-testid="empty-state"]')


@pytest.mark.parametrize("topic", ["Technology"])
@pytest.mark.web
def test_TC_FEED_001_technology_filter(page: Page, topic: str):
    """
    Scenario ID: TC-FEED-001
    Type: e2e
    Description: Verify that selecting the Technology topic filter shows only Technology posts.
    """
    page.goto(f"{page.url}/feed")
    btn = _topic_button(page, topic)
    expect(btn).to_be_visible()
    btn.click()
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    count = posts.count()
    assert count > 0, f"Expected at least one {topic} post"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Technology" in tag.text_content(), f"Post {i} does not contain Technology tag"


@pytest.mark.web
def test_TC_FEED_002_heart_topic_instant_update(page: Page):
    """
    Scenario ID: TC-FEED-002
    Type: smoke
    Description: Verify that selecting the Heart topic updates feed within 2 seconds without page reload.
    """
    page.goto(f"{page.url}/feed")
    initial_url = page.url
    heart_btn = _filter_button(page, "Heart")
    expect(heart_btn).to_be_visible()
    heart_btn.click()
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    assert page.url == initial_url, "Page reloaded after selecting Heart filter"
    count = posts.count()
    assert count > 0, "No Heart posts found"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Heart" in tag.text_content(), f"Post {i} not tagged Heart"


@pytest.mark.web
def test_TC_FEED_003_all_topics_filter(page: Page):
    """
    Scenario ID: TC-FEED-003
    Type: e2e
    Description: Verify that selecting All Topics shows all posts regardless of topic.
    """
    page.goto(f"{page.url}/feed")
    all_btn = _filter_button(page, "All Topics")
    expect(all_btn).to_be_visible()
    all_btn.click()
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    assert posts.count() > 0, "No posts found after selecting All Topics"


@pytest.mark.web
@pytest.mark.negative
def test_TC_FEED_004_travel_no_posts(page: Page):
    """
    Scenario ID: TC-FEED-004
    Type: regression
    Description: Verify that selecting Travel topic with no posts shows empty state UI.
    """
    page.goto(f"{page.url}/feed")
    travel_btn = _filter_button(page, "Travel")
    expect(travel_btn).to_be_visible()
    travel_btn.click()
    empty_state = _empty_state_locator(page)
    expect(empty_state).to_be_visible()
    assert "No posts available" in empty_state.text_content(), "Empty state message missing"


@pytest.mark.web
def test_TC_FEED_005_sports_filter_persistence(page: Page):
    """
    Scenario ID: TC-FEED-005
    Type: e2e
    Description: Verify that Sports filter remains active after page refresh and shows Sports posts.
    """
    page.goto(f"{page.url}/feed")
    sports_btn = _filter_button(page, "Sports")
    expect(sports_btn).to_be_visible()
    sports_btn.click()
    page.reload()
    active_filter = _filter_button(page, "Sports")
    expect(active_filter).to_be_visible()
    assert active_filter.is_checked(), "Sports filter not active after refresh"
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    count = posts.count()
    assert count > 0, "No Sports posts after refresh"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Sports" in tag.text_content(), f"Post {i} not tagged Sports"


@pytest.mark.web
@pytest.mark.negative
def test_TC_FEED_006_injection_attempt(page: Page):
    """
    Scenario ID: TC-FEED-006
    Type: negative
    Description: Verify that injection attempt in topic selection does not apply any filter.
    """
    page.goto(f"{page.url}/feed")
    topic_input = page.locator('[data-testid="topic-search-input"]')
    expect(topic_input).to_be_visible()
    topic_input.fill('<script>alert(1)</script>')
    submit_btn = page.locator('[data-testid="topic-search-submit"]')
    expect(submit_btn).to_be_visible()
    submit_btn.click()
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    assert posts.count() > 0, "No posts after injection attempt"
    assert not page.is_visible('text=1'), "Alert dialog appeared after injection"


@pytest.mark.web
def test_TC_FEED_007_art_topic_race_condition(page: Page):
    """
    Scenario ID: TC-FEED-007
    Type: regression
    Description: Verify that rapid clicks on Art topic updates feed correctly without crashes.
    """
    page.goto(f"{page.url}/feed")
    art_filter = _filter_button(page, "Art")
    expect(art_filter).to_be_visible()
    for _ in range(10):
        art_filter.click()
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    count = posts.count()
    assert count > 0, "No Art posts after rapid clicks"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Art" in tag.text_content(), f"Post {i} not tagged Art"


@pytest.mark.web
def test_TC_FEED_008_science_keyboard_navigation(page: Page):
    """
    Scenario ID: TC-FEED-008
    Type: regression
    Description: Verify that keyboard navigation to Science topic updates feed accordingly.
    """
    page.goto(f"{page.url}/feed")
    science_filter = _filter_button(page, "Science")
    expect(science_filter).to_be_visible()
    science_filter.focus()
    page.keyboard.press("Enter")
    posts = _post_locator(page)
    expect(posts.first).to_be_visible()
    count = posts.count()
    assert count > 0, "No Science posts after keyboard navigation"
    for i in range(count):
        tag = posts.nth(i).locator('[data-testid="post-tag"]')
        assert "Science" in tag.text_content(), f"Post {i} not tagged Science"

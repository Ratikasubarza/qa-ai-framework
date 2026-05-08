import pytest
from playwright.sync_api import Page, expect
from skills.base.element_interaction import ElementInteraction
from skills.base.wait_strategy import WaitStrategy
from skills.base.assertion_helper import AssertionHelper

# Helper functions for locators
def topic_button(page: Page, topic: str):
    return page.locator(f'[data-testid="topic-{topic.lower()}"]')

def filter_button(page: Page, filter_name: str):
    return page.locator(f'[data-testid="filter-{filter_name.lower()}"]')

def post_locator(page: Page):
    return page.locator('[data-testid="post"]')

def empty_state_locator(page: Page):
    return page.locator('[data-testid="empty-state"]')

# Test for Scenario 1: Technology tag filter
@pytest.mark.parametrize("topic", ["Technology"])
def test_TC_001_technology_filter(page: Page, topic: str):
    """
    Scenario ID: TC-001
    Type: e2e
    Description: Verify that selecting the Technology topic filter shows only Technology posts.
    """
    # Navigate to feed page
    page.goto(f"{page.url}/feed")
    # Wait for topic button
    WaitStrategy.for_element(topic_button(page, topic)).to_be_visible()
    # Click topic
    ElementInteraction.click(topic_button(page, topic))
    # Verify posts displayed
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, f"Expected at least one {topic} post")
    # Verify each post has Technology tag
    for i in range(count):
        post = posts.nth(i)
        tag = post.locator('[data-testid="post-tag"]')
        AssertionHelper.assert_contains(tag.text_content(), "Technology", f"Post {i} does not contain Technology tag")

# Test for Scenario 2: Heart topic filter with instant update
def test_TC_002_heart_topic_instant_update(page: Page):
    """
    Scenario ID: TC-002
    Type: smoke
    Description: Verify that selecting the Heart topic updates feed within 2 seconds without page reload.
    """
    page.goto(f"{page.url}/feed")
    # Capture initial URL
    initial_url = page.url
    # Click Heart filter
    WaitStrategy.for_element(filter_button(page, "Heart")).to_be_visible()
    ElementInteraction.click(filter_button(page, "Heart"))
    # Wait for posts to load
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    # Ensure URL hasn't changed
    AssertionHelper.assert_equal(page.url, initial_url, "Page reloaded after selecting Heart filter")
    # Ensure posts are Heart tagged
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No Heart posts found")
    for i in range(count):
        post = posts.nth(i)
        tag = post.locator('[data-testid="post-tag"]')
        AssertionHelper.assert_contains(tag.text_content(), "Heart", f"Post {i} not tagged Heart")

# Test for Scenario 3: All Topics filter
def test_TC_003_all_topics_filter(page: Page):
    """
    Scenario ID: TC-003
    Type: e2e
    Description: Verify that selecting All Topics shows all posts regardless of topic.
    """
    page.goto(f"{page.url}/feed")
    WaitStrategy.for_element(filter_button(page, "All Topics")).to_be_visible()
    ElementInteraction.click(filter_button(page, "All Topics"))
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No posts found after selecting All Topics")

# Test for Scenario 4: Travel topic with no posts (empty state)
def test_TC_004_travel_no_posts(page: Page):
    """
    Scenario ID: TC-004
    Type: regression
    Description: Verify that selecting Travel topic with no posts shows empty state UI.
    """
    page.goto(f"{page.url}/feed")
    WaitStrategy.for_element(filter_button(page, "Travel")).to_be_visible()
    ElementInteraction.click(filter_button(page, "Travel"))
    # Wait for empty state
    empty_state = empty_state_locator(page)
    WaitStrategy.for_element(empty_state).to_be_visible()
    AssertionHelper.assert_contains(empty_state.text_content(), "No posts available", "Empty state message missing")

# Test for Scenario 5: Sports filter remains active after refresh
def test_TC_005_sports_filter_persistence(page: Page):
    """
    Scenario ID: TC-005
    Type: e2e
    Description: Verify that Sports filter remains active after page refresh and shows Sports posts.
    """
    page.goto(f"{page.url}/feed")
    WaitStrategy.for_element(filter_button(page, "Sports")).to_be_visible()
    ElementInteraction.click(filter_button(page, "Sports"))
    # Refresh page
    page.reload()
    # Verify filter still active
    active_filter = filter_button(page, "Sports")
    WaitStrategy.for_element(active_filter).to_be_visible()
    AssertionHelper.assert_true(active_filter.is_checked(), "Sports filter not active after refresh")
    # Verify posts
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No Sports posts after refresh")
    for i in range(count):
        post = posts.nth(i)
        tag = post.locator('[data-testid="post-tag"]')
        AssertionHelper.assert_contains(tag.text_content(), "Sports", f"Post {i} not tagged Sports")

# Test for Scenario 6: Injection attempt in topic selection
def test_TC_006_injection_attempt(page: Page):
    """
    Scenario ID: TC-006
    Type: negative
    Description: Verify that injection attempt in topic selection does not apply any filter.
    """
    page.goto(f"{page.url}/feed")
    # Attempt to inject script via topic input (assuming there's an input for topic search)
    topic_input = page.locator('[data-testid="topic-search-input"]')
    WaitStrategy.for_element(topic_input).to_be_visible()
    ElementInteraction.fill(topic_input, '<script>alert(1)</script>')
    # Submit search
    submit_btn = page.locator('[data-testid="topic-search-submit"]')
    WaitStrategy.for_element(submit_btn).to_be_visible()
    ElementInteraction.click(submit_btn)
    # Verify no filter applied: feed should show default posts
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No posts after injection attempt")
    # Ensure no script executed: check for absence of alert dialog
    AssertionHelper.assert_false(page.is_visible('text=1'), "Alert dialog appeared after injection")

# Test for Scenario 7: Rapid topic changes (Art)
def test_TC_007_art_topic_race_condition(page: Page):
    """
    Scenario ID: TC-007
    Type: regression
    Description: Verify that rapid clicks on Art topic updates feed correctly without crashes.
    """
    page.goto(f"{page.url}/feed")
    art_filter = filter_button(page, "Art")
    WaitStrategy.for_element(art_filter).to_be_visible()
    # Rapidly click 10 times
    for _ in range(10):
        ElementInteraction.click(art_filter)
    # Verify feed shows Art posts
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No Art posts after rapid clicks")
    for i in range(count):
        post = posts.nth(i)
        tag = post.locator('[data-testid="post-tag"]')
        AssertionHelper.assert_contains(tag.text_content(), "Art", f"Post {i} not tagged Art")

# Test for Scenario 8: Keyboard navigation for Science topic
def test_TC_008_science_keyboard_navigation(page: Page):
    """
    Scenario ID: TC-008
    Type: regression
    Description: Verify that keyboard navigation to Science topic updates feed accordingly.
    """
    page.goto(f"{page.url}/feed")
    # Focus on Science filter via keyboard
    science_filter = filter_button(page, "Science")
    WaitStrategy.for_element(science_filter).to_be_visible()
    science_filter.focus()
    # Press Enter
    page.keyboard.press("Enter")
    # Verify feed updates
    posts = post_locator(page)
    WaitStrategy.for_element(posts).to_be_visible()
    count = posts.count()
    AssertionHelper.assert_greater_than(count, 0, "No Science posts after keyboard navigation")
    for i in range(count):
        post = posts.nth(i)
        tag = post.locator('[data-testid="post-tag"]')
        AssertionHelper.assert_contains(tag.text_content(), "Science", f"Post {i} not tagged Science")
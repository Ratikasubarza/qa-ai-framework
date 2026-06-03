"""
Feed Search & Filter Web Locators — data-testid selectors for the Hono feed page.
"""

# ── Feed page navigation ───────────────────────────────────────────────────
FEED_URL = "/feed"

# ── Topic filters ──────────────────────────────────────────────────────────
def TOPIC_BUTTON(topic: str) -> str:
    return f'[data-testid="topic-{topic.lower()}"]'

def FILTER_BUTTON(filter_name: str) -> str:
    return f'[data-testid="filter-{filter_name.lower()}"]'

# ── Feed content ───────────────────────────────────────────────────────────
POST            = '[data-testid="post"]'
POST_TAG        = '[data-testid="post-tag"]'
EMPTY_STATE     = '[data-testid="empty-state"]'

# ── Search ─────────────────────────────────────────────────────────────────
TOPIC_SEARCH_INPUT  = '[data-testid="topic-search-input"]'
TOPIC_SEARCH_SUBMIT = '[data-testid="topic-search-submit"]'

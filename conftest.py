import pytest
from playwright.sync_api import Page

BASE_URL = "https://app-dev.thehono.com"

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL

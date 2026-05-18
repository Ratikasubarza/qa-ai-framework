"""
Root conftest for all features.
asyncio_mode = auto is set in pytest.ini — no event loop fixture needed here.
Feature-specific fixtures live in features/<feature>/steps/*/conftest.py.
"""
import pytest
from config.test_config import TestConfig


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return TestConfig.API_URL


@pytest.fixture(scope="session")
def web_base_url() -> str:
    return TestConfig.WEB_APP_URL


@pytest.fixture(scope="session")
def api_key() -> str:
    return TestConfig.API_KEY
